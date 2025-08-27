import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import sys

def run_migration():
    """
    Este script actualiza el esquema de la tabla 'feedbacks' para adaptarlo
    al nuevo sistema de encuestas conversacionales.

    Ejecución:
    1. Renombra las columnas 'sentiment' y 'summary'.
    2. Añade nuevas columnas para gestionar el estado y las respuestas de la encuesta.
    3. Elimina columnas antiguas que ya no son necesarias.
    """
    print("======================================================")
    print("=  Iniciando Migración de la Base de Datos para el   =")
    print("=            Sistema de Encuestas v2.0               =")
    print("======================================================")
    
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        print("\n[ERROR] Faltan variables de entorno para la base de datos en el archivo .env.")
        print("Asegúrate de que DB_USER, DB_PASSWORD, DB_HOST, DB_PORT y DB_NAME estén configurados.")
        sys.exit(1) # Termina el script si faltan credenciales

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("\n[INFO] Conexión con la base de datos establecida.")
            
            # Usamos una transacción para asegurar que todos los cambios se apliquen
            # de forma atómica (o todo o nada).
            with connection.begin() as transaction:
                
                print("\n--- PASO 1/3: Renombrando columnas antiguas ---")
                try:
                    connection.execute(text("ALTER TABLE feedbacks RENAME COLUMN sentiment TO final_sentiment;"))
                    connection.execute(text("ALTER TABLE feedbacks RENAME COLUMN summary TO final_summary;"))
                    print("[ÉXITO] Columnas 'sentiment' y 'summary' renombradas a 'final_sentiment' y 'final_summary'.")
                except Exception as e:
                    # Este error es esperado si las columnas ya fueron renombradas
                    if "does not exist" in str(e):
                        print("[AVISO] Las columnas 'sentiment' y 'summary' no existen. Probablemente ya fueron renombradas. Saltando paso.")
                    else:
                        raise e

                print("\n--- PASO 2/3: Añadiendo nuevas columnas para la encuesta ---")
                # Añadimos las columnas una por una para poder manejar errores si ya existen
                columnas_a_anadir = {
                    "status": "VARCHAR(50)",
                    "current_step": "INTEGER",
                    "q1_rating": "INTEGER",
                    "q2_feedback": "TEXT",
                    "updated_at": "TIMESTAMP WITHOUT TIME ZONE"
                }
                for col, tipo in columnas_a_anadir.items():
                    try:
                        connection.execute(text(f"ALTER TABLE feedbacks ADD COLUMN {col} {tipo};"))
                        print(f"[ÉXITO] Columna '{col}' añadida.")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"[AVISO] La columna '{col}' ya existe. Saltando.")
                        else:
                            raise e

                print("\n--- PASO 3/3: Eliminando columnas obsoletas ---")
                columnas_a_eliminar = [
                    "message_type",
                    "original_text",
                    "transcribed_text",
                    "audio_path"
                ]
                for col in columnas_a_eliminar:
                    try:
                        connection.execute(text(f"ALTER TABLE feedbacks DROP COLUMN {col};"))
                        print(f"[ÉXITO] Columna obsoleta '{col}' eliminada.")
                    except Exception as e:
                        if "does not exist" in str(e):
                            print(f"[AVISO] La columna '{col}' no existe. Probablemente ya fue eliminada. Saltando.")
                        else:
                            raise e

                transaction.commit()
            
            print("\n======================================================")
            print("=  ¡Migración completada con éxito!                =")
            print("=  La tabla 'feedbacks' está lista para el nuevo   =")
            print("=  sistema.                                        =")
            print("======================================================")

    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("=      ERROR DURANTE LA MIGRACIÓN - NO SE HICIERON CAMBIOS     =")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"\nDetalles del error: {e}")
        print("\nPosibles causas:")
        print(" - El servicio de PostgreSQL no está corriendo.")
        print(" - Las credenciales en el archivo .env son incorrectas.")
        print(" - La tabla 'feedbacks' no existe (ejecuta 'database.py' primero).")

if __name__ == "__main__":
    run_migration()