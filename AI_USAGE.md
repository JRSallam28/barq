# AI usage disclosure

Write None if no AI was used. Otherwise record each use:

- Tool/model:
- Purpose:
- Files or decisions affected:
- What you changed or rejected:
- How you independently verified it:
- Related commit:

You may use AI and external resources. You must understand and demonstrate the work.


# AI usage disclosure

AI assistance was used during this assessment. All suggested changes were reviewed, executed, and verified manually before being committed.

## ChatGPT (GPT-5.6 Sol)

* Tool/model: ChatGPT, GPT-5.6 Sol
* Purpose:

  * troubleshoot Docker, Compose, NGINX, PostgreSQL and Redis issues
  * review runtime/network isolation decisions
  * help improve validation and failure-test logic
  * draft backup/restore scripts and CI workflow
  * help structure technical documentation
* Files or decisions affected:

  * `Dockerfile`
  * `docker-compose.yml`
  * `validate.py`
  * `failure_test.py`
  * `.env.example`
  * `backup.sh`
  * `restore.sh`
  * `.github/workflows/ci.yml`
  * `troubleshooting.md`
  * `decisions.md`
  * `security_review.md`
  * this `AI_USAGE.md`
* What I changed or rejected:

  * I did not accept suggestions without testing them.
  * An incorrect Redis image digest was detected when Docker rejected it; I recovered the exact digest from the running container and retested the pull and rebuild.
  * Network validation was corrected after noticing NGINX was incorrectly allowed on the backend network.
  * Backend instance validation was changed from a fixed request burst to a bounded retry window after reproducing a transient false failure.
  * Generated documentation was adjusted to match the actual commands, outputs, commits and observed behavior.
* How I independently verified it:

  * ran `docker compose config --quiet`
  * rebuilt and recreated the Compose environment
  * checked Docker container health and network membership
  * ran `./validate.py`
  * ran `./failure_test.py`
  * manually tested `/instance` through NGINX
  * created and restored a PostgreSQL backup and verified restored row count
  * checked `.env` ignore/tracking behavior with Git
  * ran syntax checks such as `python3 -m py_compile`, `bash -n` and `git diff --check`
  * pushed the repository and confirmed GitHub Actions run `34737925277` completed successfully
* Related commits:

  * `86391bf feat: add automated environment validation`
  * `2b9a9f4 feat: add failure and recovery test`
  * `e1e24e4 fix: harden runtime and enforce network isolation`
  * `332700b docs: add safe runtime environment example`
  * `68d4856 feat: add PostgreSQL backup and restore scripts`
  * `a2bf83e ci: validate environment on push and pull request`
  * later documentation commits
