# Security and production-readiness review

Record at least 8 concrete risks or improvements relevant to your final solution.
This is a review requirement, not the number of hidden faults.

For each finding:
- Risk and evidence:
- Impact:
- Implemented fix / commit:
- Production follow-up:
- How to verify:

Cover secrets, ports, container user, image selection, networks, persistence/backup,
logging/monitoring and availability. Separate completed work from planned improvements.

# Security and production-readiness review

This review separates controls already implemented in the assessment environment from production improvements that are not claimed as completed.

## 1. Runtime secrets must not be committed

* Risk and evidence: database connection credentials and runtime secrets would be exposed if stored directly in source code, Compose files or the image.
* Impact: leaked credentials could allow unauthorized access to PostgreSQL or other dependent services.
* Implemented fix / commit:

  * real local values are stored in ignored `.env`
  * `.env` is not tracked
  * `.env.example` contains safe placeholder values only
  * commits: `ff478d7` and `332700b`
* Production follow-up: use a dedicated secrets manager or platform secret store with rotation and scoped access.
* How to verify:

  * `git check-ignore -v .env`
  * `git ls-files .env`
  * review tracked configuration for hardcoded credentials

## 2. Only NGINX is published to the host

* Risk and evidence: publishing PostgreSQL, Redis or Flask container ports would unnecessarily expose internal services.
* Impact: increases attack surface and could bypass the intended reverse-proxy boundary.
* Implemented fix / commit:

  * only NGINX publishes a host port
  * PostgreSQL and Redis expose container-internal ports only
  * validator checks for prohibited host mappings
  * related commits: `afc63ea`, `ce34fc8`, `86391bf`
* Production follow-up: enforce equivalent restrictions with cloud firewall/security-group rules and private subnets.
* How to verify:

  * `docker compose -p barq-assessment ps`
  * run `./validate.py`

## 3. Application container runs as non-root

* Risk and evidence: running the Flask application as root increases the impact of an application-level compromise.
* Impact: an attacker could gain unnecessary privileges inside the container.
* Implemented fix / commit:

  * application user/group use UID/GID 10001
  * Dockerfile ends with `USER app`
  * commit: `e1e24e4`
* Production follow-up:

  * use a read-only root filesystem where possible
  * drop unnecessary Linux capabilities
  * consider `no-new-privileges`
* How to verify:

  * inspect Dockerfile
  * `docker exec app-01 id`

## 4. Backend network is isolated from NGINX

* Risk and evidence: placing NGINX on the backend network would give it direct connectivity to PostgreSQL and Redis even though it does not require that access.
* Impact: unnecessary lateral movement path if NGINX is compromised.
* Implemented fix / commit:

  * NGINX uses `frontend` only
  * applications use `frontend` and `backend`
  * PostgreSQL and Redis use `backend` only
  * backend network is `internal: true`
  * validator explicitly rejects NGINX membership on backend
  * commit: `e1e24e4`
* Production follow-up: implement equivalent network policies/firewall rules and restrict database access to only required application identities.
* How to verify:

  * `docker network inspect barq-assessment_backend`
  * `docker inspect nginx`
  * run `./validate.py`

## 5. Container images are pinned by digest

* Risk and evidence: floating image tags can change without a repository change, reducing reproducibility and potentially introducing unreviewed software.
* Impact: unexpected image changes, supply-chain risk or inconsistent environments.
* Implemented fix / commit:

  * Python, PostgreSQL, Redis and NGINX images are pinned by SHA-256 digest
  * Redis digest was verified against the running container after an incorrect digest caused a failed pull
  * commit: `e1e24e4`
* Production follow-up:

  * automate controlled digest updates
  * add vulnerability/image scanning
  * review signed provenance where available
* How to verify:

  * inspect Dockerfile and `docker-compose.yml`
  * `docker compose -p barq-assessment pull`

## 6. Persistent data is separated from container lifecycle

* Risk and evidence: container-local PostgreSQL data would be destroyed during container recreation.
* Impact: data loss.
* Implemented fix / commit:

  * PostgreSQL uses named volume `postgres-data`
  * Redis uses named volume `redis-data`
  * Redis AOF persistence is enabled
  * PostgreSQL records were verified after container recreation
  * related commits: `ff478d7`, `e1e24e4`
* Production follow-up:

  * use replicated or managed data services
  * encrypt persistent storage
  * define durability and retention objectives
* How to verify:

  * inspect Compose volumes
  * recreate the PostgreSQL container without deleting volumes and verify existing records remain

## 7. Backups are tested by restoring them

