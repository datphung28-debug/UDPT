from examples.distributed_features.app import RESULT_BACKEND, app
from examples.distributed_features.tracing import (
    InMemoryTraceRecorder,
    RedisTraceRecorder,
    create_child_context,
    create_trace_context,
    record_trace_event,
)


@app.task(name='distributed_features.add')
def add(x, y):
    return x + y


@app.task(name='distributed_features.hello')
def hello(to='world'):
    return f'Hello {to}'


def create_default_trace_recorder():
    try:
        from redis import Redis
    except ImportError:
        return InMemoryTraceRecorder()

    return RedisTraceRecorder(Redis.from_url(RESULT_BACKEND))


def _merge_context_clock(context, observed_context):
    return create_trace_context(
        trace_id=context.trace_id,
        task_id=context.task_id,
        worker_id=context.worker_id,
        logical_clock=max(context.logical_clock, observed_context.logical_clock),
    )


def _validate_order(order_id, recorder, parent_context):
    context = create_child_context(
        parent_context,
        task_id='validate-order',
        worker_id='worker-validate',
    )
    context = record_trace_event(recorder, context, 'started')

    if not order_id:
        context = record_trace_event(recorder, context, 'failed')
        exc = ValueError('order_id is required')
        exc.trace_context = context
        raise exc

    context = record_trace_event(recorder, context, 'success')
    return context


def run_traced_order_workflow(order_id, recorder=None, trace_id=None):
    recorder = recorder or create_default_trace_recorder()
    context = create_trace_context(
        trace_id=trace_id,
        task_id='process-order',
        worker_id='worker-process',
    )
    context = record_trace_event(recorder, context, 'started')
    context = record_trace_event(recorder, context, 'sent')

    try:
        child_context = _validate_order(order_id, recorder, context)
    except Exception as exc:
        failed_context = getattr(exc, 'trace_context', context)
        context = _merge_context_clock(context, failed_context)
        record_trace_event(recorder, context, 'failed')
        raise

    context = _merge_context_clock(context, child_context)
    record_trace_event(recorder, context, 'success')
    return f'{order_id} processed'


@app.task(name='distributed_features.process_order')
def process_order(order_id, trace_id=None):
    return run_traced_order_workflow(order_id, trace_id=trace_id)


def run_basic_demo():
    print('Sending distributed_features.add(2, 3)')
    result = add.delay(2, 3)
    print(f'Task id: {result.id}')
    print(f'Result: {result.get(timeout=10)}')


if __name__ == '__main__':
    run_basic_demo()
