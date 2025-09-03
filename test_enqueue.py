# test_enqueue.py (VERSIÓN CORREGIDA Y FINAL)

import json
from redis import Redis
import uuid
import base64

# Configuración
redis_client = Redis.from_url("redis://localhost:6379/0")
CELERY_QUEUE_NAME = "celery"

def send_task_to_celery(task_name: str, task_args: list):
    """
    Construye y encola un mensaje de tarea en el formato correcto para Celery v5+.
    """
    task_id = str(uuid.uuid4())

    # Preparamos el payload principal de la tarea
    message_payload = {
        "id": task_id,
        "task": task_name,
        "args": task_args,
        "kwargs": {},
        "retries": 0,
        "eta": None,
        "expires": None,
        "utc": True,
        "callbacks": None,
        "errbacks": None,
        "timelimit": (None, None),
        "taskset": None,
        "chord": None,
    }

    # Empaquetamos en el formato que espera el 'broker' (Kombu)
    broker_message = {
        "body": base64.b64encode(json.dumps(message_payload).encode('utf-8')).decode('utf-8'),
        "content-encoding": "utf-8",
        "content-type": "application/json",
        "headers": {},
        "properties": {
            "correlation_id": task_id,
            "reply_to": str(uuid.uuid4()),
            "delivery_mode": 2,
            "delivery_info": {"exchange": "", "routing_key": CELERY_QUEUE_NAME},
            "priority": 0,
            "body_encoding": "base64",
            "delivery_tag": str(uuid.uuid4()),
        },
    }

    try:
        redis_client.lpush(CELERY_QUEUE_NAME, json.dumps(broker_message))
        print(f"Tarea '{task_name}' enviada correctamente a la cola '{CELERY_QUEUE_NAME}'.")
    except Exception as e:
        print(f"Error al enviar a Redis: {e}")

if __name__ == "__main__":
    test_payload = {
        'user_id': '573044696202',
        'type': 'text',
        'content': 'quiero dejar un comentario'
    }
    
    send_task_to_celery(
        task_name='process_feedback_task',
        task_args=[test_payload]
    )