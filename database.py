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

# --- DEFINICIÓN DEL MODELO DE DATOS (LA TABLA ACTUALIZADA) ---
# Esta clase es el "mapa" que le dice a SQLAlchemy cómo es la tabla 'feedbacks'
# en PostgreSQL. Ahora incluye los nuevos campos para gestionar encuestas.
class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Nuevas columnas para el manejo de la encuesta
    status = Column(String(50)) # ej: 'initiated', 'completed', 'aborted'
    current_step = Column(Integer)
    q1_rating = Column(Integer, nullable=True) # Calificación de 1 a 5
    q2_feedback = Column(Text, nullable=True) # Feedback abierto (texto o transcripción)
    
    # Columnas para el resultado final del análisis de IA
    final_sentiment = Column(String, nullable=True)
    final_summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# --- Función de Inicialización ---
# Esta función crea la tabla si no existe.
# Después de la migración, no es estrictamente necesaria para correr el proyecto,
# pero es crucial si alguna vez empiezas con una base de datos vacía de nuevo.
def init_db():
    try:
        print("Creando tablas si no existen...")
        Base.metadata.create_all(bind=engine)
        print("¡Tablas listas!")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

if __name__ == "__main__":
    init_db()