"""
Celery worker for async file processing

Run with:
celery -A worker.celery_app worker --loglevel=info --concurrency=4
"""

from app.tasks.celery_tasks import celery_app

if __name__ == '__main__':
    celery_app.start()
