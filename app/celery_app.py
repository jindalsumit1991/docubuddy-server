from celery import Celery
import os

# Ensure the Redis URL is set properly
redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

# Celery configuration
celery_app = Celery(
    'celery_app',
    broker=redis_url,  # Ensure this is correctly set to Redis
    backend=redis_url  # Optional: Redis can also be used as the result backend
)

# Set Celery configuration
celery_app.conf.update(
    broker_connection_retry_on_startup=True,  # Set to True to maintain retry behavior on startup
    task_serializer='json',
    accept_content=['json'],  # Only accept JSON-serialized tasks
    result_serializer='json',
    timezone='UTC',
    enable_utc=True
)

# Import the task from app.main
from app.main import process_single_file  # Ensure this is imported

# Make sure the task is registered by including it in the tasks list
celery_app.autodiscover_tasks(['app.main'])