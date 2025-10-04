# survey_questions.py - Definición de las 27 preguntas para adultos mayores

ELDERLY_SURVEY_QUESTIONS = {
    1: {
        "text": "¡Hola! Vamos a conocer mejor su experiencia de vida.\n\n¿En qué actividades productivas que le generen ingresos o no (personales, laborales, familiares, comunitarias) participa actualmente?",
        "type": "open",
        "column": "q1_actividades_productivas"
    },
    2: {
        "text": "¿De qué manera siente que su experiencia y conocimientos siguen aportando valor en su vida diaria?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q2_experiencia_valor"
    },
    3: {
        "text": "En una escala de 1 a 5, ¿qué tan productivo(a) se siente hoy en día?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q3_nivel_productividad",
        "options": ["1 - Nada", "2 - Poco", "3 - Moderado", "4 - Bastante", "5 - Demasiado"]
    },
    4: {
        "text": "¿Utiliza herramientas digitales (celular, internet, redes sociales, aplicaciones) en su vida diaria?",
        "type": "buttons",
        "column": "q4_uso_tecnologia",
        "options": ["Sí, frecuentemente", "Ocasionalmente", "No las uso"]
    },
    5: {
        "text": "¿Qué tan fácil o difícil le resulta aprender nuevas tecnologías? Si le resulta difícil, ¿podría decirnos cuáles son los motivos?",
        "type": "open",
        "column": "q5_aprendizaje_tecnologia"
    },
    6: {
        "text": "En una escala de 1 a 5, ¿qué tanto cree que el mundo digital le ha abierto oportunidades de participación?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q6_oportunidades_digitales",
        "options": ["1 - Ninguna", "2 - Pocas", "3 - Algunas", "4 - Muchas", "5 - Muchísimas"]
    },
    7: {
        "text": "¿Qué actividades le dan un sentido de propósito en esta etapa de su vida?",
        "type": "open",
        "column": "q7_actividades_proposito"
    },
    8: {
        "text": "¿Qué tan importante es para usted sentirse útil dentro de su familia o comunidad?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q8_importancia_utilidad"
    },
    9: {
        "text": "En una escala de 1 a 5, ¿cómo calificaría el propósito que siente en su vida actualmente?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q9_nivel_proposito",
        "options": ["1 - Sin propósito", "2 - Poco", "3 - Moderado", "4 - Fuerte", "5 - Muy fuerte"]
    },
    10: {
        "text": "¿Actualmente está viviendo solo o comparte vivienda con algún familiar o amigo?",
        "type": "buttons",
        "column": "q10_situacion_vivienda",
        "options": ["Vivo solo/a", "Vivo acompañado/a", "Prefiero no decir"]
    },
    11: {
        "text": "¿Quiénes hacen parte de su entorno más cercano? (Hijos, nietos, amigos, etc.)",
        "type": "open",
        "column": "q11_entorno_cercano"
    },
    12: {
        "text": "¿Con qué frecuencia comparte tiempo con su familia o amigos?",
        "type": "list",
        "column": "q12_frecuencia_social",
        "options": ["Diariamente", "Varias x semana", "1 vez x semana", "Algunas x mes", "Raramente", "Nunca"]
    },
    13: {
        "text": "¿Ha sentido soledad o abandono en los últimos meses? ¿En qué circunstancias?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q13_soledad"
    },
    14: {
        "text": "En una escala de 1 a 5, ¿cómo describiría su nivel de compañía y apoyo social?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q14_nivel_apoyo_social",
        "options": ["1 - Sin apoyo", "2 - Poco", "3 - Moderado", "4 - Mucho", "5 - Excelente"]
    },
    15: {
        "text": "¿Qué actividades disfruta más en su día a día? (hobbies, viajes, entretenimiento, encuentro con amigos)?",
        "type": "open",
        "column": "q15_actividades_disfrute"
    },
    16: {
        "text": "¿Con qué frecuencia dedica tiempo a cosas que le producen placer o alegría?",
        "type": "list",
        "column": "q16_frecuencia_placer",
        "options": ["Diariamente", "Varias x semana", "1 vez x semana", "Algunas x mes", "Raramente", "Nunca"]
    },
    17: {
        "text": "En una escala de 1 a 5, ¿qué tan satisfecho(a) está con sus espacios de disfrute personal?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q17_satisfaccion_disfrute",
        "options": ["1 - Nada", "2 - Poco", "3 - Moderado", "4 - Mucho", "5 - Completo"]
    },
    18: {
        "text": "¿Cuántos años tiene?",
        "type": "list",
        "column": "q18_edad",
        "options": ["55-60 años", "61-65 años", "66-70 años", "71-75 años", "76-80 años", "81-85 años", "86-90 años", "Más de 90 años", "Prefiero no decir"]
    },
    19: {
        "text": "¿Alguna vez ha sentido que lo han tratado diferente por su edad? Si es así, ¿en cuáles situaciones?",
        "type": "open",
        "column": "q19_experiencias_discriminacion"
    },
    20: {
        "text": "¿En qué espacios (familia, trabajo, comunidad, servicios) ha percibido discriminación por su edad?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q20_espacios_discriminacion"
    },
    21: {
        "text": "En una escala de 1 a 5, ¿qué tan frecuente considera que enfrenta discriminación por edad?\n\nSeleccione una opción:",
        "type": "scale_1_5",
        "column": "q21_frecuencia_discriminacion",
        "options": ["1 - Nunca", "2 - Raramente", "3 - Ocasionalmente", "4 - Frecuentemente", "5 - Muy frecuentemente"]
    },
    22: {
        "text": "¿Hay alguna frase que resuma su forma de ver la vida en esta etapa?",
        "type": "open",
        "column": "q22_filosofia_vida"
    },
    23: {
        "text": "¿Qué mensaje le daría a las nuevas generaciones?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q23_mensaje_generaciones"
    },
    24: {
        "text": "¿Qué más le gustaría compartir que no le haya preguntado?",
        "type": "open",
        "column": "q24_compartir_adicional"
    },
    25: {
        "text": "¿Hay algo que considere importante destacar sobre sus experiencias recientes?",
        "type": "open",
        "column": "q25_experiencias_recientes"
    },
    26: {
        "text": "¿Cuál servicio considera que necesita y no lo encuentra o nadie se lo está ofreciendo?\n\n💬 Puede responder por texto o audio 🎤",
        "type": "open",
        "column": "q26_servicios_necesarios"
    },
    27: {
        "text": "¿Hay alguna actividad que no pueda realizar por alguna limitación de tipo físico?",
        "type": "open",
        "column": "q27_limitaciones_fisicas"
    }
}


