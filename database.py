import os
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base 

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construir la URL de conexión.
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- MOTOR Y SESIÓN DE SQLAlchemy ---
engine = create_engine(DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() 

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    message_type = Column(String) # Será 'text' o 'audio'
    original_text = Column(Text, nullable=True) # El mensaje de texto original
    transcribed_text = Column(Text, nullable=True) # El texto transcrito de un audio
    audio_path = Column(String, nullable=True) # La ruta donde se guarda el audio procesado
    sentiment = Column(String, index=True) # 'Positivo', 'Negativo' o 'Neutral'
    summary = Column(Text, nullable=True) # El resumen de la queja o sugerencia
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# --- FUNCIÓN DE INICIALIZACIÓN ---
def init_db():
    try:
        print("Intentando conectar a la base de datos para crear las tablas...")
        Base.metadata.create_all(bind=engine)
        print("¡Conexión exitosa! Tabla 'feedbacks' creada o ya existente.")
    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"ERROR: No se pudo conectar a la base de datos. Detalles:")
        print(e)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("POSIBLES SOLUCIONES:")
        print("1. ¿Está el servidor de PostgreSQL corriendo?")
        print("2. ¿Son correctos los datos (usuario, contraseña, host, etc.) en tu archivo .env?")
        print("3. Si tu contraseña tiene caracteres especiales, ¿probaste a ponerla entre comillas dobles en el .env?")


if __name__ == "__main__":
    print("Inicializando la base de datos...")
    init_db()