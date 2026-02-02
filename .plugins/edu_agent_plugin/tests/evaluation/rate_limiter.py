"""
Rate Limiter for LLM API Calls

Implements a simple sliding window rate limiter for requests per minute (RPM).
Optionally tracks tokens per minute (TPM) and requests per day (RPD).
"""
import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """
    Async-compatible rate limiter using sliding window algorithm.
    
    Attributes:
        rpm: Maximum requests per minute (0 = disabled)
        tpm: Maximum tokens per minute (0 = disabled, not currently enforced)
        rpd: Maximum requests per day (0 = disabled)
    """
    
    def __init__(
        self,
        rpm: int = 0,
        tpm: int = 0,
        rpd: int = 0,
    ):
        """
        Initialize the rate limiter.
        
        Args:
            rpm: Requests per minute limit (0 to disable)
            tpm: Tokens per minute limit (0 to disable, tracked but not enforced)
            rpd: Requests per day limit (0 to disable)
        """
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        
        # Sliding window for RPM (stores timestamps)
        self._minute_window: deque = deque()
        
        # Daily counter
        self._day_start: float = time.time()
        self._day_count: int = 0
        
        # Whether rate limiting is enabled
        self.enabled = rpm > 0 or rpd > 0
        
        if self.enabled:
            print(f"[RateLimiter] Enabled with RPM={rpm}, TPM={tpm}, RPD={rpd}")
    
    async def acquire(self) -> None:
        """
        Wait until a request can be made without exceeding rate limits.
        
        Call this before making an API request.
        """
        if not self.enabled:
            return
        
        now = time.time()
        
        # Check and enforce RPM limit
        if self.rpm > 0:
            # Remove timestamps older than 60 seconds
            while self._minute_window and (now - self._minute_window[0]) > 60:
                self._minute_window.popleft()
            
            # If at limit, wait until oldest request expires
            if len(self._minute_window) >= self.rpm:
                wait_time = 60 - (now - self._minute_window[0])
                if wait_time > 0:
                    print(f"[RateLimiter] RPM limit reached, waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time + 0.1)  # Small buffer
                    # Clean up again after waiting
                    now = time.time()
                    while self._minute_window and (now - self._minute_window[0]) > 60:
                        self._minute_window.popleft()
        
        # Check RPD limit
        if self.rpd > 0:
            # Reset daily counter if new day
            if (now - self._day_start) > 86400:  # 24 hours
                self._day_start = now
                self._day_count = 0
            
            if self._day_count >= self.rpd:
                print(f"[RateLimiter] Daily limit reached ({self.rpd} requests)")
                raise RuntimeError(f"Daily rate limit exceeded ({self.rpd} requests)")
        
        # Record this request
        self._minute_window.append(now)
        if self.rpd > 0:
            self._day_count += 1
    
    def get_stats(self) -> dict:
        """Returns current rate limiter statistics."""
        now = time.time()
        
        # Clean minute window
        while self._minute_window and (now - self._minute_window[0]) > 60:
            self._minute_window.popleft()
        
        return {
            "rpm_current": len(self._minute_window),
            "rpm_limit": self.rpm,
            "rpd_current": self._day_count,
            "rpd_limit": self.rpd,
            "enabled": self.enabled,
        }


def create_rate_limiter(llm_config: dict) -> RateLimiter:
    """
    Creates a rate limiter from LLM config.
    
    Args:
        llm_config: Dict with rate_limit_rpm, rate_limit_tpm, rate_limit_rpd
        
    Returns:
        RateLimiter instance (may be disabled if no limits set)
    """
    return RateLimiter(
        rpm=llm_config.get("rate_limit_rpm", 0),
        tpm=llm_config.get("rate_limit_tpm", 0),
        rpd=llm_config.get("rate_limit_rpd", 0),
    )
