# Evidence and Submission Index

## Submission

- Repository URL: https://github.com/JRSallam28/barq
- Starting video commit: `3fa8caf3f5d6abcde3fb0db37c432b6b40dad213`
- Video implementation commit: `79719af`
- Final implementation/documentation commit: `f1c39fa`
- Matching implementation CI run: `34801568373`
- Continuous 12-18 minute video URL: https://drive.google.com/file/d/1Z7oHXBgChkhbAMPwwMoDLuDLF58HUoDE/view?usp=sharing
- Challenge receipt ID: `64797be527da43368122cb96e4216fed`
- Evidence-only metadata commit: repository HEAD on `main`
- Latest verified green CI before final evidence edit: `34803519400`

## Final demonstrated state

- Public port: `8090`
- Backends: `app-01`, `app-02`, `app-03`
- Reverse proxy: `nginx`
- Database: `postgres`
- Cache: `redis`

## Evidence map

| Requirement | File / Evidence | Video timestamp |
|---|---|---|
| Starting repository state | `git status`, starting commit above | See continuous video |
| Build and startup | `docker-compose.yml`, video terminal output | See continuous video |
| Required endpoints | `app/`, `validate.py` | See continuous video |
| Multiple backends | `/instance`, `app-01`, `app-02`, `app-03` | See continuous video |
| Failure and recovery | `failure_test.py` | See continuous video |
| PostgreSQL persistence | `/records`, named volume, `backup.sh`, `restore.sh` | See continuous video |
| Redis shared counter | `/counter`, Redis AOF volume | See continuous video |
| Historical log finding | `log_analysis.md` | See continuous video |
| Runtime challenge | `.assessment/challenge.json` | See continuous video |
| Live port change | final public port `8090` | See continuous video |
| Live app-03 addition | `docker-compose.yml`, `nginx/nginx.conf` | See continuous video |
| Final validation | `validate.py` -> `VALIDATION PASSED` | See continuous video |
| Commit and push | video implementation commit `79719af` | See continuous video |
| Final architecture | `architecture.dot`, `architecture.png` | N/A |
| Troubleshooting journal | `troubleshooting.md` | N/A |
| Security review | `security_review.md` | N/A |
| Decisions / trade-offs | `decisions.md` | N/A |
| AI disclosure | `AI_USAGE.md` | N/A |

## CI evidence

Final commit: f1c39fa
Matching final CI run: 34801568373
Continuous 12-18 minute video URL: <(https://drive.google.com/file/d/1Z7oHXBgChkhbAMPwwMoDLuDLF58HUoDE/view?usp=sharing)>
Later documentation-only commit: f1c39fa
Final green CI: 34801568373

## Consistency check

The final README, Compose configuration, CI workflow, validator and architecture must all describe the same final state:

`8090 -> nginx -> app-01/app-02/app-03 -> PostgreSQL + Redis`
