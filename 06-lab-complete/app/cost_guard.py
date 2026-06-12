import time
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
    _daily_cost = 0.0
    _cost_reset_day = time.strftime("%Y-%m-%d")

# Price per 1k tokens (GPT-4o-mini rates)
PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

def get_daily_cost() -> float:
    global _daily_cost, _cost_reset_day
    today = time.strftime("%Y-%m-%d")
    if USE_REDIS:
        try:
            cost_str = r_client.get(f"cost:{today}")
            return float(cost_str) if cost_str else 0.0
        except Exception:
            return 0.0
    else:
        if today != _cost_reset_day:
            _daily_cost = 0.0
            _cost_reset_day = today
        return _daily_cost

def check_and_record_cost(input_tokens: int, output_tokens: int):
    global _daily_cost, _cost_reset_day
    today = time.strftime("%Y-%m-%d")
    current_cost = get_daily_cost()
    
    if current_cost >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=503, 
            detail="Daily budget exhausted. Try tomorrow."
        )
        
    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    
    if USE_REDIS:
        try:
            pipe = r_client.pipeline()
            key = f"cost:{today}"
            pipe.incrbyfloat(key, cost)
            pipe.expire(key, 86400 * 2) # keep for 2 days
            pipe.execute()
        except Exception:
            pass
    else:
        _daily_cost += cost
