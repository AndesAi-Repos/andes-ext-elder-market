# tasks.py (VERSIÓN FINAL CON CIERRE CORRECTO DE ARCHIVOS)

import os
import uuid
import requests
import ffmpeg
import time
import json
import wave
from vosk import Model, KaldiRecognizer
from celery import Celery
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

from database import SessionLocal, Feedback

# --- CONFIGURACIÓN ---
load_dotenv()
celery_app = Celery(__name__, broker=os.getenv("CELERY_BROKER_URL"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {"temperature": 0.2}
model_text = genai.GenerativeModel('gemini-1.5-flash-latest')
VOSK_MODEL_PATH = "vosk-model-small-es-0.42"
if not os.path.exists(VOSK_MODEL_PATH):
    raise FileNotFoundError(f"El modelo de Vosk no se encuentra en la ruta: {VOSK_MODEL_PATH}.")
model_vosk = Model(VOSK_MODEL_PATH)


# --- FUNCIÓN DE AYUDA CON REINTENTOS PARA GEMINI ---
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


# --- TAREA PRINCIPAL DE CELERY ---
@celery_app.task(name='process_feedback_task')
def process_feedback(payload):
    print(f"--- INICIO TAREA --- Usuario: {payload['user_id']}, Tipo: {payload['type']}")

    final_text = ""
    db_entry = Feedback(user_id=payload['user_id'], message_type=payload['type'])

    if payload['type'] == 'audio':

        original_audio_path = f"temp_{uuid.uuid4()}.ogg"
        wav_audio_path = f"temp_{uuid.uuid4()}.wav"
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
            
            with open(original_audio_path, 'wb') as f: f.write(response_download.content)
            
            print("[FFMPEG_STEP] Convirtiendo audio a formato WAV para Vosk...")
            (ffmpeg.input(original_audio_path).output(wav_audio_path, acodec='pcm_s16le', ac=1, ar=16000).run(overwrite_output=True, quiet=True))
            
            print("[VOSK_STEP] Transcribiendo audio localmente...")
            with wave.open(wav_audio_path, "rb") as wf:
                rec = KaldiRecognizer(model_vosk, wf.getframerate())
                rec.SetWords(True)
                
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0: break
                    rec.AcceptWaveform(data)
            
            result_json = rec.FinalResult()
            result_dict = json.loads(result_json)
            final_text = result_dict['text']
            
            db_entry.transcribed_text = final_text
            print(f"[VOSK_STEP] Transcripción exitosa: '{final_text}'")

        except Exception as e:
            print(f"!!!!!!!!!!!!!! ERROR EN EL PROCESO DE AUDIO !!!!!!!!!!!!!!")
            print(f"Error: {e}")
            return
        finally:
            # Nos aseguramos de borrar los archivos temporales incluso si algo falla
            if os.path.exists(original_audio_path): os.remove(original_audio_path)
            if os.path.exists(wav_audio_path): os.remove(wav_audio_path)
            
    # --- LÓGICA DE PROCESAMIENTO DE TEXTO ---
    elif payload['type'] == 'text':
        final_text = payload['content']
        db_entry.original_text = final_text
    
    if not final_text:
        print("Texto final vacío. Terminando tarea.")
        return

    # --- ANÁLISIS DE IA CON GEMINI ---
    try:
        print("[GEMINI_STEP] Analizando sentimiento (con reintentos)...")
        prompt_sentiment = f"""Analiza el sentimiento del siguiente comentario. Responde únicamente con 'Positivo', 'Negativo' o 'Neutral'. Comentario: "{final_text}" """
        response_sentiment = generate_content_with_retry(model_text, prompt_sentiment)
        sentiment = response_sentiment.text.strip()
        db_entry.sentiment = sentiment
        print(f"[GEMINI_STEP] Sentimiento detectado: {sentiment}")

        if sentiment == 'Negativo':
            print("[GEMINI_STEP] Generando resumen de queja (con reintentos)...")
            prompt_summary = f"""Del siguiente comentario negativo, resume en una frase concisa la queja principal. Comentario: "{final_text}" """
            response_summary = generate_content_with_retry(model_text, prompt_summary)
            db_entry.summary = response_summary.text.strip()
            print(f"[GEMINI_STEP] Resumen de queja: {db_entry.summary}")

    except Exception as e:
        print(f"ERROR FINAL DURANTE ANÁLISIS CON GEMINI: {e}")
        return

    # --- GUARDAR EN BASE DE DATOS ---
    db_session = SessionLocal()
    try:
        db_session.add(db_entry)
        db_session.commit()
        print("¡Resultados guardados en la base de datos!")
    except Exception as e:
        db_session.rollback()
        print(f"ERROR AL GUARDAR EN BASE DE DATOS: {e}")
    finally:
        db_session.close()
    
    print("--- FIN TAREA ---")