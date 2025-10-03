import os
import uuid
import json
import requests
import logging
import ffmpeg
import wave
from datetime import datetime
from celery import Celery
from dotenv import load_dotenv
from vosk import Model, KaldiRecognizer
from database import SessionLocal, Feedback
from survey_questions import ELDERLY_SURVEY_QUESTIONS
from whatsapp_service import whatsapp_service
from audio_processing import process_elderly_audio, cleanup_audio_files

# Cargar variables de entorno
load_dotenv()

# Configuración de logging - SOLO INFO Y ERRORES
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuración de Celery
app = Celery('tasks', broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'))

# Configuraciones de WhatsApp (para compatibilidad)
WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

def send_whatsapp_message(to_number, message):
    """Envía mensaje de texto a WhatsApp - Versión refactorizada"""
    return whatsapp_service.send_text(to_number, message)

def send_whatsapp_buttons(to_number, body_text, buttons):
    """Envía mensaje con botones de respuesta rápida - Versión refactorizada"""
    return whatsapp_service.send_buttons(to_number, body_text, buttons)

def send_whatsapp_list(to_number, header_text, body_text, list_items):
    """Envía mensaje con lista de opciones - Versión refactorizada"""
    return whatsapp_service.send_list(to_number, header_text, body_text, list_items)

@app.task
def process_whatsapp_message(payload):
    """Procesa mensajes entrantes de WhatsApp"""
    try:
        logger.info("Procesando mensaje de WhatsApp...")
        
        # Extraer información del payload
        if 'entry' not in payload or not payload['entry']:
            return {'status': 'no_entry'}
        
        entry = payload['entry'][0]
        if 'changes' not in entry or not entry['changes']:
            return {'status': 'no_changes'}
        
        change = entry['changes'][0]
        value = change.get('value', {})
        
        # Filtrar mensajes de estado (delivered, read, sent) que no son útiles
        if 'statuses' in value and value['statuses']:
            logger.info("Mensaje de estado ignorado (delivered/read/sent)")
            return {'status': 'status_message_ignored'}
        
        if 'messages' not in value or not value['messages']:
            return {'status': 'no_messages'}
        
        message = value['messages'][0]
        from_number = message['from']
        message_type = message.get('type')
        
        logger.info(f"Mensaje de {from_number}, tipo: {message_type}")
        
        # Obtener sesión de base de datos
        db = SessionLocal()
        
        try:
            # Buscar encuesta existente
            survey = db.query(Feedback).filter_by(user_id=from_number).first()
            
            # Procesar según tipo de mensaje
            if message_type == 'text':
                text_body = message['text']['body'].strip()
                return handle_text_message(db, survey, from_number, text_body)
            
            elif message_type == 'interactive':
                if 'button_reply' in message['interactive']:
                    button_title = message['interactive']['button_reply']['title']
                    return handle_interactive_response(db, survey, from_number, button_title)
                
                elif 'list_reply' in message['interactive']:
                    list_title = message['interactive']['list_reply']['title']
                    return handle_interactive_response(db, survey, from_number, list_title)
            
            elif message_type == 'audio':
                return handle_audio_message(db, survey, from_number, message['audio'])
            
            else:
                send_whatsapp_message(from_number, "Por favor, envía solo mensajes de texto, audio o selecciona una opción.")
                return {'status': 'unsupported_type'}
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return {'status': 'error', 'error': str(e)}

def handle_text_message(db, survey, from_number, text_body):
    """Maneja mensajes de texto"""
    try:
        text_lower = text_body.lower().strip()
        
        # COMANDOS ESPECIALES DE TESTING (SIEMPRE PROCESADOS PRIMERO)
        if text_lower in ['reset', 'resetear', 'reiniciar']:
            return reset_survey(db, survey, from_number)
        
        if text_lower.startswith('ir a '):
            # Comando: "ir a 13" para saltar a pregunta específica
            try:
                question_num = int(text_lower.replace('ir a ', '').strip())
                return jump_to_question(db, survey, from_number, question_num)
            except ValueError:
                send_whatsapp_message(from_number, "❌ Formato incorrecto. Use: 'ir a 13'")
                return {'status': 'invalid_jump_command'}
        
        if text_lower in ['estado', 'info', 'status']:
            return show_survey_status(db, survey, from_number)
        
        # Palabras clave para iniciar encuesta NUEVA (solo si no hay encuesta activa)
        start_keywords = ['encuesta', 'empezar', 'comenzar', 'hola', 'inicio']
        
        if not survey:
            # Nueva conversación
            if any(keyword in text_body.lower() for keyword in start_keywords):
                return start_new_survey(db, from_number)
            else:
                # Mensaje de bienvenida
                welcome_msg = """¡Hola! 👋 

Soy un asistente digital especializado en encuestas. 

📋 Mi objetivo es conocer mejor sus experiencias, actividades y perspectivas de vida.

Para comenzar la encuesta, escriba: *encuesta*"""
                
                send_whatsapp_message(from_number, welcome_msg)
                return {'status': 'welcome_sent'}
        else:
            # Continuar encuesta existente
            return process_survey_response(db, survey, from_number, text_body)
    
    except Exception as e:
        logger.error(f"Error en handle_text_message: {e}")
        return {'status': 'error'}

def handle_interactive_response(db, survey, from_number, response_text):
    """Maneja respuestas de botones y listas"""
    try:
        if survey:
            return process_survey_response(db, survey, from_number, response_text)
        else:
            send_whatsapp_message(from_number, "Para comenzar la encuesta, escriba 'encuesta'")
            return {'status': 'no_survey'}
    
    except Exception as e:
        logger.error(f"Error en handle_interactive_response: {e}")
        return {'status': 'error'}

def handle_audio_message(db, survey, from_number, audio_data):
    """Maneja mensajes de audio con procesamiento directo usando Vosk"""
    try:
        if not survey:
            send_whatsapp_message(from_number, "Para comenzar la encuesta, escriba 'encuesta'")
            return {'status': 'no_survey'}
        
        logger.info("Procesando audio...")
        
        try:
            # Importar dependencias necesarias
            import uuid
            import ffmpeg
            import wave
            import json
            from vosk import Model, KaldiRecognizer
            
            # Verificar que el modelo Vosk esté disponible
            VOSK_MODEL_PATH = "vosk-model-small-es-0.42"
            if not os.path.exists(VOSK_MODEL_PATH):
                send_whatsapp_message(from_number, "🎤 Servicio de audio no disponible. Por favor responda por texto 📝")
                return {'status': 'vosk_model_not_found'}
            
            model_vosk = Model(VOSK_MODEL_PATH)
            
            # Obtener metadata del audio
            media_id = audio_data['id']
            api_token = WHATSAPP_API_TOKEN
            url_info = f"https://graph.facebook.com/v18.0/{media_id}/"
            headers_info = {'Authorization': f'Bearer {api_token}'}
            response_info = requests.get(url_info, headers=headers_info)
            response_info.raise_for_status()
            media_url = response_info.json()['url']
            
            # Descargar el archivo de audio
            headers_download = {'Authorization': f'Bearer {api_token}'}
            response_download = requests.get(media_url, headers=headers_download)
            response_download.raise_for_status()
            
            # Guardar audio original
            original_audio_path = f"temp_{uuid.uuid4()}.ogg"
            
            with open(original_audio_path, 'wb') as f: 
                f.write(response_download.content)
            
            # 🎵 PROCESAR AUDIO CON FILTROS AVANZADOS PARA ADULTOS MAYORES
            logger.info("🔧 Aplicando filtros de audio especializados...")
            processed_audio_path, audio_quality = process_elderly_audio(original_audio_path)
            
            logger.info(f"📊 Calidad de audio: {audio_quality['recommendation']}")
            logger.info(f"🎯 Claridad: {audio_quality['clarity']:.1f}% | "
                       f"Ruido: {audio_quality['noise_level']:.1f}% | "
                       f"Duración: {audio_quality['duration']:.1f}s")
            
            # Transcribir con Vosk usando el audio procesado
            with wave.open(processed_audio_path, "rb") as wf:
                rec = KaldiRecognizer(model_vosk, wf.getframerate())
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0: 
                        break
                    rec.AcceptWaveform(data)
            
            result_dict = json.loads(rec.FinalResult())
            transcribed_text = result_dict.get('text', '')
            
            # Limpiar archivos temporales
            os.remove(original_audio_path)
            if os.path.exists(processed_audio_path):
                os.remove(processed_audio_path)
            cleanup_audio_files()  # Limpiar archivos del servicio de audio
            
            if transcribed_text:
                logger.info(f"Audio transcrito exitosamente: '{transcribed_text}'")
                # Procesar la transcripción como respuesta de encuesta
                return process_survey_response(db, survey, from_number, transcribed_text)
            else:
                send_whatsapp_message(from_number, "🎤 No pude entender el audio. Por favor responda por texto 📝")
                return {'status': 'transcription_empty'}
                
        except ImportError as ie:
            logger.warning(f"Dependencias de audio no disponibles: {ie}")
            send_whatsapp_message(from_number, "🎤 Audio recibido. Por el momento, responda por texto 📝")
            return {'status': 'audio_dependencies_unavailable'}
            
        except Exception as ae:
            logger.error(f"Error procesando audio: {ae}")
            send_whatsapp_message(from_number, "🎤 Error procesando audio. Por favor responda por texto 📝")
            return {'status': 'audio_processing_error'}
            
    except Exception as e:
        logger.error(f"Error en handle_audio_message: {e}")
        send_whatsapp_message(from_number, "🎤 Error procesando audio. Por favor responda por texto 📝")
        return {'status': 'error'}

def start_new_survey(db, from_number):
    """Inicia una nueva encuesta"""
    try:
        # Verificar si ya existe una encuesta
        existing_survey = db.query(Feedback).filter_by(user_id=from_number).first()
        
        if existing_survey:
            if existing_survey.status == 'completed':
                # Reiniciar encuesta completada
                existing_survey.current_step = 1
                existing_survey.status = 'active'
                existing_survey.created_at = datetime.now()
                survey = existing_survey
            else:
                # Continuar encuesta existente
                survey = existing_survey
        else:
            # Crear nueva encuesta
            survey = Feedback(
                user_id=from_number,
                current_step=1,
                status='active',
                created_at=datetime.now()
            )
            db.add(survey)
        
        db.commit()
        
        # Mensaje de bienvenida
        welcome_msg = """👋 ¡Bienvenido/a a nuestra encuesta!

🎯 Esta encuesta está diseñada especialmente para adultos mayores y tiene como objetivo conocer mejor sus experiencias, actividades y perspectivas de vida.

📝 Puede responder las preguntas por texto.
⏱️ La encuesta toma aproximadamente 10-15 minutos.
🔒 Sus respuestas son completamente confidenciales.

¡Empezamos con la primera pregunta!"""
        
        send_whatsapp_message(from_number, welcome_msg)
        
        # Enviar primera pregunta
        send_current_question(survey, from_number)
        
        return {'status': 'survey_started'}
    
    except Exception as e:
        logger.error(f"Error iniciando encuesta: {e}")
        return {'status': 'error'}

def parse_intelligent_response(response_text, question_type, options=None):
    """Reconoce respuestas de múltiples formas para adultos mayores"""
    response_lower = response_text.lower().strip()
    
    if question_type == 'buttons' and options:
        # Mapear respuestas comunes a opciones de botones
        for option in options:
            option_lower = option.lower()
            
            # Buscar coincidencias exactas o parciales
            if option_lower in response_lower or response_lower in option_lower:
                return option
            
            # Mapear respuestas positivas (Sí)
            if any(word in option_lower for word in ['sí', 'si', 'frecuente']):
                if any(word in response_lower for word in ['sí', 'si', 'yes', 'claro', 'por supuesto', 'efectivamente', 'correcto', 'afirmativo']):
                    return option
            
            # Mapear respuestas negativas (No)
            if any(word in option_lower for word in ['no', 'nunca']):
                if any(word in response_lower for word in ['no', 'nunca', 'jamás', 'para nada', 'negativo', 'tampoco']):
                    return option
                    
            # Mapear respuestas ocasionales
            if any(word in option_lower for word in ['ocasional', 'a veces']):
                if any(word in response_lower for word in ['ocasional', 'a veces', 'algunas veces', 'de vez en cuando', 'poco', 'regular']):
                    return option
    
    elif question_type == 'scale_1_5' and options:
        # Reconocer números directos primero
        for i, option in enumerate(options):
            if f"{i+1}" in response_lower or f"opción {i+1}" in response_lower:
                return option
        
        # Reconocer palabras descriptivas
        for i, option in enumerate(options):
            option_lower = option.lower()
            
            # Extraer la parte descriptiva después del " - "
            if ' - ' in option_lower:
                description = option_lower.split(' - ')[1]
                
                # Mapear palabras clave específicas
                if i == 0:  # Primera opción (1 - Nada/Muy poco)
                    if any(word in response_lower for word in ['nada', 'cero', 'ningún', 'ninguna', 'muy poco', 'mínimo']):
                        return option
                elif i == 1:  # Segunda opción (2 - Poco)
                    if any(word in response_lower for word in ['poco', 'bajo', 'escaso', 'limitado']):
                        return option
                elif i == 2:  # Tercera opción (3 - Moderado/Regular)
                    if any(word in response_lower for word in ['moderado', 'regular', 'medio', 'normal', 'promedio']):
                        return option
                elif i == 3:  # Cuarta opción (4 - Mucho/Alto)
                    if any(word in response_lower for word in ['mucho', 'muy', 'alto', 'bastante', 'considerable']):
                        return option
                elif i == 4:  # Quinta opción (5 - Extremo/Máximo)
                    if any(word in response_lower for word in ['extremo', 'máximo', 'muchísimo', 'totalmente', 'completamente']):
                        return option
                
                # Buscar coincidencias parciales en la descripción
                description_words = description.split()
                if any(word in response_lower for word in description_words):
                    return option
    
    elif question_type == 'list' and options:
        # Para listas, buscar coincidencias similares a botones
        for option in options:
            option_lower = option.lower()
            if option_lower in response_lower or response_lower in option_lower:
                return option
            
            # Mapear frecuencias comunes
            if 'diario' in option_lower or 'diariamente' in option_lower:
                if any(word in response_lower for word in ['diario', 'todos los días', 'cada día', 'siempre']):
                    return option
            elif 'semana' in option_lower:
                if any(word in response_lower for word in ['semana', 'semanal']):
                    return option
            elif 'mes' in option_lower:
                if any(word in response_lower for word in ['mes', 'mensual']):
                    return option
            elif 'rara' in option_lower or 'nunca' in option_lower:
                if any(word in response_lower for word in ['rara', 'nunca', 'casi nunca', 'muy poco']):
                    return option
    
    # Si no encuentra coincidencia, devolver respuesta original
    return response_text

def reset_survey(db, survey, from_number):
    """TESTING: Resetea la encuesta para poder empezar de nuevo"""
    try:
        if survey:
            # Eliminar encuesta existente completamente
            user_id = survey.user_id
            db.delete(survey)
            db.commit()
            logger.info(f"Encuesta reseteada para usuario {user_id}")
            send_whatsapp_message(from_number, "🔄 ¡Encuesta eliminada completamente!\n\n✨ Escriba 'encuesta' para comenzar una nueva.")
        else:
            send_whatsapp_message(from_number, "ℹ️ No hay encuesta activa.\n\n✨ Escriba 'encuesta' para empezar una nueva.")
        return {'status': 'survey_reset'}
    except Exception as e:
        logger.error(f"Error reseteando encuesta: {e}")
        send_whatsapp_message(from_number, "❌ Error al resetear. Intente de nuevo.")
        return {'status': 'error'}

def jump_to_question(db, survey, from_number, question_num):
    """TESTING: Salta a una pregunta específica"""
    try:
        if not survey:
            send_whatsapp_message(from_number, "❌ No hay encuesta activa. Escriba 'encuesta' para empezar.")
            return {'status': 'no_survey'}
        
        if question_num < 1 or question_num > len(ELDERLY_SURVEY_QUESTIONS):
            send_whatsapp_message(from_number, f"❌ Pregunta inválida. Use números del 1 al {len(ELDERLY_SURVEY_QUESTIONS)}")
            return {'status': 'invalid_question'}
        
        # Saltar a la pregunta especificada
        survey.current_step = question_num
        # survey.is_in_followup = 0  # Reset seguimiento (TEMPORALMENTE DESHABILITADO)
        # survey.followup_question = None  # TEMPORALMENTE DESHABILITADO
        db.commit()
        
        send_whatsapp_message(from_number, f"⏭️ Saltando a pregunta {question_num}...")
        send_current_question(survey, from_number)
        
        return {'status': 'jumped_to_question'}
    except Exception as e:
        logger.error(f"Error saltando a pregunta: {e}")
        return {'status': 'error'}

def show_survey_status(db, survey, from_number):
    """TESTING: Muestra el estado actual de la encuesta"""
    try:
        if not survey:
            send_whatsapp_message(from_number, "📊 Estado: No hay encuesta activa")
            return {'status': 'no_survey'}
        
        status_msg = f"""📊 **Estado de la Encuesta**
        
👤 Usuario: {survey.user_id}
📍 Pregunta actual: {survey.current_step}/{len(ELDERLY_SURVEY_QUESTIONS)}
🔄 En seguimiento: No (funcionalidad deshabilitada)

**Comandos disponibles:**
• 'reset' - Resetear encuesta
• 'ir a X' - Saltar a pregunta X
• 'estado' - Ver este estado"""
        
        send_whatsapp_message(from_number, status_msg)
        return {'status': 'status_shown'}
    except Exception as e:
        logger.error(f"Error mostrando estado: {e}")
        return {'status': 'error'}

def validate_response_completion(survey, current_step):
    """Control estricto: valida que la pregunta actual esté respondida antes de avanzar"""
    try:
        if current_step > len(ELDERLY_SURVEY_QUESTIONS):
            return True
            
        question = ELDERLY_SURVEY_QUESTIONS[current_step]
        column_name = question['column']
        
        if hasattr(survey, column_name):
            current_response = getattr(survey, column_name)
            return current_response is not None and str(current_response).strip() != ''
        
        return False
    except Exception as e:
        logger.error(f"Error validando respuesta: {e}")
        return False

def handle_followup_response(db, survey, from_number, response_text):
    """Maneja respuestas a preguntas de seguimiento condicionales"""
    try:
        # Obtener el número de pregunta original que disparó el seguimiento
        original_question_num = survey.followup_question
        original_question = ELDERLY_SURVEY_QUESTIONS[original_question_num]
        
        # Obtener configuración de la pregunta de seguimiento
        follow_up_config = original_question['conditional']['follow_up']
        follow_up_column = follow_up_config['column']
        
        # Guardar respuesta de seguimiento
        if hasattr(survey, follow_up_column):
            setattr(survey, follow_up_column, response_text)
            logger.info(f"Respuesta de seguimiento guardada: {follow_up_column} = '{response_text}'")
        
        # Terminar el modo de seguimiento
        survey.is_in_followup = 0
        survey.followup_question = None
        
        # Avanzar al siguiente paso de la encuesta principal
        survey.current_step = original_question_num + 1
        survey.updated_at = datetime.now()
        
        # Enviar siguiente pregunta principal o finalizar
        if survey.current_step <= len(ELDERLY_SURVEY_QUESTIONS):
            send_current_question(survey, from_number)
            db.commit()
            return {'status': 'followup_completed_next_question'}
        else:
            send_whatsapp_message(from_number, "¡Felicitaciones! Ha completado toda la encuesta. Gracias por compartir su experiencia.")
            db.commit()
            return {'status': 'survey_completed'}
            
    except Exception as e:
        logger.error(f"Error procesando respuesta de seguimiento: {e}")
        survey.is_in_followup = 0  # Reset en caso de error
        return {'status': 'error'}

def send_followup_question(from_number, follow_up_config):
    """Envía una pregunta de seguimiento condicional"""
    try:
        question_text = follow_up_config['text']
        question_type = follow_up_config['type']
        
        if question_type == 'open':
            # Pregunta abierta, solo enviar texto
            return send_whatsapp_message(from_number, question_text)
        elif question_type == 'buttons':
            options = follow_up_config.get('options', [])
            return send_whatsapp_buttons(from_number, question_text, options)
        elif question_type == 'list':
            options = follow_up_config.get('options', [])
            return send_whatsapp_list(from_number, question_text, options)
        else:
            return send_whatsapp_message(from_number, question_text)
            
    except Exception as e:
        logger.error(f"Error enviando pregunta de seguimiento: {e}")
        return False

def process_survey_response(db, survey, from_number, response_text):
    """Procesa respuesta de encuesta con reconocimiento inteligente y control estricto"""
    try:
        # Verificar si estamos en una pregunta de seguimiento
        # TEMPORALMENTE DESHABILITADO hasta resolver problema de BD
        # if hasattr(survey, 'is_in_followup') and survey.is_in_followup == 1:
        #     return handle_followup_response(db, survey, from_number, response_text)
        
        current_step = survey.current_step
        
        if current_step > len(ELDERLY_SURVEY_QUESTIONS):
            send_whatsapp_message(from_number, "¡Ya ha completado la encuesta! Gracias por su participación.")
            return {'status': 'already_completed'}
        
        # Control estricto: verificar que no haya respuesta previa para este paso
        # MODO TESTING: Comentar la siguiente línea para permitir sobrescribir respuestas
        # if validate_response_completion(survey, current_step):
        if False:  # Temporalmente deshabilitado para testing
            # Ya respondió esta pregunta, informar amablemente
            next_step = current_step + 1
            if next_step <= len(ELDERLY_SURVEY_QUESTIONS):
                send_whatsapp_message(
                    from_number, 
                    f"Ya respondió la pregunta {current_step}. Continuemos con la siguiente pregunta."
                )
                survey.current_step = next_step
                send_current_question(survey, from_number)
                db.commit()
                return {'status': 'already_answered_proceeding'}
            else:
                send_whatsapp_message(from_number, "¡Ya ha completado toda la encuesta! 🎉")
                return {'status': 'survey_completed'}
        
        # Obtener pregunta actual
        question = ELDERLY_SURVEY_QUESTIONS[current_step]
        column_name = question['column']
        
        # Reconocimiento inteligente de respuesta
        parsed_response = parse_intelligent_response(
            response_text, 
            question['type'], 
            question.get('options')
        )
        
        # Guardar respuesta parseada
        if hasattr(survey, column_name):
            setattr(survey, column_name, parsed_response)
            logger.info(f"Respuesta inteligente guardada para pregunta {current_step}: '{response_text}' -> '{parsed_response}'")
        
        # Verificar si hay pregunta condicional de seguimiento
        # TEMPORALMENTE DESHABILITADO hasta resolver problema de BD
        # if 'conditional' in question:
        if False:  # Deshabilitar preguntas condicionales temporalmente
            conditional = question['conditional']
            trigger_answer = conditional['trigger_answer']
            
            # Si la respuesta coincide con el trigger, mostrar pregunta de seguimiento
            if parsed_response == trigger_answer or response_text.strip() == trigger_answer:
                follow_up = conditional['follow_up']
                # Marcar que estamos en una pregunta de seguimiento
                survey.is_in_followup = 1
                survey.followup_question = current_step
                db.commit()
                
                # Enviar pregunta de seguimiento
                send_followup_question(from_number, follow_up)
                return {'status': 'followup_sent'}
        
        # Avanzar al siguiente paso
        survey.current_step = current_step + 1
        survey.updated_at = datetime.now()
        
        if survey.current_step <= len(ELDERLY_SURVEY_QUESTIONS):
            # Enviar siguiente pregunta
            send_current_question(survey, from_number)
            db.commit()
            return {'status': 'question_sent', 'step': survey.current_step}
        else:
            # Encuesta completada
            survey.status = 'completed'
            survey.completed_at = datetime.now()
            db.commit()
            
            completion_msg = """¡Encuesta completada!

Muchas gracias por dedicar su tiempo a responder nuestras preguntas. Sus respuestas son muy valiosas para entender mejor las necesidades y experiencias de los adultos mayores.
¡Que tenga un excelente día!"""
            
            send_whatsapp_message(from_number, completion_msg)
            return {'status': 'survey_completed'}
    
    except Exception as e:
        logger.error(f"Error procesando respuesta: {e}")
        return {'status': 'error'}

def send_current_question(survey, from_number):
    """Envía la pregunta actual según su tipo"""
    try:
        current_step = survey.current_step
        
        if current_step > len(ELDERLY_SURVEY_QUESTIONS):
            return False
        
        question = ELDERLY_SURVEY_QUESTIONS[current_step]
        question_text = f"📝 Pregunta {current_step} de {len(ELDERLY_SURVEY_QUESTIONS)}\n\n{question['text']}"
        
        if question['type'] == 'open':
            return send_whatsapp_message(from_number, question_text)
        
        elif question['type'] == 'scale_1_5':
            return send_whatsapp_list(
                from_number,
                f"Pregunta {current_step}",
                question['text'],
                question['options']
            )
        
        elif question['type'] == 'buttons':
            return send_whatsapp_buttons(from_number, question_text, question['options'])
        
        else:
            return send_whatsapp_message(from_number, question_text)
    
    except Exception as e:
        logger.error(f"Error enviando pregunta: {e}")
        return False

@app.task
def health_check():
    """Verificación de salud del sistema"""
    try:
        # Verificar base de datos
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'questions_loaded': len(ELDERLY_SURVEY_QUESTIONS)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

if __name__ == '__main__':
    print("Sistema de Encuestas para Adultos Mayores - Refactorizado ✅")
    print(f"Preguntas disponibles: {len(ELDERLY_SURVEY_QUESTIONS)}")
    print(f"WhatsApp configurado: {'✅' if whatsapp_service.is_configured() else '❌'}")
    print("🏗️ Arquitectura: Clases profesionales + Interfaces")
    print("🚫 Reducción if/else: WhatsApp Service refactorizado")