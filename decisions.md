# Technical decisions

Record at least 5 decisions. Include assumptions and limits.

## Decision
- Choice:
- Why:
- Alternative:
- Trade-off:
- Evidence / commit:
- Production improvement:

Cover your base image, health checks, networks, timeouts/retries, restart/resource settings,
storage and any other meaningful choices.

# Technical decisions

These decisions describe the current BARQ assessment implementation. Production improvements are listed separately so implemented controls are not confused with future plans.

## 1. Use pinned container image digests

* Choice: use versioned images pinned by SHA-256 digest for Python, PostgreSQL, Redis and NGINX.
* Why: a digest makes the build more reproducible and prevents an upstream tag from silently changing.
* Alternative: use floating tags such as `python:3.12-slim`, `postgres:16-alpine`, `redis:7.4-alpine` and `nginx:alpine`.
* Trade-off: pinned images do not receive upstream fixes automatically; digest updates must be deliberate and tested.
* Evidence / commit: Dockerfile and `docker-compose.yml`; `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: use an automated dependency/image update process with vulnerability scanning and controlled review.

## 2. Run the Flask application as a non-root user

* Choice: create UID/GID 10001 and run the application as `USER app`.
* Why: the Flask process does not require root privileges, so dropping root reduces the impact of an application compromise.
* Alternative: run the container as root for simpler file ownership and startup behavior.
* Trade-off: non-root execution requires correct ownership of copied files and can expose permission mistakes that root would hide.
* Evidence / commit: Dockerfile; `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: also use a read-only root filesystem where practical, drop Linux capabilities and apply additional runtime security controls.

## 3. Separate liveness from dependency readiness

* Choice:

  * `/health` checks whether the Flask process can respond.
  * `/ready` checks real PostgreSQL and Redis connectivity.
  * the Docker app healthcheck uses `/health`.
* Why: a temporary database/cache failure should not incorrectly mean the application process itself is dead. Dependency-aware readiness is tested separately before considering the service fully usable.
* Alternative: make the Docker healthcheck call `/ready`.
* Trade-off: `/health` can remain healthy while dependencies are unavailable, so monitoring must also check `/ready`.
* Evidence / commit: app healthcheck configuration and validator; `4e6aeaa fix: correct application healthcheck endpoint`.
* Production improvement: expose separate liveness/readiness metrics and alert on sustained readiness failure.

## 4. Use health-aware startup dependencies

* Choice: `app-01` and `app-02` depend on healthy PostgreSQL and Redis, while NGINX depends on healthy application instances.
* Why: this reduces avoidable connection failures during normal startup and makes the Compose environment deterministic enough for automated validation.
* Alternative: start all containers concurrently and rely entirely on application retry behavior.
* Trade-off: Compose startup ordering helps the lab environment but does not replace resilient retry/backoff logic inside applications.
* Evidence / commit: `docker-compose.yml`; `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: applications should tolerate dependency restarts using bounded connection retries, backoff and connection-pool recovery.

## 5. Isolate frontend and backend networks

* Choice:

  * NGINX: `frontend` only.
  * Flask apps: `frontend` and `backend`.
  * PostgreSQL and Redis: `backend` only.
  * `backend` is configured as `internal: true`.
* Why: NGINX only needs access to the application backends. It does not need direct connectivity to PostgreSQL or Redis.
* Alternative: connect every service to one shared Docker network.
* Trade-off: network separation adds configuration complexity but reduces unnecessary connectivity and limits lateral access.
* Evidence / commit: `docker-compose.yml` and validation checks; `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: use explicit network policies/firewall rules, TLS between services where required and database-level access controls.

## 6. Persist PostgreSQL and Redis using named volumes

* Choice:

  * PostgreSQL stores data in `postgres-data`.
  * Redis stores `/data` in `redis-data` and uses AOF persistence.
* Why: application/container recreation should not destroy PostgreSQL records, and Redis state should survive ordinary Redis container recreation where appropriate.
* Alternative:

  * ephemeral container storage;
  * Redis persistence disabled.
* Trade-off: named volumes improve persistence but are still local to the Docker host and are not backups.
* Evidence / commit: `ff478d7 fix: secure runtime config and persistence` and `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: use managed or replicated storage, defined retention policies, off-host encrypted backups and regular restore testing.

## 7. Apply bounded resource limits and restart policies

* Choice:

  * app instances: `0.50` CPU, `256m` memory, `128` PIDs.
  * PostgreSQL: `0.50` CPU, `512m` memory, `128` PIDs.
  * Redis: `0.25` CPU, `128m` memory, `64` PIDs.
  * NGINX: `0.25` CPU, `128m` memory, `64` PIDs.
  * services use `restart: unless-stopped`.
* Why: the assessment environment should have explicit resource boundaries and recover automatically from ordinary process/container failures.
* Alternative: leave resources unlimited and use no restart policy.
* Trade-off: these limits are lab assumptions, not performance-tested production sizing. Limits that are too low can create artificial failures.
* Evidence / commit: `docker-compose.yml`; `e1e24e4 fix: harden runtime and enforce network isolation`.
* Production improvement: derive CPU/memory limits from load tests and production telemetry, and use orchestrator health/restart policies appropriate to the deployment platform.

## 8. Keep runtime secrets outside tracked files

* Choice:

  * real local runtime values are stored in ignored `.env`.
  * `.env.example` contains safe placeholders.
  * Compose references `POSTGRES_PASSWORD`, `DATABASE_URL` and `REDIS_URL` through environment substitution.
* Why: credentials must not be embedded in source code, images or committed Compose configuration.
* Alternative: hardcode credentials directly in `docker-compose.yml` or application files.
* Trade-off: local `.env` files are convenient for the assessment but still place secrets on disk and require careful file permissions and handling.
* Evidence / commit: `ff478d7 fix: secure runtime config and persistence` and `332700b docs: add safe runtime environment example`.
* Production improvement: use a dedicated secrets manager or orchestrator secret mechanism with rotation, scoped access and audit logging.

## Assumptions and limitations

* Resource limits are intentionally conservative lab values and were not derived from production load testing.
* `restart: unless-stopped` improves local recovery but does not provide host-level high availability.
* PostgreSQL, Redis and NGINX are each single instances, so they remain single points of failure.
* Named volumes provide persistence but not disaster recovery.
* Docker network isolation reduces unnecessary connectivity but is not equivalent to a production zero-trust network policy.
* Green validation and CI prove the tested Compose environment satisfies the automated checks; they do not prove production security, scalability, monitoring quality or disaster recovery.
