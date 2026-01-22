"""
Caching and Rate Limiting Utilities

Provides in-memory caching and rate limiting.
Note: For production, consider using Redis instead.

Author: AutoAssistGroup Development Team
"""

import time
from collections import defaultdict
from threading import Lock


# Thread-safe locks for cache operations
_cache_lock = Lock()
_rate_limit_lock = Lock()

# In-memory storage
_cache_storage = {}
_rate_limit_storage = defaultdict(list)


def cache_get(key, default=None):
    """
    Get value from cache.
    
    Args:
        key: Cache key
        default: Default value if key not found or expired
        
    Returns:
        Cached value or default
    """
    with _cache_lock:
        if key in _cache_storage:
            value, expires = _cache_storage[key]
            if time.time() < expires:
                return value
            else:
                # Clean up expired entry
                del _cache_storage[key]
        
        return default


def cache_set(key, value, expires_in=300):
    """
    Set value in cache with expiration.
    
    Args:
        key: Cache key
        value: Value to cache
        expires_in: Time to live in seconds (default 5 minutes)
    """
    with _cache_lock:
        expires_at = time.time() + expires_in
        _cache_storage[key] = (value, expires_at)


def cache_delete(key):
    """
    Delete a key from cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        bool: True if key was deleted, False if not found
    """
    with _cache_lock:
        if key in _cache_storage:
            del _cache_storage[key]
            return True
        return False


def cache_clear():
    """Clear all cached values."""
    with _cache_lock:
        _cache_storage.clear()


def rate_limit_check(key, limit=10, window=60):
    """
    Simple in-memory rate limiting.
    
    For production use, consider Redis-based rate limiting.
    
    Args:
        key: Identifier for rate limit (e.g., IP address, user ID)
        limit: Maximum requests allowed in window
        window: Time window in seconds
        
    Returns:
        bool: True if request should be allowed, False if rate limited
    """
    current_time = time.time()
    
    with _rate_limit_lock:
        # Remove old entries outside the window
        _rate_limit_storage[key] = [
            timestamp for timestamp in _rate_limit_storage[key]
            if current_time - timestamp < window
        ]
        
        # Check if limit exceeded
        if len(_rate_limit_storage[key]) >= limit:
            return False
        
        # Add current request timestamp
        _rate_limit_storage[key].append(current_time)
        return True


def rate_limit_remaining(key, limit=10, window=60):
    """
    Get remaining rate limit allowance.
    
    Args:
        key: Identifier for rate limit
        limit: Maximum requests allowed in window
        window: Time window in seconds
        
    Returns:
        int: Number of requests remaining in current window
    """
    current_time = time.time()
    
    with _rate_limit_lock:
        # Count requests in current window
        recent_requests = [
            timestamp for timestamp in _rate_limit_storage.get(key, [])
            if current_time - timestamp < window
        ]
        
        return max(0, limit - len(recent_requests))


def rate_limit_reset(key):
    """
    Reset rate limit for a key.
    
    Args:
        key: Identifier to reset
    """
    with _rate_limit_lock:
        if key in _rate_limit_storage:
            del _rate_limit_storage[key]
