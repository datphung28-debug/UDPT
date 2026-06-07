# Distributed Features Demo

This example is the course project workspace for two Celery distributed-system
features:

1. Distributed task tracing with logical clocks.
2. Singleton task execution with a Redis-backed distributed lock.

Task 1 provides only the runnable demo skeleton. Later tasks add tracing,
logical-clock event recording, and singleton locking.

## Prerequisites

- Python environment with Celery dependencies installed.
- Redis running locally on port `6379`.

The demo uses Redis database `0` as the broker and Redis database `1` as the
result backend.

## Start Redis

```bash
redis-server
```

If Redis is already running, keep using the existing process.

## Start A Worker

From the repository root:

```bash
celery -A examples.distributed_features.app worker -l INFO
```

For later multi-worker demos, start named workers in separate terminals:

```bash
celery -A examples.distributed_features.app worker -l INFO -n worker1@%h
celery -A examples.distributed_features.app worker -l INFO -n worker2@%h
```

## Run The Basic Task Demo

In another terminal:

```bash
python -m examples.distributed_features.tasks
```

Expected output shape:

```text
Sending distributed_features.add(2, 3)
Task id: <uuid>
Result: 5
```

## Run The Trace Timeline Demo

Start Redis and a worker first. Then dispatch the traced order workflow with a
trace id:

```bash
python - <<'PY'
from examples.distributed_features.tasks import process_order

result = process_order.delay('order-1', trace_id='order-1-trace')
print(result.get(timeout=10))
PY
```

Print the timeline stored in Redis:

```bash
python examples/distributed_features/show_trace.py order-1-trace
```

Expected output shape:

```text
trace_id: order-1-trace
[1] started process-order on worker-process
[2] sent process-order on worker-process
[4] started validate-order on worker-validate parent=process-order
[5] success validate-order on worker-validate parent=process-order
[6] success process-order on worker-process
```

## Files

- `app.py`: Celery application and Redis configuration.
- `tasks.py`: Basic tasks used to verify the demo app skeleton.
- `tracing.py`: Trace context, event models, and trace recorders.
- `show_trace.py`: CLI for printing a compact trace timeline.
