# Log analysis

Use all three supplied logs. Answer every question with commands/scripts and actual output.

1. What UTC interval is covered? How many valid, malformed and duplicate lines are in each file?
2. How many distinct client requests occurred? How did you deduplicate and avoid counting retries twice?
3. What are the final client status counts and error rate? State your denominator.
4. Which paths, time windows and backends account for the failures?
5. What are the median and p95 client latencies? State the percentile method and units.
6. Which requests retried upstream? How many succeeded after retrying?
7. Build an incident timeline using evidence from access, error AND application logs.
8. Show one correlated failed request and one successful request. Include IDs and timestamps.
9. Which errors appear to be proxy/connectivity issues versus dependency/application issues? What proves it?
10. What do the logs not prove? What would you check next in a running environment?

## Commands / scripts
## Results
## Timeline and correlated examples
## Conclusions and limits

# Log analysis

The three historical logs were analyzed without modifying the originals:

* `logs/access.log`
* `logs/application.log`
* `logs/error.log`

The logs describe a historical training incident and are separate from the current repaired runtime.

## 1. UTC interval, valid lines, malformed lines and duplicates

### Access log

* Total lines: 726
* Valid JSON request lines: 725
* Malformed lines: 1
* Exact duplicate lines: 5
* First timestamp: `2026-08-20T11:00:00.015Z`
* Last timestamp: `2026-08-20T11:29:57.578Z`

### Application log

* Total lines: 730
* Valid JSON lines: 729
* Malformed lines: 1
* Exact duplicate lines: 2
* First timestamp: `2026-08-20T11:00:00.015Z`
* Last timestamp: `2026-08-20T11:29:57.578Z`

The 729 valid application lines contain:

* 682 `http_request` events
* 47 `dependency_error` events

### NGINX error log

* Total lines: 68
* Request-related error lines: 67
* Additional valid NGINX notice lines: 1
* Exact duplicate lines: 0
* Malformed lines: 0 based on the general NGINX text format
* First request error: `2026/08/20 11:05:02`
* Last request error: `2026/08/20 11:26:47`
* Final non-error line: a log-rotation notice at `11:30:00`

The earlier request-specific parser classified the notice as non-valid because it did not contain a `request_id`; I do not treat that valid NGINX notice as a malformed log line.

### Overall time range

The client access record covers approximately:

`2026-08-20 11:00:00 UTC` through `2026-08-20 11:29:57 UTC`.

## 2. Distinct client requests and deduplication

The access log contains:

* 725 valid access lines
* 720 distinct `request_id` values
* 5 request IDs with multiple access lines
* all 5 duplicated request IDs are exact duplicates
* 0 conflicting duplicate request IDs

Therefore the correct client-request denominator is **720 distinct requests**, not 725 access-log lines.

I deduplicated by `request_id` only after confirming that repeated access records were exact copies. This avoids counting duplicated log lines as additional client traffic.

Upstream retries were not counted as additional client requests. A request such as:

`upstream_status="502, 200"`

represents one client request that made multiple upstream attempts, not two client requests.

## 3. Final client status counts and error rate

After deduplicating by `request_id`, the final status counts are:

| Final status | Requests |
| ------------ | -------: |
| 200          |      615 |
| 404          |       10 |
| 502          |       40 |
| 503          |       47 |
| 504          |        8 |
| **Total**    |  **720** |

There were:

* 95 final 5xx responses
* denominator: 720 distinct client requests

Therefore:

**5xx client error rate = 95 / 720 = 13.19%**

The 10 client-visible 404 responses are reported separately and are not included in the 5xx incident error rate.

## 4. Paths, time windows and backends responsible for failures

### 5xx failures by path

| Path       | 5xx count |
| ---------- | --------: |
| `/records` |        26 |
| `/counter` |        26 |
| `/ready`   |        23 |
| `/health`  |        10 |
| `/`        |        10 |

### Failures by path and final status

| Path       | Status | Count |
| ---------- | -----: | ----: |
| `/`        |    502 |    10 |
| `/counter` |    502 |    10 |
| `/counter` |    503 |    16 |
| `/health`  |    502 |    10 |
| `/ready`   |    503 |    23 |
| `/records` |    502 |    10 |
| `/records` |    503 |     8 |
| `/records` |    504 |     8 |

### 5xx failures by five-minute UTC window

