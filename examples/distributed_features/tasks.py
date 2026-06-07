from examples.distributed_features.app import app


@app.task(name='distributed_features.add')
def add(x, y):
    return x + y


@app.task(name='distributed_features.hello')
def hello(to='world'):
    return f'Hello {to}'


def run_basic_demo():
    print('Sending distributed_features.add(2, 3)')
    result = add.delay(2, 3)
    print(f'Task id: {result.id}')
    print(f'Result: {result.get(timeout=10)}')


if __name__ == '__main__':
    run_basic_demo()
