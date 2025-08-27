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


# --- 4. LA TAREA PRINCIPAL DE CELERY (EL MOTOR DE ENCUESTAS) ---
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
        try:
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
    
    current_survey = db.query(Feedback).filter(Feedback.user_id == user_id, Feedback.status != 'completed').first()

    # --- LÓGICA DE INICIO CON TU FRASE CLAVE PREFERIDA ---
    frases_de_inicio = ['quiero dejar un comentario', 'dejar un comentario']
    
    if not current_survey and user_message_text in frases_de_inicio:
        print(f"Iniciando nueva encuesta para {user_id} a través de la frase clave.")
        new_survey = Feedback(user_id=user_id, status='step_1_sent', current_step=1, created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
        db.add(new_survey)
        db.commit()
        
        q1_text = "¡Genial! Para empezar, ¿cómo calificarías tu experiencia general con la app?"
        q1_buttons = ["Mala 👎", "Regular 😐", "Buena 👍"]
        send_whatsapp_message(user_id, q1_text, q1_buttons)

    elif current_survey and current_survey.current_step == 1:
        respuesta_texto = user_message_text
        
        if respuesta_texto in ["mala 👎", "regular 😐", "buena 👍"]:
            if respuesta_texto == "mala 👎": rating_num = 1
            elif respuesta_texto == "regular 😐": rating_num = 3
            else: rating_num = 5
            
            current_survey.q1_rating = rating_num
            current_survey.status = 'step_2_sent'
            current_survey.current_step = 2
            
            # --- TUS MENSAJES PERSONALIZADOS ---
            if rating_num <= 2:
                q2_text = "Entendido, lamentamos que tu experiencia no haya sido la ideal.\n\n*Por favor, cuéntanos qué salió mal o qué podríamos mejorar.*\n\nPuedes *escribirlo o enviarnos una nota de voz* con los detalles. 🎤"
            elif rating_num == 3:
                q2_text = "Entendido, gracias.\n\n*Cuéntanos un poco más sobre tu experiencia.* ¿Qué podríamos mejorar o qué te motivó a darnos esa calificación?\n\nPuedes *escribir tu respuesta o enviarnos una nota de voz*. 🎤"
            else:
                q2_text = "¡Nos alegra saber eso!\n\n*Para ayudarnos a entenderlo mejor, ¿qué fue lo que más te gustó?*\n\n¡Nos encantaría que nos lo contaras *por texto o en una nota de voz*! 🎤"
            
            send_whatsapp_message(user_id, q2_text)
            db.commit()
        else:
            send_whatsapp_message(user_id, "Por favor, selecciona una de las opciones válidas usando los botones.")

    elif current_survey and current_survey.current_step == 2:
        if not user_message_text:
             print("Respuesta a P2 vacía. Ignorando.")
             db.close()
             return

        current_survey.q2_feedback = user_message_text
        current_survey.status = 'completed'
        current_survey.current_step = 3
        current_survey.updated_at = datetime.datetime.utcnow()

        send_whatsapp_message(user_id, "¡Recibido! Muchas gracias por tu feedback. Nos es de gran ayuda para mejorar. 🙏")

        try:
            full_feedback_text = f"Calificación: {current_survey.q1_rating}/5. Comentario: {current_survey.q2_feedback}"
            
            prompt_sentiment = f"Analiza el sentimiento del siguiente feedback. Responde 'Positivo', 'Negativo' o 'Neutral'. Feedback: \"{full_feedback_text}\""
            response_sentiment = generate_content_with_retry(model_text, prompt_sentiment)
            current_survey.final_sentiment = response_sentiment.text.strip()
            
            if current_survey.q1_rating <= 3:
                prompt_summary = f"Resume la queja principal del siguiente feedback en una frase: \"{full_feedback_text}\""
                response_summary = generate_content_with_retry(model_text, prompt_summary)
                current_survey.final_summary = response_summary.text.strip()
            
            db.commit()
            print("Análisis de Gemini completado y guardado.")
        except Exception as e:
            print(f"Error en el análisis final con Gemini: {e}")
            db.rollback()

    else:
        # --- MENSAJE DE AYUDA ACTUALIZADO ---
        send_whatsapp_message(user_id, "Hola. Si quieres dejarnos un comentario sobre la app, por favor, envía la frase: quiero dejar un comentario")
        
    db.close()
    print("--- FIN TAREA ---")