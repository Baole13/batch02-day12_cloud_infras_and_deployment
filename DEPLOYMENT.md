# Deployment Information

## Public URL
https://agent-production-41ed.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl -i https://agent-production-41ed.up.railway.app/health
```
**Expected Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 124.5,
  "total_requests": 2,
  "checks": {
    "llm": "mock"
  },
  "timestamp": "2026-06-12T09:05:00.000000Z"
}
```

### API Test (with API Key Authentication)
```bash
curl -i -X POST https://agent-production-41ed.up.railway.app/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello Agent!"}'
```
**Expected Response:**
```json
{
  "question": "Hello Agent!",
  "answer": "[Mock LLM Response to: Hello Agent!]",
  "model": "gpt-4o-mini",
  "timestamp": "2026-06-12T09:05:05.123456Z"
}
```

### API Test (Failure without Key)
```bash
curl -i -X POST https://agent-production-41ed.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello Agent!"}'
```
**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid or missing API key. Include header: X-API-Key: <key>"
}
```

## Environment Variables Set
- `PORT` = `8000`
- `REDIS_URL` = `redis://default:password@redis-host:port`
- `AGENT_API_KEY` = `dev-key-change-me`
- `ENVIRONMENT` = `production`
- `DEBUG` = `false`

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