| Window start | 5xx requests |
| ------------ | -----------: |
| 11:05        |           40 |
| 11:10        |           23 |
| 11:15        |            8 |
| 11:20        |           16 |
| 11:25        |            8 |

This shows several distinct incident phases rather than one continuous failure.

### Backend concentration

Among the 95 final 5xx responses:

* `172.23.0.12:8080`: 68
* `172.23.0.11:8080`: 27

The historical application mapping shows these backends as the two Flask instances, with failures concentrated more heavily on the backend represented by `172.23.0.12`.

The first final 5xx request was:

* timestamp: `2026-08-20T11:05:02.503Z`
* request: `lab-000122`
* path: `/health`
* final status: 502
* upstream: `172.23.0.12:8080`

The final 5xx request was:

* timestamp: `2026-08-20T11:26:47.001Z`
* request: `lab-000643`
* path: `/records`
* final status: 504
* upstream: `172.23.0.11:8080`

## 5. Median and p95 client latency

Latency was calculated from the 720 deduplicated client requests using `request_time`.

`request_time` is stored in seconds and was converted to milliseconds.

Results:

* samples: 720
* median: **54 ms**
* p95: **2001 ms**

Methods:

* median: standard midpoint median for the even-sized sample
* p95: nearest-rank percentile, using rank `ceil(0.95 * N)`

The p95 near two seconds is consistent with the dependency timeout and upstream timeout periods visible elsewhere in the logs.

## 6. Upstream retries

Nineteen deduplicated access records contain multiple upstream attempts.

Results:

* retried client requests: 19
* succeeded after retry: 19
* failed after retry: 0
* final retry status counts: `{200: 19}`

Example:

`lab-000124`:

* path: `/ready`
* first upstream: `172.23.0.12:8080`
* first upstream status: 502
* retry upstream: `172.23.0.11:8080`
* retry status: 200
* final client status: 200

The same pattern appears on other request IDs such as `lab-000130`, `lab-000136`, and `lab-000142`.

This also explains why NGINX recorded more connection failures than the number of final 502 client responses. Some upstream connection failures were hidden from the client by a successful retry.

## 7. Incident timeline

### 11:00:00 UTC — normal traffic

The logs begin with normal application traffic.

Example successful request:

`lab-000002`

* access log:

  * `2026-08-20T11:00:02.532Z`
  * `GET /health`
  * final status 200
  * upstream `172.23.0.12:8080`
  * latency 32 ms
* application log:

  * same request ID
  * `app-02`
  * status 200
  * duration 32 ms
* error log:

  * no corresponding NGINX error

### 11:05:02–11:09:57 UTC — upstream connection-refused incident

NGINX recorded:

* 59 `connect() failed (111: Connection refused)` events
* first: `11:05:02`
* last: `11:09:57`

The first event was:

`lab-000122 GET /health`

toward:

`172.23.0.12:8080`

This phase produced final 502 responses, but some client requests were recovered by NGINX retrying the other application backend.

There were 19 successful retry cases overall.

### 11:12:09–11:15:52 UTC — Redis dependency incident

The application log contains:

* 31 `dependency_error` events
* dependency: `redis`
* first: `2026-08-20T11:12:09.524Z`
* last: `2026-08-20T11:15:52.024Z`

Both `app-01` and `app-02` reported Redis failures.

These errors produced application-generated 503 responses, particularly on dependency-aware endpoints such as `/ready` and Redis-backed `/counter`.

### 11:20:07–11:21:45 UTC — PostgreSQL dependency incident

The application log contains:

* 16 `dependency_error` events
* dependency: `postgres`
* first: `2026-08-20T11:20:07.540Z`
* last: `2026-08-20T11:21:45.040Z`

Both application instances were affected.

PostgreSQL-related failures appear on `/ready` and `/records`.

### 11:25:14–11:26:47 UTC — upstream timeout incident

NGINX recorded:

* 8 `upstream timed out` events
* first: `11:25:14`
* last: `11:26:47`

The client-visible result was eight 504 responses.

The final request-related error was:

`lab-000643`

* `GET /records`
* upstream `172.23.0.11:8080`
* NGINX: upstream timed out while reading response header
* final client status: 504

### 11:30:00 UTC — log rotation

The final `error.log` line is a NGINX notice indicating that the log collector rotated the stream.

It is not an application failure.

## 8. Correlated failed and successful requests

### Failed application/dependency request: `lab-000292`

