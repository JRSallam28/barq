<img src="assets/barq-logo.svg" alt="BARQ Systems" width="180">

# BARQ Systems DevOps Internship Assessment

Final repaired and validated BARQ assessment environment.

## Final State

* Public URL: `http://127.0.0.1:8090`
* Reverse proxy: NGINX
* Flask backends: `app-01`, `app-02`, `app-03`
* PostgreSQL for persistent records
* Redis for the shared atomic counter
* Only NGINX is published to the host
* Flask applications listen internally on port `8080`
* PostgreSQL and Redis have no host-published ports

### Network layout

`frontend`:

* nginx
* app-01
* app-02
* app-03

`backend` (`internal: true`):

* app-01
* app-02
* app-03
* postgres
* redis

NGINX is deliberately not connected to the backend network.

## Requirements

* Linux or WSL2
* Docker with Compose
* Git
* Bash
* Python 3

Docker must be running before starting the environment.

## Setup

Create the local environment file:

```bash
cp .env.example .env

password="$(openssl rand -hex 24)"
sed -i "s/change-me/$password/g" .env
```

The real `.env` is ignored by Git and must not be committed.

Validate the Compose configuration:

```bash
docker compose -p barq-assessment config --quiet
```

## Build and Start

```bash
docker compose -p barq-assessment build
docker compose -p barq-assessment up -d
docker compose -p barq-assessment ps
```

The final environment contains six containers:

```text
app-01
app-02
app-03
nginx
postgres
redis
```

## Endpoint Checks

```bash
curl -i http://127.0.0.1:8090/
curl -i http://127.0.0.1:8090/health
curl -i http://127.0.0.1:8090/ready
curl -i http://127.0.0.1:8090/instance
```

`/health` checks Flask process liveness.

`/ready` performs real PostgreSQL and Redis dependency checks.

To prove all three application instances are reachable through NGINX:

```bash
for i in {1..18}; do
  curl -s -H 'Connection: close' http://127.0.0.1:8090/instance
  echo
done
```

The output should include:

```text
app-01
app-02
app-03
```

## PostgreSQL Records

Create a record:

```bash
curl -i \
  -H 'Content-Type: application/json' \
  -d '{"title":"Persistence proof"}' \
  http://127.0.0.1:8090/records
```

Read records:

```bash
curl http://127.0.0.1:8090/records
```

## Redis Counter

```bash
curl http://127.0.0.1:8090/counter
curl http://127.0.0.1:8090/counter
curl http://127.0.0.1:8090/counter
```

The counter uses Redis atomic increments and is shared across all application instances.

## Automated Validation

```bash
BASE_URL=http://127.0.0.1:8090 ./validate.py
```

A successful run ends with:

```text
VALIDATION PASSED
```

The validator verifies:

* public readiness
* required application endpoints
* request IDs
* all three backend identities
* PostgreSQL record persistence
* Redis counter behavior
* container health
* PostgreSQL and Redis host-port isolation
* internal backend network isolation

## Failure and Recovery Test

```bash
BASE_URL=http://127.0.0.1:8090 ./failure_test.py
```

The test removes one application backend from service, measures availability, restores the backend and verifies that it serves traffic again.

## Persistence

PostgreSQL and Redis use named Docker volumes. Redis also has AOF persistence enabled.

A PostgreSQL record can be created and then containers recreated without deleting the volume:

```bash
docker compose -p barq-assessment up -d --force-recreate postgres app-01 app-02 app-03
docker compose -p barq-assessment ps
curl http://127.0.0.1:8090/records
```

The previously created record should still exist.

A Docker volume protects data from normal container replacement, but it is not a substitute for an independent backup.

## Backup

Create a PostgreSQL logical backup:

```bash
./backup.sh
```

Or specify a custom output path:

```bash
./backup.sh backups/manual.sql
```

Backup files are excluded from Git.

## Restore

Restore the backup into the isolated restore-test database:

```bash
./restore.sh backups/barq_tasks_backup.sql
```