INICIO_ENCUESTA_FRASES = [
    'quiero participar en la encuesta',
    'participar en la encuesta', 
    'encuesta',
    'quiero comenzar',
    'comenzar encuesta',
    'empezar',
    'iniciar'
]

def get_intelligent_response(user_text, options=None, keywords=None):
    """
    Procesa respuestas de usuario de manera inteligente
    Convierte respuestas libres a opciones estructuradas cuando es posible
    """
    if not user_text:
        return ""
    
    user_text = user_text.lower().strip()
    
    # Si hay opciones disponibles, intentar hacer matching inteligente
    if options:
        # Primero, buscar coincidencia exacta
        for option in options:
            if user_text == option.lower():
                return option
        
        # Luego, buscar coincidencias parciales
        for option in options:
            option_lower = option.lower()
            # Buscar palabras clave en la opción
            if any(word in option_lower for word in user_text.split() if len(word) > 2):
                return option
        
        # Mapeo específico para escalas numéricas
        if any(word in user_text for word in ['1', 'uno', 'nada', 'ningún', 'sin']):
            for option in options:
                if '1' in option or 'nada' in option.lower() or 'ningún' in option.lower():
                    return option
        
        if any(word in user_text for word in ['2', 'dos', 'poco', 'raro']):
            for option in options:
                if '2' in option or 'poco' in option.lower() or 'raro' in option.lower():
                    return option
        
        if any(word in user_text for word in ['3', 'tres', 'moderado', 'algunas', 'ocasional']):
            for option in options:
                if '3' in option or 'moderado' in option.lower() or 'algunas' in option.lower():
                    return option
        
        if any(word in user_text for word in ['4', 'cuatro', 'mucho', 'muchas', 'frecuente']):
            for option in options:
                if '4' in option or 'mucho' in option.lower() or 'muchas' in option.lower():
                    return option
        
        if any(word in user_text for word in ['5', 'cinco', 'extremo', 'muchísimas', 'completo', 'excelente']):
            for option in options:
                if '5' in option or 'extremo' in option.lower() or 'excelente' in option.lower():
                    return option
        
        # Para preguntas de sí/no/ocasional
        if any(word in user_text for word in ['sí', 'si', 'claro', 'por supuesto', 'frecuentemente']):
            for option in options:
                if 'frecuentemente' in option.lower() or 'sí' in option.lower():
                    return option
        
        if any(word in user_text for word in ['no', 'nunca', 'jamás']):
            for option in options:
                if 'no las uso' in option.lower() or 'nunca' in option.lower():
                    return option
        
        if any(word in user_text for word in ['ocasional', 'veces', 'a veces']):
            for option in options:
                if 'ocasionalmente' in option.lower():
                    return option
    
    # Si no hay coincidencia con opciones, devolver texto original
    return user_text
