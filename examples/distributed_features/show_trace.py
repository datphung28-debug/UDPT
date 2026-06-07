import argparse
import sys
from operator import attrgetter
from pathlib import Path


if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.distributed_features.app import RESULT_BACKEND
from examples.distributed_features.tracing import RedisTraceRecorder


def load_trace_timeline(recorder, trace_id):
    events = recorder.events_for_trace(trace_id)
    return sorted(events, key=attrgetter('logical_clock', 'timestamp'))


def format_trace_timeline(trace_id, events):
    lines = [f'trace_id: {trace_id}']

    if not events:
        lines.append('No events found.')
        return '\n'.join(lines)

    for event in events:
        line = (
            f'[{event.logical_clock}] {event.event} '
            f'{event.task_id} on {event.worker_id}'
        )
        if event.parent_task_id:
            line = f'{line} parent={event.parent_task_id}'
        lines.append(line)

    return '\n'.join(lines)


def create_redis_trace_recorder(redis_url=RESULT_BACKEND):
    from redis import Redis

    return RedisTraceRecorder(Redis.from_url(redis_url))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Print a distributed task trace timeline.',
    )
    parser.add_argument('trace_id', help='Trace id to load from Redis.')
    parser.add_argument(
        '--redis-url',
        default=RESULT_BACKEND,
        help='Redis URL containing trace events.',
    )
    args = parser.parse_args(argv)

    recorder = create_redis_trace_recorder(args.redis_url)
    events = load_trace_timeline(recorder, args.trace_id)
    print(format_trace_timeline(args.trace_id, events))


if __name__ == '__main__':
    main()
