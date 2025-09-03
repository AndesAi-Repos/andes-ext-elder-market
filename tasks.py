import os
import uuid
import requests
import ffmpeg
import time
import json
import wave
import datetime
from vosk import Model, KaldiRecognizer
from celery import Celery
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

from database import SessionLocal, Feedback

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
celery_app = Celery(__name__, broker=os.getenv("CELERY_BROKER_URL"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {"temperature": 0.2}
model_text = genai.GenerativeModel('gemini-1.5-flash-latest')
VOSK_MODEL_PATH = "vosk-model-small-es-0.42"
if not os.path.exists(VOSK_MODEL_PATH):
    raise FileNotFoundError(f"El modelo de Vosk no se encuentra en la ruta: {VOSK_MODEL_PATH}.")
model_vosk = Model(VOSK_MODEL_PATH)


# --- 2. FUNCIÓN PARA ENVIAR MENSAJES DE WHATSAPP ---
def send_whatsapp_message(phone_number: str, message_body: str, buttons: list = None):
    API_URL = f"https://graph.facebook.com/v20.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_API_TOKEN')}", "Content-Type": "application/json"}
    
    payload = { "messaging_product": "whatsapp", "to": phone_number }
    
    if buttons:
        payload["type"] = "interactive"
        payload["interactive"] = {
            "type": "button",
            "body": {"text": message_body},
            "action": {
                "buttons": [{"type": "reply", "reply": {"id": f"btn_{btn_text.lower()}", "title": btn_text}} for btn_text in buttons]
            }
        }
    else:
        payload["type"] = "text"
        payload["text"] = {"body": message_body}

    try:
        print(f"Enviando mensaje a {phone_number}: '{message_body[:30]}...'")
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        print("Mensaje enviado con éxito.")
    except requests.exceptions.HTTPError as e:
        print(f"!!!!!!!!!!!!!! ERROR AL ENVIAR MENSAJE DE WHATSAPP !!!!!!!!!!!!!!")
        print(f"Respuesta: {e.response.text}")


# --- 3. FUNCIÓN DE AYUDA CON REINTENTOS PARA GEMINI ---
def generate_content_with_retry(model, prompt, max_retries=3):
    retries = 0
    wait_time = 2
    while retries < max_retries:
        try:
            return model.generate_content(prompt, generation_config=generation_config)
        except exceptions.ResourceExhausted as e:
            print(f"ERROR DE CUOTA DE GEMINI (429). Reintentando en {wait_time}s...")
            time.sleep(wait_time)
            retries += 1
            wait_time *= 2
        except Exception as e:
            print(f"ERROR INESPERADO EN LLAMADA A GEMINI: {e}")
            raise
    raise Exception("Se superó el número máximo de reintentos para la API de Gemini.")


# --- 4. LA TAREA PRINCIPAL DE CELERY (MOTOR DE ENCUESTA DE 5 PASOS) ---
@celery_app.task(name='process_feedback_task')
def process_feedback(payload):
    print(f"--- INICIO TAREA --- Usuario: {payload['user_id']}, Tipo: {payload['type']}")
    
    db = SessionLocal()
    user_id = payload['user_id']
    user_message_text = ""

    # 1. Extraer el texto del mensaje del usuario
    if payload['type'] == 'text' or payload['type'] == 'interactive':
        user_message_text = payload.get('content', '').strip().lower()
    elif payload['type'] == 'audio':
        # (La lógica de transcripción de audio con Vosk no cambia)
        try:
            # ... (código de transcripción de audio) ...
            media_id = payload['media_id']
            api_token = os.getenv("WHATSAPP_API_TOKEN")
            url_info = f"https://graph.facebook.com/v20.0/{media_id}/"
            headers_info = {'Authorization': f'Bearer {api_token}'}
            response_info = requests.get(url_info, headers=headers_info)
            response_info.raise_for_status()
            media_url = response_info.json()['url']
            headers_download = {'Authorization': f'Bearer {api_token}'}
            response_download = requests.get(media_url, headers=headers_download)
            response_download.raise_for_status()
            
            original_audio_path = f"temp_{uuid.uuid4()}.ogg"
            wav_audio_path = f"temp_{uuid.uuid4()}.wav"
            with open(original_audio_path, 'wb') as f: f.write(response_download.content)
            (ffmpeg.input(original_audio_path).output(wav_audio_path, acodec='pcm_s16le', ac=1, ar=16000).run(overwrite_output=True, quiet=True))
            
            with wave.open(wav_audio_path, "rb") as wf:
                rec = KaldiRecognizer(model_vosk, wf.getframerate())
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0: break
                    rec.AcceptWaveform(data)
            result_dict = json.loads(rec.FinalResult())
            user_message_text = result_dict.get('text', '')
            print(f"Audio transcrito a: '{user_message_text}'")
            
            os.remove(original_audio_path)
            os.remove(wav_audio_path)
        except Exception as e:
            print(f"Error en transcripción de audio: {e}")
            db.close()
            return

    # 2. Buscar si hay una encuesta en progreso
    current_survey = db.query(Feedback).filter(Feedback.user_id == user_id, Feedback.status != 'completed').first()

    # 3. Lógica del motor de encuestas por pasos
    frases_de_inicio = ['quiero dejar un comentario', 'dejar un comentario']
    
    if not current_survey and user_message_text in frases_de_inicio:
        # PASO 0: INICIAR ENCUESTA
        print(f"Iniciando nueva encuesta para {user_id}.")
        new_survey = Feedback(user_id=user_id, status='step_1_sent', current_step=1, created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
        db.add(new_survey)
        db.commit()
        q1_text = "¡Genial! Para empezar, en una escala de 1 a 3, ¿qué tan probable es que recomiendes nuestra app a un amigo?"
        q1_buttons = ["No muy probable 👎", "Quizás 🤔", "Muy probable 👍"]
        send_whatsapp_message(user_id, q1_text, q1_buttons)

    elif current_survey and current_survey.current_step == 1:
        # PASO 1: RECIBIR RESPUESTA NPS
        respuesta_texto = user_message_text
        if respuesta_texto in ["no muy probable 👎", "quizás 🤔", "muy probable 👍"]:
            current_survey.q1_nps = respuesta_texto
            current_survey.status = 'step_2_sent'
            current_survey.current_step = 2
            
            if respuesta_texto == "no muy probable 👎":
                q2_text = "Entendido, gracias por tu honestidad. Para nosotros es crucial saber en qué fallamos. *¿Cuál fue la razón principal de tu calificación?*\n\nPuedes *escribirlo o enviarnos una nota de voz*. 🎤"
            elif respuesta_texto == "quizás 🤔":
                q2_text = "Gracias por tu respuesta. Nos encantaría saber qué podría convertir tu experiencia en una excelente. *¿Qué le falta a la app o qué podríamos hacer mejor para que la recomendaras?*\n\nPuedes *escribirlo o enviarnos una nota de voz*. 🎤"
            else: # Muy probable
                q2_text = "¡Fantástico! Nos alegra mucho saber eso. *¿Qué fue lo que más te gustó o la característica que te pareció más útil?*\n\nPuedes *escribirlo o en una nota de voz*. 🎤"
            send_whatsapp_message(user_id, q2_text)
            db.commit()
        else:
            send_whatsapp_message(user_id, "Por favor, selecciona una de las opciones usando los botones.")

    elif current_survey and current_survey.current_step == 2:
        # PASO 2: RECIBIR EL "PORQUÉ"
        current_survey.q2_reason = user_message_text
        current_survey.status = 'step_3_sent'
        current_survey.current_step = 3
        db.commit()
        q3_text = "Entendido. Ahora, pensando en las características principales de la app, ¿cuál de estas áreas es la *más importante* para ti?"
        q3_buttons = ["Diseño y Facilidad de Uso ✨", "Velocidad y Rendimiento 🚀", "Funcionalidades Específicas 🛠️"]
        send_whatsapp_message(user_id, q3_text, q3_buttons)

    elif current_survey and current_survey.current_step == 3:
        # PASO 3: RECIBIR LA PRIORIDAD
        current_survey.q3_priority = user_message_text
        current_survey.status = 'step_4_sent'
        current_survey.current_step = 4
        db.commit()
        q4_text = "Gracias por esa información. Si tuvieras una varita mágica, *¿qué única función o mejora añadirías a la aplicación?*"
        send_whatsapp_message(user_id, q4_text)

    elif current_survey and current_survey.current_step == 4:
        # PASO 4: RECIBIR LA "VARITA MÁGICA"
        current_survey.q4_magic_wand = user_message_text
        current_survey.status = 'step_5_sent'
        current_survey.current_step = 5
        db.commit()
        q5_text = "¡Ya casi terminamos! Solo una última pregunta. ¿Cómo descubriste nuestra aplicación?"
        q5_buttons = ["Redes Sociales 📱", "Recomendación de un amigo 🗣️", "Navegando en la web 🌐"]
        send_whatsapp_message(user_id, q5_text, q5_buttons)

    elif current_survey and current_survey.current_step == 5:
        # PASO 5: RECIBIR CANAL DE DESCUBRIMIENTO Y FINALIZAR
        current_survey.q5_discovery = user_message_text
        current_survey.status = 'completed'
        current_survey.current_step = 6
        current_survey.updated_at = datetime.datetime.utcnow()

        send_whatsapp_message(user_id, "¡Eso es todo! Muchísimas gracias por tu tiempo y por ayudarnos a construir una mejor aplicación. ¡Tu feedback es increíblemente valioso para nosotros! 🙏")

        # ANÁLISIS FINAL CON GEMINI
        try:
            full_feedback_text = f"NPS: {current_survey.q1_nps}. Razón: {current_survey.q2_reason}. Prioridad: {current_survey.q3_priority}. Sugerencia: {current_survey.q4_magic_wand}."
            
            prompt_sentiment = f"Analiza el sentimiento general del siguiente feedback de un usuario. Responde solo 'Positivo', 'Negativo' o 'Neutral'. Feedback: \"{full_feedback_text}\""
            response_sentiment = generate_content_with_retry(model_text, prompt_sentiment)
            current_survey.final_sentiment = response_sentiment.text.strip()
            
            if current_survey.q1_nps != "Muy probable 👍":
                prompt_summary = f"Del siguiente feedback, resume la queja o sugerencia principal en una frase corta y accionable: \"{full_feedback_text}\""
                response_summary = generate_content_with_retry(model_text, prompt_summary)
                current_survey.final_summary = response_summary.text.strip()
            
            db.commit()
            print("Análisis de Gemini completado y guardado.")
        except Exception as e:
            print(f"Error en el análisis final con Gemini: {e}")
            db.rollback()

    else:
        # Mensaje fuera de contexto
        send_whatsapp_message(user_id, "Hola. Si quieres dejarnos un comentario sobre la app, por favor, envía la frase: quiero dejar un comentario")
        
    db.close()
    print("--- FIN TAREA ---")