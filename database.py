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

# --- DEFINICIÓN DEL MODELO DE DATOS (CORREGIDO) ---
# Este es el "mapa" que debe coincidir con la estructura de la base de datos
# después de ejecutar la migración v2.0.
class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Columnas para el manejo de la encuesta de 5 pasos
    status = Column(String(50))
    current_step = Column(Integer)
    q1_nps = Column(String(50), nullable=True)     # NPS: No muy probable, Quizás, Muy probable
    q2_reason = Column(Text, nullable=True)         # El "porqué" abierto
    q3_priority = Column(String(100), nullable=True)# Prioridad: Diseño, Velocidad, Funciones
    q4_magic_wand = Column(Text, nullable=True)     # La función mágica
    q5_discovery = Column(String(100), nullable=True)# Canal de descubrimiento
    
    # Columnas para el resultado final del análisis de IA
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