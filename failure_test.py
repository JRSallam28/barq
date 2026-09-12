#!/usr/bin/env python3

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

BASE_URL = "http://127.0.0.1:8080"
PROJECT = "barq-assessment"
BACKEND = "app-02"
REQUESTS = 20
TIMEOUT = 3
HEALTH_WAIT = 30


def run_command(*args):
    result = subprocess.run(
        args,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n"
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def http_get(path):
    url = BASE_URL + path

    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body

    except urllib.error.HTTPError as exc:
        return exc.code, ""

    except Exception as exc:
        return 0, str(exc)


def wait_for_backend_healthy(timeout=HEALTH_WAIT):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            output = run_command(
                "docker",
                "compose",
                "-p",
                PROJECT,
                "ps",
                "--format",
                "json",
                BACKEND,
            )

            if output:
                data = json.loads(output)

                if isinstance(data, list):
                    data = data[0] if data else {}

                health = data.get("Health", "").lower()
                state = data.get("State", "").lower()

                if health == "healthy":
                    return True

                if state == "running" and not health:
                    # Older compose output may omit Health.
                    status, _ = http_get("/health")
                    if status == 200:
                        return True

        except Exception:
            pass

        time.sleep(1)

    return False


def measure_traffic(label):
    statuses = []
    instances = []

    print(f"\n[{label}] Sending {REQUESTS} requests...")

    for _ in range(REQUESTS):
        status, body = http_get("/instance")
        statuses.append(status)

        if status == 200:
            try:
                data = json.loads(body)
                instances.append(data.get("instance_id", "unknown"))
            except json.JSONDecodeError:
                instances.append("invalid-json")

        time.sleep(0.1)

    counts = Counter(statuses)

    print(f"[{label}] HTTP status counts: {dict(sorted(counts.items()))}")
    print(f"[{label}] Instances observed: {sorted(set(instances))}")

    successful = counts.get(200, 0)
    errors = REQUESTS - successful

    return successful, errors, instances


def main():
    failed = False

    print("=== BARQ Failure / Recovery Test ===")
    print(f"Project: {PROJECT}")
    print(f"Backend under test: {BACKEND}")
    print(f"Public endpoint: {BASE_URL}")

    # Initial health check
    status, _ = http_get("/ready")

    if status != 200:
        print(f"FAIL: public /ready returned HTTP {status}")
        return 1

    print("PASS: public /ready is healthy before failure test.")

    try:
        # Stop one backend
        print(f"\nStopping {BACKEND}...")
        run_command(
            "docker",
            "compose",
            "-p",
            PROJECT,
            "stop",
            BACKEND,
        )

        print(f"PASS: {BACKEND} stopped.")

        # Measure availability while backend is down
        successful, errors, instances = measure_traffic("FAILURE")

        if successful == REQUESTS:
            print(
                f"PASS: traffic remained fully available "
                f"({successful}/{REQUESTS} HTTP 200)."
            )
        elif successful > 0:
            print(
                f"PASS: service remained available during backend failure "
                f"({successful}/{REQUESTS} HTTP 200, {errors} errors)."
            )
            print("NOTE: Some errors occurred during failover.")
        else:
            print("FAIL: no successful requests during backend failure.")
            failed = True

        if "app-02" in instances:
            print("FAIL: app-02 still served traffic while stopped.")
            failed = True
        else:
            print("PASS: app-02 was absent from observed traffic.")

    finally:
        # Always restore the stopped backend
        print(f"\nRestoring {BACKEND}...")
        try:
            run_command(
                "docker",
                "compose",
                "-p",
                PROJECT,
                "start",
                BACKEND,
            )
            print(f"PASS: {BACKEND} start requested.")
        except Exception as exc:
            print(f"FAIL: could not restore {BACKEND}: {exc}")
            failed = True

    # Wait for recovery
    print(f"Waiting up to {HEALTH_WAIT}s for {BACKEND} to become healthy...")

    if wait_for_backend_healthy():
        print(f"PASS: {BACKEND} is healthy again.")
    else:
        print(f"FAIL: {BACKEND} did not become healthy.")
        failed = True

    # Measure traffic after recovery
    successful, errors, instances = measure_traffic("RECOVERY")

    if successful > 0:
        print(
            f"PASS: service is available after recovery "
            f"({successful}/{REQUESTS} HTTP 200)."
        )
    else:
        print("FAIL: no successful requests after recovery.")
        failed = True

    if "app-02" in instances:
        print("PASS: app-02 returned to the traffic pool.")
    else:
        print("FAIL: app-02 was not observed after recovery.")
        failed = True

    # Final readiness check
    status, _ = http_get("/ready")

    if status == 200:
        print("PASS: public /ready is healthy after recovery.")
    else:
        print(f"FAIL: public /ready returned HTTP {status} after recovery.")
        failed = True

    print("\n=== RESULT ===")

    if failed:
        print("FAIL: failure/recovery test did not fully pass.")
        return 1

    print("PASS: failure/recovery test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
