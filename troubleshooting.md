# Troubleshooting journal

This journal records the actual investigation, failed attempts, fixes, and retest evidence from the BARQ DevOps environment. No issue is considered fixed without a successful retest.

## 1. Application healthcheck used the wrong endpoint

- Symptom: the application container healthcheck did not become healthy.
- Hypothesis: the configured healthcheck path did not match the Flask API contract.
- Command or test: inspected the Compose healthcheck and compared it with the application endpoints.
- Actual output: the healthcheck targeted `/healthz`, while the application exposes `/health`.
- Failed attempt and what changed my thinking: initial container failures could have been caused by the application itself, but checking the endpoint directly showed the process responded on `/health`.
- Root cause: incorrect healthcheck path.
- Fix: changed the application healthcheck to `http://127.0.0.1:8080/health`.
- Retest evidence: application healthcheck could proceed to the next startup issue.
- Related commit: `4e6aeaa fix: correct application healthcheck endpoint`
- Remaining uncertainty: none for this issue.

## 2. Flask was not reachable from other containers

- Symptom: NGINX could not reliably reach the Flask services over the Docker network.
- Hypothesis: Flask was listening only on loopback inside its container.
- Command or test: inspected application bind configuration and container networking.
- Actual output: the application was not bound to all container interfaces.
- Failed attempt and what changed my thinking: fixing the healthcheck path alone did not make the service reachable through the expected container network path.
- Root cause: incorrect application bind address.
- Fix: configured `APP_HOST=0.0.0.0` and `APP_PORT=8080`.
- Retest evidence: application services became reachable using Docker service/container networking.
- Related commit: `f38813d fix: bind app services to container network`
- Remaining uncertainty: none for this issue.

## 3. NGINX upstream and public port mapping were incorrect

- Symptom: public requests through NGINX did not reach the Flask backends correctly.
- Hypothesis: the NGINX upstream or host/container port mapping was wrong.
- Command or test: inspected `nginx/nginx.conf`, Compose ports, and tested the public endpoint.
- Actual output: the upstream and port mapping did not match the Flask listener.
- Root cause: incorrect NGINX upstream/port configuration.
- Fix:
  - upstreams changed to `app-01:8080` and `app-02:8080`
  - only NGINX publishes `127.0.0.1:8080 -> 80`
- Retest evidence: public requests successfully reached the application through NGINX.
- Related commit: `afc63ea fix: correct nginx upstream and port mapping`
- Remaining uncertainty: none for this issue.

## 4. PostgreSQL and Redis used incorrect internal ports

- Symptom: application readiness failed because dependency connections did not succeed.
- Hypothesis: database/cache connection URLs were using the wrong container ports.
- Command or test: compared application URLs with PostgreSQL and Redis default internal ports.
- Actual output: dependency port configuration did not match PostgreSQL `5432` and Redis `6379`.
- Root cause: incorrect service-to-service ports.
- Fix:
  - PostgreSQL: `postgres:5432`
  - Redis: `redis:6379`
- Retest evidence: `/ready` successfully reported both dependencies ready.
- Related commit: `ce34fc8 fix: use correct internal ports for PostgreSQL and Redis`
- Remaining uncertainty: none for this issue.

## 5. Both backends initially returned the same identity

- Symptom: repeated `/instance` requests did not prove two distinct Flask instances.
- Hypothesis: both services were configured with the same `INSTANCE_ID`.
- Command or test: called `/instance` repeatedly and inspected Compose environment values.
- Actual output: application identity configuration was duplicated.
- Root cause: `app-02` did not have its own instance identifier.
- Fix:
  - `app-01`: `INSTANCE_ID=app-01`
  - `app-02`: `INSTANCE_ID=app-02`
- Retest evidence: repeated `/instance` requests eventually observed both `app-01` and `app-02`.
- Related commit: `fe10888 fix: assign unique instance id to app-02`
- Remaining uncertainty: none for this issue.

## 6. Runtime secrets and persistence configuration required hardening

- Symptom: runtime configuration included values that should not be stored in tracked configuration files.
- Hypothesis: secrets should come from an ignored local `.env` instead of tracked application configuration.
- Command or test:
  - `git check-ignore -v .env`
  - `git ls-files .env`
- Actual output:
  - `.env` was ignored by `.gitignore`
  - `git ls-files .env` returned no tracked file
- Root cause: runtime configuration needed clearer separation between tracked configuration and local secrets.
- Fix:
  - real local values kept in ignored `.env`
  - tracked `config/app.env` contains no real secret
  - PostgreSQL uses a named volume
- Retest evidence: application remained functional and PostgreSQL records survived container recreation.
- Related commit: `ff478d7 fix: secure runtime config and persistence`
- Remaining uncertainty: production secret management would require a real secrets manager.

## 7. Initial validator incorrectly classified exposed container ports

- Symptom: validation reported PostgreSQL and Redis as publicly exposed even though no host mappings existed.
- Hypothesis: the validator confused Docker's internal exposed ports with host port publishing.
- Command or test: compared `docker compose ps` output with validator parsing.
- Actual output: values such as `5432/tcp` and `6379/tcp` were treated as host mappings.
- Failed attempt and what changed my thinking: the first validation implementation treated any displayed port as exposure.
- Root cause: incorrect host-port detection logic.
- Fix: a port is treated as host-published only when the Docker output contains `->`.
- Retest evidence: validator correctly passed PostgreSQL/Redis host-port isolation.
- Related commit: `86391bf feat: add automated environment validation`
- Remaining uncertainty: none for the current Docker Compose output format.

