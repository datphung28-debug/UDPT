from datetime import datetime, timezone

from examples.distributed_features.tasks import main, run_lock_demo, run_trace_demo
from examples.distributed_features.tracing import InMemoryTraceRecorder, TraceEvent


class FakeAsyncResult:
    def __init__(self, task_id, value):
        self.id = task_id
        self.value = value

    def get(self, timeout=None):
        return self.value


class FakeTask:
    def __init__(self, task_id, value):
        self.task_id = task_id
        self.value = value
        self.delay_calls = []

    def delay(self, *args, **kwargs):
        self.delay_calls.append((args, kwargs))
        return FakeAsyncResult(self.task_id, self.value)


def test_run_trace_demo_dispatches_task_and_prints_timeline(capsys):
    recorder = InMemoryTraceRecorder()
    recorder.record(
        TraceEvent(
            trace_id='trace-1',
            parent_task_id=None,
            task_id='process-order',
            worker_id='worker-process',
            event='started',
            logical_clock=1,
            timestamp=datetime(2026, 6, 7, 8, 0, tzinfo=timezone.utc),
        )
    )
    task = FakeTask('task-1', 'order-1 processed')

    output = run_trace_demo(
        order_id='order-1',
        trace_id='trace-1',
        task=task,
        recorder=recorder,
    )

    assert task.delay_calls == [(('order-1',), {'trace_id': 'trace-1'})]
    assert 'Task id: task-1' in output
    assert 'Result: order-1 processed' in output
    assert '[1] started process-order on worker-process' in output
    assert output == capsys.readouterr().out.rstrip()


def test_run_lock_demo_dispatches_two_inventory_tasks_for_same_product(capsys):
    task = FakeTask(
        'inventory-task',
        {'status': 'updated', 'product_id': 'sku-1', 'quantity': 5},
    )

    output = run_lock_demo(
        product_id='sku-1',
        task=task,
    )

    assert task.delay_calls == [
        ((), {'product_id': 'sku-1', 'quantity': 5, 'hold_seconds': 2}),
        ((), {'product_id': 'sku-1', 'quantity': 7, 'hold_seconds': 0}),
    ]
    assert 'First task id: inventory-task' in output
    assert 'Second result:' in output
    assert output == capsys.readouterr().out.rstrip()


def test_main_routes_trace_demo_command(monkeypatch):
    calls = []

    monkeypatch.setattr(
        'examples.distributed_features.tasks.run_trace_demo',
        lambda: calls.append('trace'),
    )

    main(['run-trace-demo'])

    assert calls == ['trace']


def test_main_routes_lock_demo_command(monkeypatch):
    calls = []

    monkeypatch.setattr(
        'examples.distributed_features.tasks.run_lock_demo',
        lambda: calls.append('lock'),
    )

    main(['run-lock-demo'])

    assert calls == ['lock']
