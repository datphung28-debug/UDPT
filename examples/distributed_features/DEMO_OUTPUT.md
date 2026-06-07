# Distributed Features Demo Output

Captured on 2026-06-07 from `/home/admin/git/celery`.

## Unit Verification

```text
$ python -m pytest t/unit/examples/test_distributed_tracing.py -q
..........                                                               [100%]
10 passed in 0.05s

$ python -m pytest t/unit/examples/test_singleton_lock.py -q
...........                                                              [100%]
11 passed in 0.03s

$ python -m pytest t/unit/examples/test_distributed_demo_commands.py t/unit/examples/test_show_trace.py t/unit/examples/test_distributed_features_skeleton.py -q
.........                                                                [100%]
9 passed in 0.03s
```

## Manual Setup

Redis was started with Docker:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

Two workers were started in separate terminals:

```bash
celery -A examples.distributed_features.app worker -l INFO --pool=solo -n worker1@%h
celery -A examples.distributed_features.app worker -l INFO --pool=solo -n worker2@%h
```

Both workers registered the demo tasks:

```text
[tasks]
  . distributed_features.add
  . distributed_features.hello
  . distributed_features.process_order
  . distributed_features.update_inventory
```

## Trace Demo

Command:

```bash
python -m examples.distributed_features.tasks run-trace-demo
```

Output:

```text
Dispatching distributed_features.process_order('order-1')
Task id: c633a99b-b697-496f-88c9-3fb63bd86693
Result: order-1 processed
trace_id: order-1-trace
[1] started process-order on worker-process
[2] sent process-order on worker-process
[4] started validate-order on worker-validate parent=process-order
[5] success validate-order on worker-validate parent=process-order
[6] success process-order on worker-process
```

Worker evidence:

```text
Task distributed_features.process_order[c633a99b-b697-496f-88c9-3fb63bd86693] received
Task distributed_features.process_order[c633a99b-b697-496f-88c9-3fb63bd86693] succeeded in 0.006664443999397918s: 'order-1 processed'
```

## Singleton Lock Demo

Command:

```bash
python -m examples.distributed_features.tasks run-lock-demo
```

Output after adding a short dispatch gap so the first task acquires the lock:

```text
Dispatching two update_inventory tasks for sku-1
First task id: f3dd9517-4547-426f-a226-bbae294a3a37
Second task id: 6a1ba2f0-4b36-46e1-8c9e-e017906d48a0
First result: {'status': 'updated', 'product_id': 'sku-1', 'quantity': 5}
Second result: {'status': 'skipped', 'reason': 'lock_not_acquired', 'lock_key': 'inventory:sku-1'}
```

Worker evidence:

```text
Task distributed_features.update_inventory[f3dd9517-4547-426f-a226-bbae294a3a37] received
Task distributed_features.update_inventory[f3dd9517-4547-426f-a226-bbae294a3a37] succeeded in 2.0047192349993566s: {'status': 'updated', 'product_id': 'sku-1', 'quantity': 5}
Task distributed_features.update_inventory[6a1ba2f0-4b36-46e1-8c9e-e017906d48a0] received
Task distributed_features.update_inventory[6a1ba2f0-4b36-46e1-8c9e-e017906d48a0] succeeded in 0.0028664159999607364s: {'status': 'skipped', 'reason': 'lock_not_acquired', 'lock_key': 'inventory:sku-1'}
```

## Limitations

- The trace demo stores events in Redis as a simple list. It is enough for the course demo, but not a production tracing backend.
- Worker names inside trace events are fixed demo labels such as `worker-process` and `worker-validate`, not the actual Celery hostname.
- `RedisDistributedLock.release()` uses get-compare-delete. A production implementation should use a Redis Lua script to make ownership check and delete atomic.
- The lock demo uses a short dispatch gap before the second task so the first task reliably acquires the lock during presentation.
- The singleton task demo returns a skipped result instead of retrying automatically. Retry policy is left for a later extension.