* Risk and evidence: an untested backup may exist but be unusable during recovery.
* Impact: false confidence and possible unrecoverable data loss.
* Implemented fix / commit:

  * `backup.sh` creates a PostgreSQL dump
  * `restore.sh` restores into a separate test database
  * restore was verified with 10 recovered records
  * commit: `68d4856`
* Production follow-up:

  * store encrypted backups off-host
  * define retention and rotation
  * automate scheduled backups
  * perform recurring restore drills
* How to verify:

  * `./backup.sh`
  * `./restore.sh`
  * query the restored database

## 8. Resource consumption is bounded

* Risk and evidence: containers without CPU, memory or PID limits can consume excessive host resources.
* Impact: one service can degrade or deny service to the rest of the environment.
* Implemented fix / commit:

  * apps: 0.50 CPU, 256 MB memory, 128 PIDs
  * PostgreSQL: 0.50 CPU, 512 MB memory, 128 PIDs
  * Redis: 0.25 CPU, 128 MB memory, 64 PIDs
  * NGINX: 0.25 CPU, 128 MB memory, 64 PIDs
  * commit: `e1e24e4`
* Production follow-up: derive limits from load testing and production telemetry rather than lab assumptions.
* How to verify:

  * inspect `docker-compose.yml`
  * inspect container host configuration

## 9. Service health and readiness are explicitly checked

* Risk and evidence: routing traffic to a process that is running but cannot reach dependencies can produce avoidable failures.
* Impact: failed requests and slower recovery during dependency problems.
* Implemented fix / commit:

  * `/health` provides process liveness
  * `/ready` verifies real PostgreSQL and Redis operations
  * Compose healthchecks and health-aware dependencies are configured
  * validator uses bounded readiness checks
  * related commits: `4e6aeaa`, `86391bf`, `e1e24e4`
* Production follow-up:

  * add external health monitoring
  * collect metrics and alerts for readiness failures, dependency latency and error rates
* How to verify:

  * `curl http://127.0.0.1:8080/health`
  * `curl http://127.0.0.1:8080/ready`
  * `./validate.py`

## 10. Application availability survives one backend failure, but infrastructure single points of failure remain

* Risk and evidence: two Flask backends provide limited application redundancy, but NGINX, PostgreSQL, Redis and the Docker host are single instances.
* Impact: failure of one of those components can still make the service unavailable or remove state.
* Implemented fix / commit:

  * two Flask instances run behind NGINX
  * `failure_test.py` verifies continued HTTP availability while `app-02` is stopped and verifies it returns after recovery
  * commit: `2b9a9f4`
* Production follow-up:

  * multiple reverse-proxy/load-balancer instances
  * PostgreSQL replication/failover
  * Redis high availability where required
  * multi-host/orchestrated deployment
* How to verify:

  * run `./failure_test.py`
  * confirm 20/20 requests succeed while one backend is stopped

## 11. Logging and monitoring remain limited

* Risk and evidence: container logs and request IDs exist, but no centralized log collection, metrics platform or alerting system is implemented.
* Impact: incidents may be detected late and cross-service diagnosis becomes harder.
* Implemented fix / commit:

  * request IDs are returned and checked by validation
  * historical logs are analyzed separately as part of the assessment
* Production follow-up:

  * centralized structured logs
  * metrics and dashboards
  * alerting on latency, error rates, saturation and dependency failures
  * trace/request-ID propagation across services
* How to verify:

  * inspect response `X-Request-ID`
  * inspect Docker service logs
  * review `log_analysis.md`

## 12. CI verifies the tested environment but is not a complete security gate

* Risk and evidence: configuration regressions could be merged if they are not exercised automatically.
* Impact: broken networking, readiness or exposed ports could reach the main branch unnoticed.
* Implemented fix / commit:

  * CI runs on push and pull request
  * performs syntax/Compose checks, build, startup, bounded readiness wait and validation
  * successful run: `34737925277`
  * commit: `a2bf83e`
* Production follow-up:

  * add dependency and image vulnerability scanning
  * secret scanning
  * static analysis
  * policy checks for container/runtime configuration
* How to verify:

  * inspect `.github/workflows/ci.yml`
  * review the matching GitHub Actions run

## Summary of remaining production risks

The assessment implementation improves isolation, reproducibility, validation and recovery evidence, but it is still a single-host lab environment. The main remaining production gaps are high availability for NGINX/PostgreSQL/Redis, centralized monitoring, stronger secret management, encrypted/off-host backup handling, automated vulnerability scanning and production-derived capacity limits.
