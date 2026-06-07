from datetime import datetime, timezone

from examples.distributed_features.show_trace import (
    format_trace_timeline,
    load_trace_timeline,
)
from examples.distributed_features.tracing import InMemoryTraceRecorder, TraceEvent


def test_load_trace_timeline_sorts_by_logical_clock_then_timestamp():
    recorder = InMemoryTraceRecorder()
    later = datetime(2026, 6, 7, 8, 0, 2, tzinfo=timezone.utc)
    earlier = datetime(2026, 6, 7, 8, 0, 1, tzinfo=timezone.utc)

    recorder.record(
        TraceEvent(
            trace_id='trace-1',
            parent_task_id=None,
            task_id='validate-order',
            worker_id='worker-2',
            event='started',
            logical_clock=2,
            timestamp=later,
        )
    )
    recorder.record(
        TraceEvent(
            trace_id='trace-1',
            parent_task_id=None,
            task_id='process-order',
            worker_id='worker-1',
            event='sent',
            logical_clock=1,
            timestamp=later,
        )
    )
    recorder.record(
        TraceEvent(
            trace_id='trace-1',
            parent_task_id=None,
            task_id='process-order',
            worker_id='worker-1',
            event='started',
            logical_clock=1,
            timestamp=earlier,
        )
    )

    events = load_trace_timeline(recorder, 'trace-1')

    assert [event.event for event in events] == ['started', 'sent', 'started']
    assert [event.task_id for event in events] == [
        'process-order',
        'process-order',
        'validate-order',
    ]


def test_format_trace_timeline_prints_compact_output():
    timestamp = datetime(2026, 6, 7, 8, 0, tzinfo=timezone.utc)
    events = [
        TraceEvent(
            trace_id='trace-1',
            parent_task_id=None,
            task_id='process-order',
            worker_id='worker-process',
            event='sent',
            logical_clock=1,
            timestamp=timestamp,
        ),
        TraceEvent(
            trace_id='trace-1',
            parent_task_id='process-order',
            task_id='validate-order',
            worker_id='worker-validate',
            event='started',
            logical_clock=2,
            timestamp=timestamp,
        ),
    ]

    output = format_trace_timeline('trace-1', events)

    assert output == (
        'trace_id: trace-1\n'
        '[1] sent process-order on worker-process\n'
        '[2] started validate-order on worker-validate parent=process-order'
    )


def test_format_trace_timeline_handles_empty_trace():
    assert format_trace_timeline('missing-trace', []) == (
        'trace_id: missing-trace\n'
        'No events found.'
    )
