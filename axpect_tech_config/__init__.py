try:
    from .celery import app as celery_app  # Optional: only if Celery is installed
    __all__ = ('celery_app',)
except Exception:
    # Allow Django to run without Celery
    celery_app = None
    __all__ = ()
