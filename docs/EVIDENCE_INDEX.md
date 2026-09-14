# Evidence and Submission Index

## Submission

- Repository URL: https://github.com/JRSallam28/barq
- Starting video commit: `3fa8caf3f5d6abcde3fb0db37c432b6b40dad213`
- Video implementation commit: `79719af`
- Final commit: TODO_AFTER_FINAL_DOCS_COMMIT
- Matching final CI run: TODO_AFTER_FINAL_GREEN_CI
- Continuous 12-18 minute video URL: TODO_ADD_VIDEO_URL
- Challenge receipt ID: `64797be527da43368122cb96e4216fed`
- Later documentation-only commit: TODO_AFTER_FINAL_DOCS_COMMIT

## Final demonstrated state

- Public port: `8090`
- Backends: `app-01`, `app-02`, `app-03`
- Reverse proxy: `nginx`
- Database: `postgres`
- Cache: `redis`

## Evidence map

| Requirement | File / Evidence | Video timestamp |
|---|---|---|
| Starting repository state | `git status`, starting commit above | TODO |
| Build and startup | `docker-compose.yml`, video terminal output | TODO |
| Required endpoints | `app/`, `validate.py` | TODO |
| Multiple backends | `/instance`, `app-01`, `app-02`, `app-03` | TODO |
| Failure and recovery | `failure_test.py` | TODO |
| PostgreSQL persistence | `/records`, named volume, `backup.sh`, `restore.sh` | TODO |
| Redis shared counter | `/counter`, Redis AOF volume | TODO |
| Historical log finding | `log_analysis.md` | TODO |
| Runtime challenge | `.assessment/challenge.json` | TODO |
| Live port change | final public port `8090` | TODO |
| Live app-03 addition | `docker-compose.yml`, `nginx/nginx.conf` | TODO |
| Final validation | `validate.py` -> `VALIDATION PASSED` | TODO |
| Commit and push | video implementation commit `79719af` | TODO |
| Final architecture | `architecture.dot`, `architecture.png` | N/A |
| Troubleshooting journal | `troubleshooting.md` | N/A |
| Security review | `security_review.md` | N/A |
| Decisions / trade-offs | `decisions.md` | N/A |
| AI disclosure | `AI_USAGE.md` | N/A |

## CI evidence

- Earlier successful CI: `34743086333`
- Post-video failed CI: `34780817420`
  - Cause: CI still used public port `8080` while the final validator used `8090`.
  - Fix documented in `troubleshooting.md`.
- Final green CI: TODO_AFTER_FINAL_PUSH

## Consistency check

The final README, Compose configuration, CI workflow, validator and architecture must all describe the same final state:

`8090 -> nginx -> app-01/app-02/app-03 -> PostgreSQL + Redis`
