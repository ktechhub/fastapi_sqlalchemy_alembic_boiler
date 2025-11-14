"""
Session utility functions for extracting client information.
"""

import re
from typing import Dict, Optional
from fastapi import Request
from user_agents import parse as parse_user_agent
import httpx
from ..core.config import settings
from ..services.redis_base import client as redis_client
from ..core.loggers import app_logger as logger


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    Handles X-Forwarded-For, X-Real-IP headers for proxy/load balancer scenarios.
    """
    # Check X-Forwarded-For header (first IP in chain)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def parse_user_agent_string(user_agent: str) -> Dict[str, Optional[str]]:
    """
    Parse user agent string to extract browser, OS, and device information.

    Returns:
        {
            "browser": "Chrome",
            "browser_version": "120.0.0.0",
            "os": "Mac OS X",
            "os_version": "10.15.7",
            "device_type": "Desktop"
        }
    """
    if not user_agent:
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "os_version": None,
            "device_type": None,
        }

    try:
        ua = parse_user_agent(user_agent)

        # Determine device type
        device_type = "Desktop"
        if ua.is_mobile:
            device_type = "Mobile"
        elif ua.is_tablet:
            device_type = "Tablet"

        return {
            "browser": ua.browser.family if ua.browser else None,
            "browser_version": (
                f"{ua.browser.version_string}"
                if ua.browser and ua.browser.version_string
                else None
            ),
            "os": ua.os.family if ua.os else None,
            "os_version": (
                f"{ua.os.version_string}" if ua.os and ua.os.version_string else None
            ),
            "device_type": device_type,
        }
    except Exception as e:
        logger.error(f"Error parsing user agent '{user_agent}': {e}")
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "os_version": None,
            "device_type": None,
        }


async def get_location_from_ip(ip: str) -> Dict[str, Optional[str]]:
    """
    Get location information from IP address.
    Uses cached results from Redis to avoid repeated API calls.

    Returns:
        {
            "city": "Munich",
            "region": "Bavaria",
            "country": "DE",
            "country_name": "Germany"
        }
    """
    # Skip localhost/private IPs
    if (
        ip in ["127.0.0.1", "::1", "localhost", "unknown"]
        or ip.startswith("192.168.")
        or ip.startswith("10.")
    ):
        return {
            "city": None,
            "region": None,
            "country": None,
            "country_name": None,
        }

    # Check Redis cache first
    cache_key = f"ip:location:{ip}"
    cached_location = redis_client.get(cache_key)
    if cached_location:
        import json

        return json.loads(cached_location)

    # Fetch from API (using ip-api.com free tier)
    location_data = {
        "city": None,
        "region": None,
        "country": None,
        "country_name": None,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Using ip-api.com (free tier: 45 req/min)
            response = await client.get(f"http://ip-api.com/json/{ip}")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    location_data = {
                        "city": data.get("city"),
                        "region": data.get("regionName"),
                        "country": data.get("countryCode"),
                        "country_name": data.get("country"),
                    }

                    # Cache for 24 hours
                    import json

                    redis_client.setex(cache_key, 86400, json.dumps(location_data))
    except Exception as e:
        logger.error(f"Error fetching location for IP {ip}: {e}")
        # Return empty location data on error

    return location_data
