"""
时光印记 - 缓存工具
TTL 缓存装饰器
"""
import time
from functools import wraps


def ttl_cache(ttl=3600):
    """
    TTL 缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
    """
    def decorator(func):
        cache = {'value': None, 'timestamp': 0}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if cache['value'] is not None and (current_time - cache['timestamp']) < ttl:
                return cache['value']
            
            result = func(*args, **kwargs)
            cache['value'] = result
            cache['timestamp'] = current_time
            return result
        
        return wrapper
    return decorator
