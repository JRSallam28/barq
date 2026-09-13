#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8090")
PROJECT = "barq-assessment"
TIMEOUT = 3
READY_WAIT = 30

failures = []


def report(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")
    if not ok:
        failures.append(name)


def request(method, path, body=None):
    url = BASE_URL + path
    data = None

    headers = {
        "Accept": "application/json",
        "User-Agent": "barq-validator/1.0",
    }

    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode()
            return response.status, raw, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, raw, dict(exc.headers)
    except Exception as exc:
        return None, str(exc), {}


def docker(*args):
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def wait_for_ready():
    deadline = time.monotonic() + READY_WAIT

    while time.monotonic() < deadline:
        status, body, _ = request("GET", "/ready")

        if status == 200:
            return True, body

        time.sleep(1)

    return False, "readiness timeout"


def check_public_ready():
    ok, body = wait_for_ready()

    if not ok:
        report("public readiness", False, body)
        return None

    try:
        payload = json.loads(body)
        deps = payload.get("dependencies", {})
        ready = (
            payload.get("status") == "ready"
            and deps.get("postgres") == "ready"
            and deps.get("redis") == "ready"
        )
        report(
            "public /ready",
            ready,
            f"postgres={deps.get('postgres')} redis={deps.get('redis')}",
        )
        return payload
    except json.JSONDecodeError:
        report("public /ready", False, "invalid JSON")
        return None


def check_endpoint(path, expected_status=200):
    status, body, headers = request("GET", path)

    ok = status == expected_status
    report(path, ok, f"HTTP {status}")

    if ok and not headers.get("X-Request-ID"):
        report(f"{path} request ID", False, "X-Request-ID missing")
    elif ok:
        report(f"{path} request ID", True)

    return status, body


def check_instances():
    instances = set()
    attempts = 0
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        attempts += 1
        status, body, _ = request("GET", "/instance")

        if status == 200:
            try:
                payload = json.loads(body)
                instance_id = payload.get("instance_id")

                if instance_id:
                    instances.add(instance_id)
            except json.JSONDecodeError:
                pass

        if {"app-01", "app-02" , "app-03"}.issubset(instances):
            break

        time.sleep(0.5)

    expected = {"app-01", "app-02", "app-03"}
    ok = expected.issubset(instances)

    report(
        "both backend instances reachable",
        ok,
        f"observed={sorted(instances)} attempts={attempts}",
    )

def check_records():
    title = f"BARQ validator {int(time.time())}"

    status, body, _ = request(
        "POST",
        "/records",
        {"title": title},
    )

    if status != 201:
        report("POST /records", False, f"HTTP {status}: {body}")
        return

    report("POST /records", True, "HTTP 201")

    status, body, _ = request("GET", "/records")

    if status != 200:
        report("GET /records", False, f"HTTP {status}")
        return

    try:
        records = json.loads(body)

        if isinstance(records, dict):
            records = records.get("records", [])

        found = any(
            isinstance(record, dict)
            and record.get("title") == title
            for record in records
        )

        report("GET /records persistence", found)
    except json.JSONDecodeError:
        report("GET /records persistence", False, "invalid JSON")


def check_counter():
    values = []

    for _ in range(3):
        status, body, _ = request("GET", "/counter")

        if status != 200:
            report("Redis counter", False, f"HTTP {status}")
            return

        try:
            payload = json.loads(body)
            values.append(int(payload["counter"]))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            report("Redis counter", False, "invalid counter response")
            return

    ok = values[0] < values[1] < values[2]

    report("Redis atomic counter", ok, f"values={values}")


def check_container_health():
    expected = ["app-01", "app-02", "app-03", "nginx", "postgres", "redis"]

    code, output, error = docker(
        "compose",
        "-p",
        PROJECT,
        "ps",
        "--format",
        "json",
    )

    if code != 0:
        report("Docker Compose health", False, error)
        return

    services = {}

    for line in output.splitlines():
        try:
            item = json.loads(line)
            services[item.get("Name")] = item
        except json.JSONDecodeError:
            continue

    missing = [name for name in expected if name not in services]

    unhealthy = []

    for name in expected:
        if name not in services:
            continue

        status = services[name].get("Health", "")
        if name != "nginx" and status != "healthy":
            unhealthy.append(f"{name}={status}")

    ok = not missing and not unhealthy

    report(
        "container health",
        ok,
        f"missing={missing} unhealthy={unhealthy}",
    )


def check_host_ports():
    expected = {
        "postgres": False,
        "redis": False,
    }

    code, output, error = docker(
        "ps",
        "--format",
        "{{.Names}}|{{.Ports}}",
    )

    if code != 0:
        report("prohibited host ports", False, error)
        return

    for line in output.splitlines():
        if "|" not in line:
            continue

        name, ports = line.split("|", 1)

        if name in expected:
            host_mapping = "->" in ports
            expected[name] = not host_mapping

    ok = all(expected.values())

    report(
        "PostgreSQL/Redis host ports absent",
        ok,
        str(expected),
    )


def check_network_isolation():
    code, output, error = docker(
        "network",
        "inspect",
        f"{PROJECT}_backend",
    )

    if code != 0:
        report("backend network isolation", False, error)
        return

    try:
        networks = json.loads(output)
        network = networks[0]

        internal = network.get("Internal") is True
        containers = network.get("Containers", {})

        names = set()

        for container in containers.values():
            names.add(container.get("Name"))

        expected = {"app-01", "app-02", "app-03", "postgres", "redis"}
        forbidden = {"nginx"}

        ok = internal and expected.issubset(names) and names.isdisjoint(forbidden)

        report(
            "backend network isolation",
            ok,
            f"internal={internal} containers={sorted(names)}",
        )
    except (ValueError, IndexError, KeyError, TypeError):
        report("backend network isolation", False, "invalid Docker network data")


def main():
    print(f"BARQ validation against {BASE_URL}")
    print("-" * 60)

    check_public_ready()

    check_endpoint("/")
    check_endpoint("/health")
    check_endpoint("/ready")
    check_endpoint("/instance")

    check_instances()
    check_records()
    check_counter()

    check_container_health()
    check_host_ports()
    check_network_isolation()

    print("-" * 60)

    if failures:
        print(f"VALIDATION FAILED: {len(failures)} check(s)")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
