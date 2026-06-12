import time
import uuid
from fastapi import HTTPException
from app.config import settings

# Initialize Redis client if redis_url is set
import redis
try:
    if settings.redis_url:
        r_client = redis.from_url(settings.redis_url, decode_responses=True)
        r_client.ping()
        USE_REDIS = True
    else:
        USE_REDIS = False
except Exception:
    USE_REDIS = False

if not USE_REDIS:
    from collections import defaultdict, deque
    _rate_windows: dict[str, deque] = defaultdict(deque)

def check_rate_limit(key: str):
    now = time.time()
    limit = settings.rate_limit_per_minute
    if USE_REDIS:
        # Use Redis sorted set for sliding window
        redis_key = f"rate_limit:{key}"
        # Remove elements older than 60 seconds
        pipe = r_client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - 60)
        pipe.zcard(redis_key)
        results = pipe.execute()
        current_requests = results[1]
        if current_requests >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} req/min",
                headers={"Retry-After": "60"},
            )
        # Add current request with a unique value (member) to avoid collision
        pipe = r_client.pipeline()
        pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex}": now})
        pipe.expire(redis_key, 60)
        pipe.execute()
    else:
        window = _rate_windows[key]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} req/min",
                headers={"Retry-After": "60"},
            )
        window.append(now)
