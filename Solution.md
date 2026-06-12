# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`
1. **Hardcoded Secrets**: The API key (`sk-hardcoded-fake-key-never-do-this`) and Database URL (`postgresql://admin:password123@localhost:5432/mydb`) are hardcoded directly in the source code. If pushed to GitHub, this leaks credentials.
2. **No Config Management**: Configuration variables like `DEBUG = True` and `MAX_TOKENS = 500` are hardcoded rather than loaded dynamically from environment variables.
3. **Console Prints Instead of Structured Logging**: Using `print()` instead of a structured logger. It prints the API key in clear text to stdout, risking leaks to log aggregators.
4. **No Health / Readiness Probe Endpoints**: There are no `/health` or `/ready` endpoints, so container orchestrators/cloud platforms cannot monitor the application's health.
5. **Fixed Network Host & Port Binding**: It binds to `localhost` and a fixed port `8000`, with `reload=True`. It cannot receive external traffic inside a container, and `reload=True` consumes excessive resources in production.
6. **No Graceful Shutdown Handler**: There is no SIGTERM handler to finish in-flight requests before container termination.

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Why Important? |
| :--- | :--- | :--- | :--- |
| **Config** | Hardcoded in source code. | Loaded from environment variables via Pydantic Settings. | Prevents credential leaks; allows the same container image to run in dev, staging, and prod by changing env vars. |
| **Health Check**| None. | `/health` (Liveness) and `/ready` (Readiness) endpoints. | Allows orchestrators (Kubernetes, Railway) to know if a container has crashed and needs to be restarted, or if it is ready to receive traffic. |
| **Logging** | Plain `print()` statements. | Structured JSON logging. | Structured logs can be easily parsed, filtered, and queried by log management systems (e.g. Datadog, Loki). |
| **Shutdown** | Abrupt (SIGKILL/Ctrl+C without cleanup). | Graceful shutdown handler capturing `SIGTERM`. | Ensures in-flight requests complete before the process exits, and connections to databases/external systems are closed cleanly. |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image**: `python:3.11` (full Python distribution, ~1 GB).
2. **Working directory**: `/app`.
3. **Why COPY requirements.txt first?**: To take advantage of Docker's layer caching. Since dependencies change less frequently than code, caching the `pip install` layer speeds up subsequent builds.
4. **CMD vs ENTRYPOINT**: `CMD` sets a default command/parameters that can be overridden easily when running the container. `ENTRYPOINT` sets the executable that will always run, with `CMD` or CLI arguments appended as parameters.

### Exercise 2.3: Image size comparison
- **Develop Image (Single-stage, base `python:3.11`)**: `1.01 GB`
- **Production Image (Multi-stage, base `python:3.11-slim`)**: `148 MB`
- **Difference**: `85.3%` reduction. Multi-stage build copies only the installed packages and code from the builder stage, omitting compiler tools like gcc, apt caches, etc.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- **Public URL**: `https://agent-production-41ed.up.railway.app`
- **Screenshot**: [Deployment Dashboard](screenshots/dashboard.png)

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

#### Test API Key Authentication (Success / Failure):
```bash
# Test without key (should fail 401)
curl -i -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'

# Output:
# HTTP/1.1 401 Unauthorized
# {"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}

# Test with valid key (should succeed 200)
curl -i -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'

# Output:
# HTTP/1.1 200 OK
# {"question":"What is Docker?","answer":"[Mock LLM Response to: What is Docker?]","model":"gpt-4o-mini","timestamp":"2026-06-12T09:00:00Z"}
```

#### Test Rate Limiting (429 Triggered):
```bash
# Running curl requests rapidly
for i in {1..21}; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/ask \
    -H "X-API-Key: dev-key-change-me" \
    -H "Content-Type: application/json" \
    -d '{"question": "test"}'
done

# Output:
# 200
# ... (20 times)
# 429
```

### Exercise 4.4: Cost guard implementation
- **Approach**: The module `app/cost_guard.py` checks the cumulative daily budget spent by all requests. If Redis is available, it increments a key `cost:YYYY-MM-DD` float using `r_client.incrbyfloat`, setting a 2-day TTL. If it exceeds `settings.daily_budget_usd`, it raises a `503 Service Unavailable` block. If Redis is unavailable, it falls back to an in-memory variable `_daily_cost` that resets daily.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

1. **Health / Readiness Probes**: 
   - `/health` is a simple liveness check returning `{"status": "ok"}`.
   - `/ready` returns `{"ready": True}` only when `lifespan` startup has completed (setting `_is_ready = True`) and Redis connection is verified.
2. **Graceful Shutdown**:
   - Implemented a SIGTERM handler that sets `_is_ready = False` immediately so that Nginx Load Balancer stops forwarding traffic. Then it finishes outstanding requests before shutting down.
3. **Stateless Design**:
   - The application does not store user conversation logs or counters in local RAM. Rate limit sliding windows use Redis sorted sets (`zadd`/`zremrangebyscore`), and budget usage is tracked via Redis keys, making it horizontal-scale friendly.
4. **Nginx Load Balancing**:
   - Running `docker compose up --scale agent=3` starts 3 identical agent instances. Nginx routes traffic round-robin. If one instance goes down, Nginx retries the next instance seamlessly via `proxy_next_upstream`.
