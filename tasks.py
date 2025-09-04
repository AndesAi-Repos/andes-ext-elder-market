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


# --- 4. LA TAREA PRINCIPAL DE CELERY (CON INTELIGENCIA DE TEXTO) ---
@celery_app.task(name='process_feedback_task')
def process_feedback(payload):
    print(f"--- INICIO TAREA --- Usuario: {payload['user_id']}, Tipo: {payload['type']}")
    
    db = SessionLocal()
    user_id = payload['user_id']
    user_message_text = ""

    # 1. Extraer el texto del mensaje
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

    # 3. Lógica del motor de encuestas por pasos
    frases_de_inicio = ['quiero dejar un comentario', 'dejar un comentario']
    
    if not current_survey and user_message_text in frases_de_inicio:
        print(f"Iniciando nueva encuesta para {user_id}.")
        new_survey = Feedback(user_id=user_id, status='step_1_sent', current_step=1, created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
        db.add(new_survey)
        db.commit()
        
        q1_text = "¡Genial! Para empezar, en una escala de 1 a 3, ¿qué tan probable es que recomiendes nuestra app a un amigo?"
        q1_buttons = ["No muy probable 👎", "Quizás 🤔", "Muy probable 👍"]
        send_whatsapp_message(user_id, q1_text, q1_buttons)

    elif current_survey:
        if current_survey.current_step == 1:
            respuesta_texto = user_message_text.lower()
            chosen_option = None

            keywords_mala = ["mala", "mal", "pésima", "terrible", "horrible", "no me gustó", "no probable", "jamas", "no", "nunca", "ni por error"]
            keywords_regular = ["regular", "normal", "más o menos", "meh", "aceptable", "quizás", "tal vez", "no se"]
            keywords_buena = ["buena", "bien", "excelente", "genial", "me encantó", "me gustó mucho", "muy probable", "probable", "seguramente", "seguro", "si"]

            if any(keyword in respuesta_texto for keyword in keywords_mala):
                chosen_option = "No muy probable 👎"
            elif any(keyword in respuesta_texto for keyword in keywords_regular):
                chosen_option = "Quizás 🤔"
            elif any(keyword in respuesta_texto for keyword in keywords_buena):
                chosen_option = "Muy probable 👍"
            
            if chosen_option:
                if chosen_option == "No muy probable 👎": rating_num = 1
                elif chosen_option == "Quizás 🤔": rating_num = 2
                else: rating_num = 3 # Corresponde a "Muy probable"
                
                current_survey.q1_nps = chosen_option
                current_survey.status = 'step_2_sent'
                current_survey.current_step = 2
                
                if rating_num == 1:
                    q2_text = "Entendido, gracias por tu honestidad. Para nosotros es crucial saber en qué fallamos. **¿Cuál fue la razón principal de tu calificación?**\n\nPuedes *escribirlo o enviarnos una nota de voz*. 🎤"
                elif rating_num == 2:
                    q2_text = "Gracias por tu respuesta. Nos encantaría saber qué podría convertir tu experiencia en una excelente. **¿Qué le falta a la app o qué podríamos hacer mejor para que la recomendaras?**\n\nPuedes *escribirlo o enviarnos una nota de voz*. 🎤"
                else:
                    q2_text = "¡Fantástico! Nos alegra mucho saber eso. **¿Qué fue lo que más te gustó o la característica que te pareció más útil?**\n\nPuedes *escribirlo o en una nota de voz*. 🎤"
                
                send_whatsapp_message(user_id, q2_text)
                db.commit()
            else:
                q1_text_retry = "No te pude entender. Por favor, elige una de las opciones con los botones."
                q1_buttons_retry = ["No muy probable 👎", "Quizás 🤔", "Muy probable 👍"]
                send_whatsapp_message(user_id, q1_text_retry, q1_buttons_retry)

        elif current_survey.current_step == 2:
            current_survey.q2_reason = user_message_text
            current_survey.status = 'step_3_sent'
            current_survey.current_step = 3
            db.commit()
            q3_text = "Entendido. Ahora, pensando en las características principales de la app, ¿cuál de estas áreas es la *más importante* para ti?"
            q3_buttons = ["Diseño/Usabilidad ✨", "Rendimiento 🚀", "Funciones 🛠️"]
            send_whatsapp_message(user_id, q3_text, q3_buttons)

        elif current_survey.current_step == 3:
            respuesta_texto = user_message_text.lower()
            chosen_option = None

            keywords_diseno = ["diseño", "usabilidad", "fácil", "interfaz", "apariencia", "interfaz", "interfaces", "vistas", "colores"]
            keywords_rendimiento = ["velocidad", "rendimiento", "rápida", "lenta", "carga", "optimizacion"]
            keywords_funciones = ["funciones", "características", "herramientas", "opciones", "funcionalidades"]

            if any(keyword in respuesta_texto for keyword in keywords_diseno):
                chosen_option = "Diseño/Usabilidad ✨"
            elif any(keyword in respuesta_texto for keyword in keywords_rendimiento):
                chosen_option = "Rendimiento 🚀"
            elif any(keyword in respuesta_texto for keyword in keywords_funciones):
                chosen_option = "Funciones 🛠️"

            if chosen_option:
                current_survey.q3_priority = chosen_option
                current_survey.status = 'step_4_sent'
                current_survey.current_step = 4
                db.commit()
                q4_text = "Gracias. Si tuvieras una varita mágica, *¿qué única función o mejora añadirías a la aplicación?*"
                send_whatsapp_message(user_id, q4_text)
            else:
                send_whatsapp_message(user_id, "No te pude entender. Por favor, elige una de las opciones con los botones.")

        elif current_survey.current_step == 4:
            current_survey.q4_magic_wand = user_message_text
            current_survey.status = 'step_5_sent'
            current_survey.current_step = 5
            db.commit()
            q5_text = "¡Ya casi terminamos! ¿Cómo descubriste nuestra aplicación?"
            q5_buttons = ["Redes Sociales 📱", "Por un amigo 🗣️", "Navegando la web 🌐"]
            send_whatsapp_message(user_id, q5_text, q5_buttons)

        elif current_survey.current_step == 5:
            respuesta_texto = user_message_text.lower()
            chosen_option = None

            keywords_redes = ["redes", "sociales", "instagram", "facebook", "tiktok", "un post", "un reel"]
            keywords_amigo = ["amigo", "amiga", "recomendación", "me dijeron", "un conocido", "una conocida", "conocido", "conocida"]
            keywords_web = ["web", "navegando", "internet", "google", "buscando", "anuncio", "opera"]

            if any(keyword in respuesta_texto for keyword in keywords_redes):
                chosen_option = "Redes Sociales 📱"
            elif any(keyword in respuesta_texto for keyword in keywords_amigo):
                chosen_option = "Por un amigo 🗣️"
            elif any(keyword in respuesta_texto for keyword in keywords_web):
                chosen_option = "Navegando la web 🌐"

            if chosen_option:
                current_survey.q5_discovery = chosen_option
                current_survey.status = 'completed'
                current_survey.current_step = 6
                current_survey.updated_at = datetime.datetime.utcnow()

                send_whatsapp_message(user_id, "¡Eso es todo! Muchísimas gracias por tu tiempo y por ayudarnos a construir una mejor aplicación. ¡Tu feedback es increíblemente valioso para nosotros! 🙏")

                try:
                    full_feedback_text = f"NPS: {current_survey.q1_nps}. Razón: {current_survey.q2_reason}. Prioridad: {current_survey.q3_priority}. Sugerencia: {current_survey.q4_magic_wand}."
                    
                    prompt_sentiment = f"Analiza el sentimiento general del siguiente feedback. Responde solo 'Positivo', 'Negativo' o 'Neutral'. Feedback: \"{full_feedback_text}\""
                    response_sentiment = generate_content_with_retry(model_text, prompt_sentiment)
                    current_survey.final_sentiment = response_sentiment.text.strip()
                    
                    if current_survey.q1_nps != "muy probable 👍":
                        prompt_summary = f"Del siguiente feedback, resume la queja o sugerencia principal en una frase corta y accionable: \"{full_feedback_text}\""
                        response_summary = generate_content_with_retry(model_text, prompt_summary)
                        current_survey.final_summary = response_summary.text.strip()
                    
                    db.commit()
                    print("Análisis de Gemini completado y guardado.")
                except Exception as e:
                    print(f"Error en el análisis final con Gemini: {e}")
                    db.rollback()
            else:
                send_whatsapp_message(user_id, "No te pude entender. Por favor, elige una de las opciones con los botones.")
    
    else:
        send_whatsapp_message(user_id, "Hola. Si quieres dejarnos un comentario sobre la app, por favor, envía la frase: quiero dejar un comentario")
        
    db.close()
    print("--- FIN TAREA ---")