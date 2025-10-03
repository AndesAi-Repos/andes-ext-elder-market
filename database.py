# database.py (VERSIÓN FINAL Y CORRECTA PARA LA ENCUESTA DE 5 PREGUNTAS)

import os
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Cargar Variables de Entorno ---
load_dotenv()

# --- Configuración de la Conexión a la Base de Datos ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Motor y Sesión de SQLAlchemy ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DEFINICIÓN DEL MODELO DE DATOS PARA ENCUESTA DE ADULTOS MAYORES ---
class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Control de la encuesta
    status = Column(String(50))
    current_step = Column(Integer)
    # is_in_followup = Column(Integer, default=0)  # 0=No, 1=Sí (SQLite compatible)
    # followup_question = Column(Integer, nullable=True)  # Número de pregunta que disparó el seguimiento
    
    # PRODUCTIVIDAD Y PARTICIPACIÓN (Preguntas 1-6)
    q1_actividades_productivas = Column(Text, nullable=True)  # P1: Actividades que generan ingresos
    q2_experiencia_valor = Column(Text, nullable=True)        # P2: Cómo aporta valor su experiencia
    q3_nivel_productividad = Column(String(10), nullable=True) # P3: Escala 1-5 productividad
    q4_uso_tecnologia = Column(String(50), nullable=True)     # P4: Uso de herramientas digitales
    q5_aprendizaje_tecnologia = Column(Text, nullable=True)   # P5: Facilidad aprender tecnología
    q6_oportunidades_digitales = Column(String(10), nullable=True) # P6: Escala 1-5 oportunidades
    
    # PROPÓSITO Y SENTIDO (Preguntas 7-9)
    q7_actividades_proposito = Column(Text, nullable=True)    # P7: Actividades que dan propósito
    q8_importancia_utilidad = Column(Text, nullable=True)     # P8: Importancia sentirse útil
    q9_nivel_proposito = Column(String(10), nullable=True)    # P9: Escala 1-5 propósito actual
    
    # COMPAÑÍA Y REDES SOCIALES (Preguntas 10-14)
    q10_situacion_vivienda = Column(String(100), nullable=True) # P10: Vive solo o acompañado
    q11_entorno_cercano = Column(Text, nullable=True)         # P11: Quiénes están cerca
    q12_frecuencia_social = Column(String(100), nullable=True) # P12: Frecuencia encuentros
    q13_soledad = Column(Text, nullable=True)                 # P13: Experiencias de soledad (respuesta larga)
    # q13b_circunstancias_soledad = Column(Text, nullable=True) # P13b: Circunstancias de soledad
    q14_nivel_apoyo_social = Column(String(10), nullable=True) # P14: Escala 1-5 apoyo social
    
    # DISFRUTE Y BIENESTAR (Preguntas 15-17)
    q15_actividades_disfrute = Column(Text, nullable=True)    # P15: Hobbies y entretenimiento
    q16_frecuencia_placer = Column(String(100), nullable=True) # P16: Tiempo para actividades placenteras
    q17_satisfaccion_disfrute = Column(String(10), nullable=True) # P17: Escala 1-5 satisfacción
    
    # DISCRIMINACIÓN POR EDAD (Preguntas 18-21)
    q18_edad = Column(Text, nullable=True)                    # P18: Edad (puede ser respuesta larga)
    q19_experiencias_discriminacion = Column(Text, nullable=True) # P19: Situaciones de discriminación
    q20_espacios_discriminacion = Column(Text, nullable=True) # P20: Dónde ha percibido discriminación
    q21_frecuencia_discriminacion = Column(String(10), nullable=True) # P21: Escala 1-5 frecuencia
    
    # REFLEXIONES Y NECESIDADES (Preguntas 22-27)
    q22_filosofia_vida = Column(Text, nullable=True)          # P22: Frase que resume su visión
    q23_mensaje_generaciones = Column(Text, nullable=True)    # P23: Mensaje a nuevas generaciones
    q24_compartir_adicional = Column(Text, nullable=True)     # P24: Qué más quiere compartir
    q25_experiencias_recientes = Column(Text, nullable=True)  # P25: Experiencias importantes
    q26_servicios_necesarios = Column(Text, nullable=True)    # P26: Servicios que necesita
    q27_limitaciones_fisicas = Column(Text, nullable=True)    # P27: Limitaciones físicas
    
    # Análisis final de IA
    final_sentiment = Column(String, nullable=True)
    final_summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# --- Función de Inicialización ---
def init_db():
    try:
        print("Creando tablas si no existen...")
        Base.metadata.create_all(bind=engine)
        print("¡Tablas listas!")
    except Exception as e:
        print(f"Error al inicializar la base de< datos: {e}")

if __name__ == "__main__":
    init_db()