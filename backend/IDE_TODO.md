# URGENT: Outstanding Issues for Other IDE

**From**: Morning IDE Session
**To**: Current IDE
**Date**: 2025-11-21

---

## Critical Issues Still Unresolved

### 1. CORS Preflight Returning 400 (BLOCKING)

**Symptom**: Backend logs show:
```
OPTIONS /api/triggers/evaluate HTTP/1.1" 400 Bad Request
```

**Impact**: Browser cannot call POST `/api/triggers/evaluate` - completely blocked.

**Root Cause**: The CORS middleware in `main.py` isn't handling OPTIONS preflight for the trigger_engine router properly.

**Fix Required**:
Check `services/trigger_engine.py` - the router may need explicit OPTIONS handling or there's a conflict with how the router is mounted. The CORSMiddleware should handle this automatically, but something is blocking it.

Possible solutions:
- Ensure the trigger_engine router doesn't have its own middleware that intercepts OPTIONS
- Check if there's a route conflict between `routes/triggers.py` and `services/trigger_engine.py` (both use `/triggers` prefix)
- Add explicit OPTIONS handler if needed

---

### 2. Remove Mock Data from Trigger Evaluate

**Issue**: You reported trigger evaluate as "mocked" - this violates our canonical **No Mock Data** rule.

**Required**: The endpoint must:
1. Fetch real weather data for the specified region
2. Evaluate actual trigger conditions from the database
3. Return real evaluation results

The logic already exists in `services/trigger_engine.py` - use it, don't mock it.

---

### 3. ANTHROPIC_API_KEY Not Loading

**Issue**: The `backend/.env` file is missing `ANTHROPIC_API_KEY`.

**Impact**: Chat endpoint and weather narrative generation fail.

**Fix**: Add to `backend/.env`:
```
ANTHROPIC_API_KEY=<key from parent .env file>
```

Or fix the loading order in `chatbot.py` which loads env vars at module import time before FastAPI initializes.

---

### 4. Weather Narrative Uses Mock Data

**Location**: `api_routes.py` lines 437-464

**Issue**: The `generate_kaitiaki_wai_narrative()` function uses hardcoded values:
```python
current_data = {
    'region': region,
    'risk_score': 45,  # HARDCODED
    ...
}
```

**Fix**: Call the actual drought risk calculation function to get real data.

---

### 5. Cache Implementation Bug

**Location**: `api_routes.py` ~line 521

**Issue**: Cache initialized with `{"narrative": None, "timestamp": None}` but checks for dynamic keys like `narrative_Taranaki` - will never hit cache.

---

## Priority Order

1. **CORS OPTIONS 400** - Fix first, it's blocking functionality
2. **Remove mock data** from trigger evaluate
3. **API key loading** for chat/narrative
4. **Narrative real data** - replace mock values
5. **Cache fix** - lower priority

---

## Verification Commands

After fixes, test with:

```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:9101/api/triggers/evaluate \
  -H "Origin: http://localhost:3002" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Should return 200 with CORS headers, NOT 400

# Test trigger evaluate
curl -X POST http://localhost:9101/api/triggers/evaluate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "weather_data": {"temp": 28, "rainfall": 1, "humidity": 45, "wind_speed": 20}}'

# Test chat
curl -X POST http://localhost:9101/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the drought risk in Taranaki?"}'

# Test narrative
curl http://localhost:9101/api/public/weather-narrative
```

---

## Canonical Rules Reminder

1. **No Mock Data** - All endpoints must return real data or proper errors
2. **Diagnose Before Acting** - Understand root cause before fixing
3. **Test Incrementally** - Verify each fix before moving to next
4. **Update Handoff** - Document what you fixed in `IDE_HANDOFF.md`

---

Good work on the graceful degradation! Now let's get these core issues resolved.
