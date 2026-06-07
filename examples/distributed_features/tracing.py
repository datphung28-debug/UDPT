from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
