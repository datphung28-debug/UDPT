import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from operator import attrgetter
from typing import Optional
from uuid import uuid4


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    parent_task_id: Optional[str]
    task_id: str
    worker_id: str
    logical_clock: int


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    parent_task_id: Optional[str]
    task_id: str
    worker_id: str
    event: str
    logical_clock: int
    timestamp: datetime

    def to_dict(self):
        payload = asdict(self)
        payload['timestamp'] = self.timestamp.isoformat()
        return payload


class InMemoryTraceRecorder:
    def __init__(self):
        self._events = {}

    def record(self, event):
        self._events.setdefault(event.trace_id, []).append(event)

    def events_for_trace(self, trace_id):
        events = self._events.get(trace_id, [])
        return sorted(events, key=attrgetter('logical_clock', 'timestamp'))


class RedisTraceRecorder:
    def __init__(self, redis_client, key_prefix='trace'):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def record(self, event):
        self.redis_client.rpush(
            self._key_for_trace(event.trace_id),
            json.dumps(event.to_dict()),
        )

    def events_for_trace(self, trace_id):
        raw_events = self.redis_client.lrange(self._key_for_trace(trace_id), 0, -1)
        events = [trace_event_from_dict(json.loads(self._decode(raw))) for raw in raw_events]
        return sorted(events, key=attrgetter('logical_clock', 'timestamp'))

    def _key_for_trace(self, trace_id):
        return f'{self.key_prefix}:{trace_id}:events'

    def _decode(self, value):
        if isinstance(value, bytes):
            return value.decode()
        return value


def next_logical_clock(current_clock):
    return current_clock + 1


def create_trace_context(
    task_id,
    worker_id,
    trace_id=None,
    logical_clock=0,
):
    return TraceContext(
        trace_id=trace_id or str(uuid4()),
        parent_task_id=None,
        task_id=task_id,
        worker_id=worker_id,
        logical_clock=logical_clock,
    )


def create_child_context(parent_context, task_id, worker_id):
    return TraceContext(
        trace_id=parent_context.trace_id,
        parent_task_id=parent_context.task_id,
        task_id=task_id,
        worker_id=worker_id,
        logical_clock=next_logical_clock(parent_context.logical_clock),
    )


def create_trace_event(context, event, timestamp=None):
    return TraceEvent(
        trace_id=context.trace_id,
        parent_task_id=context.parent_task_id,
        task_id=context.task_id,
        worker_id=context.worker_id,
        event=event,
        logical_clock=next_logical_clock(context.logical_clock),
        timestamp=timestamp or datetime.now(timezone.utc),
    )


def trace_event_from_dict(payload):
    return TraceEvent(
        trace_id=payload['trace_id'],
        parent_task_id=payload['parent_task_id'],
        task_id=payload['task_id'],
        worker_id=payload['worker_id'],
        event=payload['event'],
        logical_clock=payload['logical_clock'],
        timestamp=datetime.fromisoformat(payload['timestamp']),
    )


def record_trace_event(recorder, context, event, timestamp=None):
    trace_event = create_trace_event(context, event, timestamp=timestamp)
    recorder.record(trace_event)
    return replace(context, logical_clock=trace_event.logical_clock)
