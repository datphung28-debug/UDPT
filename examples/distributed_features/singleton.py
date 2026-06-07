from functools import wraps
from inspect import signature
from enum import Enum
from uuid import uuid4


class LockAcquireResult(str, Enum):
    ACQUIRED = 'acquired'
    NOT_ACQUIRED = 'not_acquired'


class LockReleaseResult(str, Enum):
    RELEASED = 'released'
    NOT_OWNER = 'not_owner'


class RedisDistributedLock:
    def __init__(self, redis_client, key, ttl, owner_token=None):
        self.redis_client = redis_client
        self.key = key
        self.ttl = ttl
        self.owner_token = owner_token or str(uuid4())

    def acquire(self):
        acquired = self.redis_client.set(
            self.key,
            self.owner_token,
            nx=True,
            ex=self.ttl,
        )

        if acquired:
            return LockAcquireResult.ACQUIRED

        return LockAcquireResult.NOT_ACQUIRED

    def release(self):
        current_owner = self.redis_client.get(self.key)

        if self._decode(current_owner) != self.owner_token:
            return LockReleaseResult.NOT_OWNER

        self.redis_client.delete(self.key)
        return LockReleaseResult.RELEASED

    def _decode(self, value):
        if isinstance(value, bytes):
            return value.decode()
        return value


def singleton_task(lock_key_template, ttl, redis_client_factory):
    def decorator(func):
        task_signature = signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            bound_arguments = task_signature.bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            lock_key = lock_key_template.format(**bound_arguments.arguments)
            lock = RedisDistributedLock(
                redis_client_factory(),
                lock_key,
                ttl,
            )
            wrapper.lock = lock

            if lock.acquire() != LockAcquireResult.ACQUIRED:
                return {
                    'status': 'skipped',
                    'reason': 'lock_not_acquired',
                    'lock_key': lock_key,
                }

            try:
                return func(*args, **kwargs)
            finally:
                lock.release()

        wrapper.lock = None
        return wrapper

    return decorator
