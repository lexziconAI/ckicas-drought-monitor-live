"""
NIWA DataHub Service - DEPRECATED
The NIWA DataHub API (d17fc0a885.execute-api.ap-southeast-2.amazonaws.com) is no longer active.
This service is disabled by default. For regional flow data, use TRC Hilltop SOS instead.
See drought_risk.py for the active implementation using fetch_trc_flow_data().
"""

import httpx
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../sidecar/.env")

logger = logging.getLogger(__name__)

# CIRCUIT BREAKER: NIWA DataHub is disabled by default
# The API endpoint returns 404 and is no longer operational
# Set NIWA_ENABLED=true in environment to re-enable (not recommended)
NIWA_ENABLED = os.getenv("NIWA_ENABLED", "false").lower() == "true"

NIWA_CUSTOMER_ID = os.getenv("NIWA_CUSTOMER_ID")
NIWA_API_KEY = os.getenv("NIWA_API_KEY")
NIWA_BASE_URL = "https://d17fc0a885.execute-api.ap-southeast-2.amazonaws.com/dev/api"

if not NIWA_ENABLED:
    logger.info("NIWA DataHub service is DISABLED (circuit breaker active). Use TRC Hilltop SOS for flow data.")

async def list_niwa_data_files(page: int = 1, limit: int = 50) -> Optional[dict]:
    """List available data files from NIWA DataHub"""

    # Circuit breaker - prevent 404 spam
    if not NIWA_ENABLED:
        return None

    if not NIWA_CUSTOMER_ID or not NIWA_API_KEY:
        logger.warning("NIWA credentials not configured")
        return None
    
    url = f"{NIWA_BASE_URL}/data-files"
    
    headers = {
        'X-Customer-ID': NIWA_CUSTOMER_ID,
        'Authorization': f'Bearer {NIWA_API_KEY}',
        'Accept': 'application/json'
    }
    
    params = {
        'page': page,
        'limit': limit,
        'includeMetadata': 'true'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"NIWA API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"NIWA fetch failed: {e}")
        return None


async def fetch_niwa_data_file(file_id: str) -> Optional[dict]:
    """Fetch a specific data file from NIWA DataHub"""

    # Circuit breaker - prevent 404 spam
    if not NIWA_ENABLED:
        return None

    if not NIWA_CUSTOMER_ID or not NIWA_API_KEY:
        return None
    
    url = f"{NIWA_BASE_URL}/data-files/{file_id}"
    
    headers = {
        'X-Customer-ID': NIWA_CUSTOMER_ID,
        'Authorization': f'Bearer {NIWA_API_KEY}',
        'Accept': 'application/json'
    }
    
    params = {
        'includeMetadata': 'true',
        'includeRaw': 'true'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"NIWA file fetch failed: {e}")
        return None
