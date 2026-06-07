from examples.distributed_features.app import app
from examples.distributed_features.tasks import add, hello

def test_demo_app_uses_redis_defaults():
    assert app.main == 'distributed_features'
    assert app.conf.broker_url == 'redis://localhost:6379/0'
    assert app.conf.result_backend == 'redis://localhost:6379/1'

def test_demo_tasks_are_registered():
    assert add.name == 'distributed_features.add'
    assert hello.name == 'distributed_features.hello'
    assert add.run(2, 3) == 5
    assert hello.run('Phenikaa') == 'Hello Phenikaa'