The script recreates the restore target and imports the SQL dump with PostgreSQL error checking enabled.

## Stop

Stop containers without deleting them or their volumes:

```bash
docker compose -p barq-assessment stop
```

Restart them:

```bash
docker compose -p barq-assessment start
```

## Cleanup

Remove containers and networks while retaining named volumes:

```bash
docker compose -p barq-assessment down
```

Remove the complete local lab, including persistent volumes, only when the data is no longer required:

```bash
docker compose -p barq-assessment down -v
```

Do not use `-v` during persistence testing.

## CI

GitHub Actions is implemented in:

```text
.github/workflows/ci.yml
```

It runs on pushes and pull requests and performs:

1. shell, Python and Compose checks
2. Docker image build
3. Compose startup
4. bounded readiness checking
5. `validate.py`
6. service-status capture
7. cleanup of the disposable CI environment

The final CI environment uses public port `8090`, matching the final repository and recorded video state.

CI proves that the committed environment can be built, started and validated on a clean GitHub runner. It does not prove production-scale availability, load capacity or disaster recovery.

## What Failed First?

The first repaired issue was the application container health-check configuration.

The configured probe did not correctly match the implemented Flask liveness endpoint. The cause was identified by comparing the Compose health-check configuration with the application implementation and retesting after correction.

The complete chronological investigation is recorded in `troubleshooting.md`.

## Useful Failed Attempt

During image hardening, an incorrect Redis image digest was initially tried and Docker rejected it.

Instead of guessing another value, the exact image reference was obtained by inspecting the known working Redis container. The verified digest was then pinned and successfully retested.

This demonstrated why deployment values should be verified from runtime evidence rather than assumed.

## Architecture Decisions

Docker service names are used instead of container IP addresses because Docker DNS provides stable service discovery while container addresses can change after recreation.

Only NGINX is published because the application backends, PostgreSQL and Redis do not require direct host access.

Liveness and readiness are deliberately separate:

* `/health` checks Flask process liveness.
* `/ready` checks PostgreSQL and Redis availability.

Services also use restart policies, resource limits and health checks to improve recovery behavior and reduce the impact of malfunctioning containers.

See `decisions.md` for the documented trade-offs.

## Remaining Single Points of Failure

The assessment improves application-instance availability but is not a complete production high-availability architecture.

Remaining single points include:

* one NGINX instance
* one PostgreSQL instance
* one Redis instance
* one Docker host
* local Docker volume storage

Production improvements could include redundant load balancers, database replication/failover, Redis HA, multi-host orchestration, external backups and centralized monitoring.

See `security_review.md` for the production-readiness review.

## Historical Log Analysis

Historical access, application and NGINX error logs were correlated using request IDs.

Exact duplicate request rows were removed before request-level calculations to avoid double counting.

The logs showed distinct failure phases including:

* upstream connection-refused failures
* Redis dependency failures
* PostgreSQL dependency failures
* upstream timeouts

They also contained evidence of successful NGINX retries where one upstream failed but another backend successfully completed the request.

Detailed calculations and correlated examples are documented in `log_analysis.md`.

## AI Usage

AI assistance was used for troubleshooting discussion, implementation review, validation logic, documentation structure and analysis support.

AI suggestions were verified against the actual environment rather than accepted as evidence without testing.

One incorrect AI-assisted Redis digest was rejected by Docker and replaced using evidence obtained directly from Docker inspection.

Full disclosure is documented in `AI_USAGE.md`.

## Evidence

Supporting evidence is available in:

* `troubleshooting.md`
* `log_analysis.md`
* `decisions.md`
* `security_review.md`
* `AI_USAGE.md`
* `docs/EVIDENCE_INDEX.md`
* `architecture.png`
* `.assessment/challenge.json`

The recorded challenge was executed once during the continuous assessment video and its generated receipt is preserved as evidence.

## Final Submitted Configuration

```text
Public port: 8090
Backends: app-01, app-02, app-03
Proxy: nginx
Database: postgres
Cache: redis
```
