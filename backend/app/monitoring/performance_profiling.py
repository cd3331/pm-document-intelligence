"""
Performance profiling and analysis tools
"""

import cProfile
import pstats
import io
from functools import wraps
import time
from typing import Callable, Any
from memory_profiler import profile as memory_profile


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        result = func(*args, **kwargs)

        profiler.disable()
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        stats.print_stats(20)  # Top 20 functions

        print(f"\n=== Profile for {func.__name__} ===")
        print(s.getvalue())

        return result

    return wrapper


def time_function(func: Callable) -> Callable:
    """Decorator to time function execution"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.4f} seconds")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.4f} seconds")
        return result

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
