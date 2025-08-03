# app/core/rate_limiter.py - Rate Limiting for External APIs
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for external API calls"""
    
    def __init__(self):
        self.request_times = defaultdict(deque)
        self.locks = defaultdict(asyncio.Semaphore)
        
        # Rate limits per service
        self.limits = {
            "bitscrunch": {
                "per_minute": settings.BITSCRUNCH_RATE_LIMIT_PER_MINUTE,
                "per_month": settings.BITSCRUNCH_RATE_LIMIT_PER_MONTH
            },
            "gemini": {
                "per_minute": 60,  # Conservative estimate
                "per_hour": 1000   # Conservative estimate
            }
        }
    
    async def acquire(self, service_name: str):
        """Acquire rate limit permission for a service"""
        if not settings.ENABLE_RATE_LIMITING:
            return
        
        async with self.locks[service_name]:
            await self._wait_for_rate_limit(service_name)
            self._record_request(service_name)
    
    async def _wait_for_rate_limit(self, service_name: str):
        """Wait until we can make a request within rate limits"""
        current_time = time.time()
        service_limits = self.limits.get(service_name, {})
        request_times = self.request_times[service_name]
        
        # Check minute-based limit
        per_minute = service_limits.get("per_minute")
        if per_minute:
            # Remove requests older than 1 minute
            cutoff_time = current_time - 60
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()
            
            # If we're at the limit, wait
            if len(request_times) >= per_minute:
                wait_time = 60 - (current_time - request_times[0])
                if wait_time > 0:
                    logger.info(f"Rate limit reached for {service_name}, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Remove the old request after waiting
                    request_times.popleft()
        
        # Check hour-based limit (if applicable)
        per_hour = service_limits.get("per_hour")
        if per_hour:
            cutoff_time = current_time - 3600  # 1 hour
            hour_requests = [t for t in request_times if t >= cutoff_time]
            
            if len(hour_requests) >= per_hour:
                wait_time = 3600 - (current_time - hour_requests[0])
                if wait_time > 0:
                    logger.info(f"Hourly rate limit reached for {service_name}, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
    
    def _record_request(self, service_name: str):
        """Record a request timestamp"""
        current_time = time.time()
        self.request_times[service_name].append(current_time)
        
        # Keep only last 100 requests to prevent memory issues
        if len(self.request_times[service_name]) > 100:
            self.request_times[service_name].popleft()
    
    def get_remaining_requests(self, service_name: str) -> Dict[str, int]:
        """Get remaining requests for a service"""
        current_time = time.time()
        service_limits = self.limits.get(service_name, {})
        request_times = self.request_times[service_name]
        
        # Clean old requests
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        
        minute_requests = [t for t in request_times if t >= cutoff_minute]
        hour_requests = [t for t in request_times if t >= cutoff_hour]
        
        return {
            "per_minute_remaining": max(0, service_limits.get("per_minute", 0) - len(minute_requests)),
            "per_hour_remaining": max(0, service_limits.get("per_hour", 0) - len(hour_requests))
        }