## 8. Redis image digest was accidentally changed to a nonexistent digest

- Symptom: `docker compose up -d --build` failed while resolving the Redis image.
- Actual error: Docker reported the configured Redis digest as `not found`.
- Hypothesis: the digest had been guessed or copied incorrectly during Compose hardening.
- Failed attempt:
  - `docker image inspect redis:7.4-alpine ...`
  - returned `No such image: redis:7.4-alpine`
- What changed my thinking: the running container still had the authoritative image reference even though the local tag was unavailable.
- Command that proved the cause:
  - `docker inspect redis --format '{{.Config.Image}}'`
- Actual running image:
  - `redis:7.4-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf`
- Fix: restored the exact digest from the running Redis container.
- Retest evidence:
  - `docker compose ... config --quiet` returned exit code 0
  - `docker compose ... pull redis` succeeded
  - full rebuild completed successfully
- Related commit: `e1e24e4 fix: harden runtime and enforce network isolation`
- Remaining uncertainty: image digests must be deliberately updated when upstream versions change.

## 9. NGINX was incorrectly connected to the backend network

- Symptom: the environment worked, but network topology did not satisfy the assignment isolation requirement.
- Hypothesis: NGINX should not have direct network access to PostgreSQL or Redis.
- Command or test: inspected the Compose networks and Docker backend network membership.
- Actual output: NGINX was attached to both `frontend` and `backend`.
- Root cause: incorrect network membership in Compose.
- Fix:
  - NGINX attached only to `frontend`
  - apps attached to `frontend` and `backend`
  - PostgreSQL and Redis attached only to `backend`
  - validator explicitly forbids NGINX from the backend network
- Retest evidence:
  - `docker inspect nginx` showed only `barq-assessment_frontend`
  - validator reported backend containers as `app-01`, `app-02`, `postgres`, and `redis`
- Related commit: `e1e24e4 fix: harden runtime and enforce network isolation`
- Remaining uncertainty: Docker network isolation is not a replacement for production firewall/network-policy controls.

## 10. Backend observation check was flaky immediately after NGINX recreation

- Symptom: immediately after recreating NGINX, validation sometimes observed only `app-01`.
- Hypothesis: either load balancing was broken or the validation burst was too short during upstream recovery/warm-up.
- Command or test:
  - repeated `curl -H 'Connection: close' http://127.0.0.1:8080/instance`
  - inspected frontend network membership
- Actual output:
  - both `app-01` and `app-02` were connected to `frontend`
  - early requests could hit only `app-01`
  - subsequent requests observed `app-02` as well
- Failed attempt and what changed my thinking: repeating the original fixed 12-request validator could produce a false negative even though manual traffic later reached both backends.
- Root cause: the validator used a short fixed burst rather than a bounded observation window.
- Fix: changed instance validation to retry for up to 10 seconds with 0.5 second intervals and stop early once both instances are observed.
- Retest evidence:
  - validator passed with `observed=['app-01', 'app-02'] attempts=2`
- Related commit: `e1e24e4 fix: harden runtime and enforce network isolation`
- Remaining uncertainty: this verifies backend participation, not perfectly even traffic distribution.

## 11. Failure and recovery behavior

- Symptom tested: one Flask backend should be removable without losing public availability.
- Command or test: `./failure_test.py`
- Actual output during failure:
  - stopped `app-02`
  - HTTP status counts: `{200: 20}`
  - observed instances: `['app-01']`
- Actual output after recovery:
  - `app-02` became healthy
  - HTTP status counts: `{200: 20}`
  - observed instances: `['app-01', 'app-02']`
- Root cause: this was a resilience test, not a defect.
- Fix/implementation: automated stop, traffic measurement, recovery wait, and restored-backend verification.
- Retest evidence: `PASS: failure/recovery test completed successfully.`
- Related commit: `2b9a9f4 feat: add failure and recovery test`
- Remaining uncertainty: NGINX itself remains a single point of failure.

## 12. PostgreSQL backup and restore validation

- Symptom tested: a backup must be restorable, not merely created.
- Command or test:
  - `./backup.sh`
  - `./restore.sh`
  - queried restored database
- Actual output:
  - backup completed successfully
  - restore completed successfully
  - `SELECT COUNT(*) FROM records` returned `10`
- Root cause: original `backup.sh` and `restore.sh` were placeholders that exited with code 2.
- Fix: implemented reproducible `pg_dump`, database creation, and `psql` restore scripts with non-zero failures.
- Retest evidence: restored database contained 10 records.
- Related commit: `68d4856 feat: add PostgreSQL backup and restore scripts`
- Remaining uncertainty: production backups require retention, encryption, off-host storage, and regular restore drills.

## 13. CI validation

- Symptom: no GitHub Actions workflow existed.
- Root cause: CI was an unimplemented assignment deliverable.
- Fix: added a workflow triggered on push and pull request that performs:
  - checkout
  - syntax and Compose checks
  - build
  - start
  - bounded readiness wait
  - environment validation
  - service status and cleanup
- Retest evidence:
  - GitHub Actions run `34737925277`
  - conclusion: `success`
  - commit: `a2bf83eda168cd2151bd75036cb95f19785f039f`
- Related commit: `a2bf83e ci: validate environment on push and pull request`
- Remaining uncertainty: green CI proves the tested Compose environment passed these automated checks; it does not prove production scalability, security, monitoring, or high availability.