Access log:

* timestamp: `2026-08-20T11:12:09.525Z`
* path: `/ready`
* upstream: `172.23.0.12:8080`
* upstream status: 503
* final status: 503
* request time: 2.025 seconds

Application log:

* timestamp: `2026-08-20T11:12:09.524Z`
* instance: `app-02`
* event: `dependency_error`
* dependency: `redis`
* error type: `TimeoutError`

The application then logged the same request:

* path: `/ready`
* status: 503
* duration: 2025 ms

NGINX error log:

* no matching NGINX connectivity error for this request

Conclusion: this was an application-visible Redis dependency failure, not an NGINX connection failure.

### Successful request: `lab-000002`

Access log:

* timestamp: `2026-08-20T11:00:02.532Z`
* path: `/health`
* upstream: `172.23.0.12:8080`
* final status: 200
* latency: 32 ms

Application log:

* same request ID
* instance: `app-02`
* path: `/health`
* status: 200
* duration: 32 ms

NGINX error log:

* no corresponding error

The matching request ID, timestamp, backend and duration provide cross-log correlation.

## 9. Proxy/connectivity errors versus dependency/application errors

The logs show distinct failure classes.

### Proxy/connectivity failures

NGINX recorded:

* 59 connection-refused events
* 8 upstream timeout events

Evidence of proxy/upstream connectivity failure includes messages such as:

`connect() failed (111: Connection refused) while connecting to upstream`

and:

`upstream timed out ... while reading response header from upstream`

These errors explain the client-visible 502 and 504 responses.

The 19 successful NGINX retries prove that some first-attempt upstream failures were recovered before reaching the client.

### Dependency/application failures

The application log recorded exactly 47 `dependency_error` events:

* Redis: 31
* PostgreSQL: 16

The access log contains exactly 47 final 503 responses.

Application 503 breakdown:

* `app-01 /counter`: 8
* `app-01 /ready`: 11
* `app-01 /records`: 4
* `app-02 /counter`: 8
* `app-02 /ready`: 12
* `app-02 /records`: 4

The exact 47-to-47 relationship, plus matching request IDs such as `lab-000292`, supports the conclusion that the final 503 responses were dependency/application failures rather than proxy connection failures.

## 10. What the logs do not prove

These historical logs show symptoms and correlations, but they do not prove the underlying infrastructure root cause of every incident.

For example, `Connection refused` proves that NGINX could not establish a connection to an upstream endpoint at that time. It does not by itself prove whether the container was stopped, restarting, unhealthy, listening on the wrong interface, or affected by another runtime condition.

Similarly, a Redis or PostgreSQL timeout proves the application failed to complete that dependency operation, but not whether the cause was:

* service outage
* networking
* resource saturation
* connection-pool exhaustion
* lock/contention
* storage latency
* deliberate fault injection

In a live environment I would next inspect:

* `docker compose ps`
* container health state and restart counts
* container logs around each incident window
* Docker network membership
* CPU/memory/PID usage
* PostgreSQL connection/activity statistics
* Redis latency and persistence status
* NGINX upstream state
* application connection-pool metrics
* host resource pressure

The historical logs are therefore strong evidence for the observed failure modes and timeline, but not a complete substitute for live runtime telemetry.

## Commands / scripts

Examples of reproducible commands used during analysis:

```bash
wc -l logs/access.log logs/application.log logs/error.log

head -n 5 logs/access.log
head -n 5 logs/application.log
head -n 5 logs/error.log
```

Python was used to:

* parse the two JSONL logs
* identify malformed lines
* detect exact duplicate lines
* deduplicate client requests by `request_id`
* calculate final status counts
* calculate the 5xx rate
* calculate median and nearest-rank p95 latency
* identify requests with multiple upstream attempts
* count successful retries
* aggregate failures by path, backend and five-minute window
* correlate access, application and NGINX error records by `request_id`

The original log files were not modified.

## Conclusions

The historical incident contains multiple distinct phases rather than one root cause:

1. upstream connection refusal beginning at 11:05 UTC
2. Redis dependency timeouts beginning at 11:12 UTC
3. PostgreSQL dependency errors beginning at 11:20 UTC
4. upstream response timeouts beginning at 11:25 UTC

NGINX retries successfully protected 19 client requests from an initial upstream failure.

The final client 5xx rate was **13.19%**, using **720 distinct client requests** as the denominator.

The s
