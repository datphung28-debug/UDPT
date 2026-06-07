import argparse
from time import sleep

from examples.distributed_features.app import RESULT_BACKEND, app
from examples.distributed_features.show_trace import (
    format_trace_timeline,
    load_trace_timeline,
)
from examples.distributed_features.singleton import singleton_task
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


def create_default_lock_client():
    from redis import Redis

    return Redis.from_url(RESULT_BACKEND)


@singleton_task(
    lock_key_template='inventory:{product_id}',
    ttl=30,
    redis_client_factory=lambda: create_default_lock_client(),
)
def _update_inventory(product_id, quantity, hold_seconds=0):
    if hold_seconds:
        sleep(hold_seconds)

    return {
        'status': 'updated',
        'product_id': product_id,
        'quantity': quantity,
    }


@app.task(name='distributed_features.update_inventory')
def update_inventory(product_id, quantity, hold_seconds=0):
    return _update_inventory(
        product_id=product_id,
        quantity=quantity,
        hold_seconds=hold_seconds,
    )


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


def _print_and_return(lines):
    output = '\n'.join(lines)
    print(output)
    return output


def run_trace_demo(
    order_id='order-1',
    trace_id='order-1-trace',
    task=None,
    recorder=None,
):
    task = task or process_order
    recorder = recorder or create_default_trace_recorder()

    result = task.delay(order_id, trace_id=trace_id)
    task_result = result.get(timeout=10)
    events = load_trace_timeline(recorder, trace_id)

    return _print_and_return([
        f'Dispatching distributed_features.process_order({order_id!r})',
        f'Task id: {result.id}',
        f'Result: {task_result}',
        format_trace_timeline(trace_id, events),
    ])


def run_lock_demo(product_id='sku-1', task=None, start_gap_seconds=0.2):
    task = task or update_inventory

    first = task.delay(product_id=product_id, quantity=5, hold_seconds=2)
    sleep(start_gap_seconds)
    second = task.delay(product_id=product_id, quantity=7, hold_seconds=0)

    first_result = first.get(timeout=10)
    second_result = second.get(timeout=10)

    return _print_and_return([
        f'Dispatching two update_inventory tasks for {product_id}',
        f'First task id: {first.id}',
        f'Second task id: {second.id}',
        f'First result: {first_result}',
        f'Second result: {second_result}',
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Run distributed feature demos.',
    )
    parser.add_argument(
        'command',
        nargs='?',
        default='basic',
        choices=['basic', 'run-trace-demo', 'run-lock-demo'],
    )
    args = parser.parse_args(argv)

    if args.command == 'run-trace-demo':
        return run_trace_demo()
    if args.command == 'run-lock-demo':
        return run_lock_demo()
    return run_basic_demo()


if __name__ == '__main__':
    main()
