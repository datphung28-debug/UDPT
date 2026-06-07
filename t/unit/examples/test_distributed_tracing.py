from datetime import datetime, timezone

import pytest

from examples.distributed_features.tracing import (
    InMemoryTraceRecorder,
    RedisTraceRecorder,
    TraceContext,
    TraceEvent,
    create_child_context,
    create_trace_context,
    next_logical_clock,
    record_trace_event,
)
from examples.distributed_features.tasks import run_traced_order_workflow


class FakeRedis:
    def __init__(self):
        self.values = {}

    def rpush(self, key, value):
        self.values.setdefault(key, []).append(value.encode())

    def lrange(self, key, start, stop):
        return self.values.get(key, [])[start:]


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


def test_in_memory_recorder_stores_events_by_trace_id():
    recorder = InMemoryTraceRecorder()
    context = create_trace_context(
        trace_id='trace-1',
        task_id='root-task',
        worker_id='worker-1',
    )

    context = record_trace_event(recorder, context, 'started')
    context = record_trace_event(recorder, context, 'success')

    events = recorder.events_for_trace('trace-1')
    assert [event.event for event in events] == ['started', 'success']
    assert [event.logical_clock for event in events] == [1, 2]
    assert context.logical_clock == 2


def test_redis_recorder_round_trips_events():
    redis_client = FakeRedis()
    recorder = RedisTraceRecorder(redis_client)
    context = create_trace_context(
        trace_id='trace-1',
        task_id='root-task',
        worker_id='worker-1',
    )

    context = record_trace_event(recorder, context, 'started')
    record_trace_event(recorder, context, 'success')

    events = recorder.events_for_trace('trace-1')
    assert [event.event for event in events] == ['started', 'success']
    assert redis_client.values['trace:trace-1:events']


def test_record_trace_event_keeps_events_in_lifecycle_order():
    recorder = InMemoryTraceRecorder()
    parent = create_trace_context(
        trace_id='trace-1',
        task_id='validate-order',
        worker_id='worker-1',
    )

    parent = record_trace_event(recorder, parent, 'sent')
    child = create_child_context(
        parent,
        task_id='charge-payment',
        worker_id='worker-2',
    )
    child = record_trace_event(recorder, child, 'started')
    child = record_trace_event(recorder, child, 'success')

    events = recorder.events_for_trace('trace-1')
    assert [event.event for event in events] == ['sent', 'started', 'success']
    assert [event.task_id for event in events] == [
        'validate-order',
        'charge-payment',
        'charge-payment',
    ]
    assert [event.logical_clock for event in events] == [1, 3, 4]


def test_failed_lifecycle_event_is_recorded():
    recorder = InMemoryTraceRecorder()
    context = create_trace_context(
        trace_id='trace-1',
        task_id='failing-task',
        worker_id='worker-1',
    )

    context = record_trace_event(recorder, context, 'started')
    context = record_trace_event(recorder, context, 'failed')

    events = recorder.events_for_trace('trace-1')
    assert [event.event for event in events] == ['started', 'failed']
    assert context.logical_clock == 2


def test_traced_order_workflow_records_task_lifecycle_events():
    recorder = InMemoryTraceRecorder()

    result = run_traced_order_workflow(
        order_id='order-1',
        recorder=recorder,
        trace_id='trace-1',
    )

    events = recorder.events_for_trace('trace-1')
    assert result == 'order-1 processed'
    assert [event.event for event in events] == [
        'started',
        'sent',
        'started',
        'success',
        'success',
    ]
    assert [event.task_id for event in events] == [
        'process-order',
        'process-order',
        'validate-order',
        'validate-order',
        'process-order',
    ]
    assert [event.logical_clock for event in events] == [1, 2, 4, 5, 6]
    assert [event.logical_clock for event in events] == [1, 2, 4, 5, 6]


def test_traced_order_workflow_records_failure_events():
    recorder = InMemoryTraceRecorder()

    with pytest.raises(ValueError):
        run_traced_order_workflow(
            order_id='',
            recorder=recorder,
            trace_id='trace-1',
        )

    events = recorder.events_for_trace('trace-1')
    assert [event.event for event in events] == [
        'started',
        'sent',
        'started',
        'failed',
        'failed',
    ]
    assert [event.task_id for event in events] == [
        'process-order',
        'process-order',
        'validate-order',
        'validate-order',
        'process-order',
    ]
