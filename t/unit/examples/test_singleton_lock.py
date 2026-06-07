from examples.distributed_features.singleton import (
    LockAcquireResult,
    LockReleaseResult,
    RedisDistributedLock,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []
        self.delete_calls = []
        self.return_bytes = False

    def set(self, key, value, nx=False, ex=None):
        self.set_calls.append((key, value, nx, ex))
        if nx and key in self.values:
            return False

        self.values[key] = value
        return True

    def get(self, key):
        value = self.values.get(key)
        if self.return_bytes and isinstance(value, str):
            return value.encode()
        return value

    def delete(self, key):
        self.delete_calls.append(key)
        self.values.pop(key, None)


def test_acquire_uses_redis_set_nx_ex_and_stores_owner_token():
    redis_client = FakeRedis()
    lock = RedisDistributedLock(redis_client, 'inventory:sku-1', ttl=30)

    result = lock.acquire()

    assert result == LockAcquireResult.ACQUIRED
    assert redis_client.set_calls == [
        ('inventory:sku-1', lock.owner_token, True, 30),
    ]
    assert redis_client.values['inventory:sku-1'] == lock.owner_token


def test_second_worker_cannot_acquire_owned_lock():
    redis_client = FakeRedis()
    first = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-1',
    )
    second = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-2',
    )

    assert first.acquire() == LockAcquireResult.ACQUIRED
    assert second.acquire() == LockAcquireResult.NOT_ACQUIRED
    assert redis_client.values['inventory:sku-1'] == 'worker-1'


def test_release_fails_when_lock_is_owned_by_another_worker():
    redis_client = FakeRedis()
    owner = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-1',
    )
    other = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-2',
    )

    owner.acquire()

    assert other.release() == LockReleaseResult.NOT_OWNER
    assert redis_client.values['inventory:sku-1'] == 'worker-1'
    assert redis_client.delete_calls == []


def test_release_deletes_lock_when_owner_token_matches():
    redis_client = FakeRedis()
    lock = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-1',
    )

    lock.acquire()

    assert lock.release() == LockReleaseResult.RELEASED
    assert 'inventory:sku-1' not in redis_client.values
    assert redis_client.delete_calls == ['inventory:sku-1']


def test_release_accepts_bytes_owner_from_redis_client():
    redis_client = FakeRedis()
    redis_client.return_bytes = True
    lock = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-1',
    )

    lock.acquire()

    assert lock.release() == LockReleaseResult.RELEASED


def test_release_reports_not_owner_when_lock_is_missing():
    redis_client = FakeRedis()
    lock = RedisDistributedLock(
        redis_client,
        'inventory:sku-1',
        ttl=30,
        owner_token='worker-1',
    )

    assert lock.release() == LockReleaseResult.NOT_OWNER
