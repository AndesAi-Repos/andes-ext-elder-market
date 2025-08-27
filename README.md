🤖 Analizador de Feedback de WhatsApp con IA
Una aplicación que captura opiniones de usuarios (texto y audio) desde WhatsApp, realiza transcripción de voz localmente con Vosk, lo analiza con Google Gemini para obtener insights, y presenta los resultados en un dashboard en tiempo real.

🛠️ Configuración del Proyecto
Requisitos Previos
Cuenta de Google Cloud con la API de "Generative Language" habilitada.

Credenciales de Google Gemini (API Key).

Cuenta de Meta for Developers con una App de tipo "Business".

Cuenta de WhatsApp Business (WABA) configurada y un número de teléfono verificado.

Token de acceso permanente o temporal de la API de WhatsApp.

Software instalado: Python, Node.js, PostgreSQL, Redis, FFmpeg.

Configuración
1. Variables de Entorno

Navega a la carpeta /python_worker y crea o edita el archivo .env:

# Credenciales de Google Gemini
GEMINI_API_KEY="TU_API_KEY_DE_GEMINI"

# Credenciales de la Base de Datos PostgreSQL
DB_USER="tu_usuario_postgres"
DB_PASSWORD="tu_contraseña_postgres"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="feedback_app"

# URL del Broker de Celery (Redis)
CELERY_BROKER_URL="redis://localhost:6379/0"

# Credenciales de la API de WhatsApp Business
WHATSAPP_API_TOKEN="TU_TOKEN_DE_ACCESO_DE_META"

Navega a la carpeta /express_webhook/src y edita el archivo index.ts:

// Token para verificar la autenticidad del webhook con Meta
const VERIFY_TOKEN = "TU_TOKEN_DE_VERIFICACION_SECRETO";

2. Obtener Credenciales de Gemini

Ve a Google AI Studio.

Haz clic en "Get API key" en el menú de la izquierda.

Crea o selecciona un proyecto y genera tu clave.

3. Obtener Credenciales de WhatsApp

Ve a tu aplicación en Meta for Developers.

Navega a WhatsApp > Configuración de la API.

Copia el "Token de acceso temporal".

Crea un Token de verificación (una cadena de texto secreta de tu elección).

4. Modelo de Transcripción

Descarga un modelo de lenguaje de Vosk (se recomienda vosk-model-small-es-0.42).

Descomprímelo y coloca la carpeta del modelo dentro de la carpeta /python_worker.

🚀 Guía de Ejecución en Desarrollo
Para poner en marcha todo el sistema, es necesario ejecutar 4-5 servicios en terminales separadas. El orden es importante.

1. Iniciar Servicios Base (Redis y PostgreSQL)
Asegúrate de que tu servicio de PostgreSQL esté corriendo en segundo plano.

Abre la Terminal 1 e inicia el servidor de Redis:

redis-server

2. Iniciar el Worker de Procesamiento (Python/Celery)
Abre la Terminal 2.

Navega a la carpeta del worker y activa el entorno virtual:

cd python_worker
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

Inicia el worker (el flag -P gevent es crucial para Windows):

celery -A tasks.celery_app worker -l info -P gevent

3. Iniciar el Receptor de Webhooks (Node.js)
Abre la Terminal 3.

Navega a la carpeta del webhook e inicia el servidor:

cd express_webhook
npm start

4. Iniciar el Túnel a Internet (ngrok)
Abre la Terminal 4.

Expone el puerto 3000 de tu máquina a una URL pública:

ngrok http 3000

Usa la URL https://...ngrok-free.app que te da ngrok para configurar el webhook en tu aplicación de Meta.

5. Iniciar el Dashboard (Opcional)
Abre la Terminal 5.

Navega a la carpeta del worker y activa el entorno virtual:

cd python_worker
.\venv\Scripts\Activate.ps1

Ejecuta la aplicación de Streamlit:

streamlit run dashboard.py

Funcionalidades
Estado

Característica

✅

Recepción de Webhooks de WhatsApp Business API

✅

Manejo asíncrono de tareas con Celery y Redis

✅

Procesamiento de mensajes de texto

✅

Procesamiento de notas de voz (audio)

✅

Conversión de audio con FFmpeg

✅

Transcripción de Voz a Texto offline con Vosk

✅

Análisis de Sentimiento con Google Gemini

✅

Resumen de Quejas con Google Gemini

✅

Persistencia de datos en PostgreSQL

✅

Dashboard interactivo con Streamlit

🔄

Despliegue a producción en servicios en la nube

🔄

Soporte para otros tipos de media (imágenes, documentos)

🔄

Sistema de notificaciones para insights importantes

🔄

Manejo de errores y reintentos más avanzado

Uso
El sistema se activa automáticamente cuando un usuario envía un mensaje de texto o una nota de voz al número de WhatsApp asociado.

Recepción: El servidor de Node.js recibe el mensaje y lo encola en Redis.

Procesamiento: Un worker de Celery toma la tarea de la cola.

Análisis: El worker procesa el contenido, usando Vosk para audios y luego Gemini para el análisis de texto.

Visualización: Los resultados se guardan en PostgreSQL y se reflejan automáticamente en el dashboard de Streamlit.

Solución de Problemas
Error: 401 Unauthorized en los logs del worker de Python

Causa: El WHATSAPP_API_TOKEN en tu archivo .env ha caducado (duran 24 horas).

Solución: Genera un nuevo token desde el panel de Meta, pégalo en el .env y reinicia el worker de Celery.

Error: 403 Forbidden o 404 Not Found al verificar el webhook

Causa: El token de verificación en index.ts no coincide con el de Meta, o el servidor de Node.js no está corriendo.

Solución: Asegúrate de que ambos tokens sean idénticos y que tu servidor (npm start) y ngrok estén funcionando antes de verificar.

Error: FileNotFoundError al iniciar el worker de Celery

Causa: La carpeta del modelo de Vosk no se encuentra en python_worker/.

Solución: Verifica que el nombre de la carpeta en el código (VOSK_MODEL_PATH) coincida con el nombre de la carpeta que descargaste.

Error: [WinError 32] El proceso no tiene acceso al archivo...

Causa: Un problema de bloqueo de archivos en Windows al procesar audios.

Solución: Asegúrate de estar usando la última versión del código de tasks.py, que utiliza un bloque with para manejar los archivos de audio correctamente.

Personalización
Cambiar Modelo de Transcripción:

Descarga otro modelo de Vosk (por ejemplo, uno más grande y preciso).

Coloca la nueva carpeta del modelo en /python_worker.

Actualiza la variable VOSK_MODEL_PATH en tasks.py con el nuevo nombre de la carpeta.

Ajustar Prompts de Gemini:

Abre tasks.py.

Modifica las cadenas de texto prompt_sentiment y prompt_summary para ajustar cómo quieres que la IA clasifique o resuma el texto.

Notas Técnicas
Arquitectura: Microservicios desacoplados.

Comunicación: Peticiones HTTP (Webhook) y cola de mensajes (Redis).

Concurrencia: Manejada por Celery y gevent para el procesamiento en paralelo de tareas.

Entorno de Desarrollo: Se requiere ngrok para exponer el webhook local a Internet.
