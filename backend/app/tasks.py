import time

from celery import Celery


celery_app = Celery(
    __name__,
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
)

# Configuración mínima explícita (opcional)
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
)


@celery_app.task(name='tasks.process_audio_session')
def process_audio_session(room_id: str):
    """Simula un procesamiento pesado de audio para una sala."""
    time.sleep(5)
    return {
        'room_id': room_id,
        'status': 'processed',
        'detail': 'Audio session processed asynchronously',
    }

