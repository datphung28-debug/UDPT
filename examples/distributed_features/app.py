from celery import Celery


BROKER_URL = 'redis://localhost:6379/0'
RESULT_BACKEND = 'redis://localhost:6379/1'


app = Celery(
    'distributed_features',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=['examples.distributed_features.tasks'],
)

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)
