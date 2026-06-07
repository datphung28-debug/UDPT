from datetime import datetime, timezone

from examples.distributed_features.tracing import (
    TraceContext,
    TraceEvent,
    create_child_context,
    create_trace_context,
    next_logical_clock,
)


def test_create_trace_context_builds_root_context():
    context = create_trace_context(task_id='root-task', worker_id='worker-1')

    assert isinstance(context, TraceContext)
    assert context.trace_id
    assert context.parent_task_id is None
    assert context.task_id == 'root-task'
    assert context.worker_id == 'worker-1'
    assert context.logical_clock == 0


def test_create_child_context_inherits_trace_id_and_advances_clock():
    parent = create_trace_context(
        trace_id='trace-1',
        task_id='parent-task',
        worker_id='worker-1',
        logical_clock=3,
    )

    child = create_child_context(
        parent,
        task_id='child-task',
        worker_id='worker-2',
    )

    assert child.trace_id == 'trace-1'
    assert child.parent_task_id == 'parent-task'
    assert child.task_id == 'child-task'
    assert child.worker_id == 'worker-2'
    assert child.logical_clock == 4


def test_next_logical_clock_is_monotonic():
    assert next_logical_clock(0) == 1
    assert next_logical_clock(4) == 5


def test_trace_event_contains_required_fields():
    timestamp = datetime(2026, 6, 7, 8, 0, tzinfo=timezone.utc)
    event = TraceEvent(
        trace_id='trace-1',
        parent_task_id='parent-task',
        task_id='child-task',
        worker_id='worker-2',
        event='started',
        logical_clock=5,
        timestamp=timestamp,
    )

    assert event.to_dict() == {
        'trace_id': 'trace-1',
        'parent_task_id': 'parent-task',
        'task_id': 'child-task',
        'worker_id': 'worker-2',
        'event': 'started',
        'logical_clock': 5,
        'timestamp': '2026-06-07T08:00:00+00:00',
    }
