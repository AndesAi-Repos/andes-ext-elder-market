import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import sys

def run_migration_v2():
    """
    Actualiza el esquema de la tabla 'feedbacks' a la v2.0 para la encuesta de 5 preguntas.
    Este script es 'idempotente', lo que significa que se puede ejecutar varias veces 
    sin causar errores si los cambios ya se han aplicado.
    """
    print("======================================================")
    print("=  Iniciando Migración v2.0 para Encuesta Completa   =")
    print("======================================================")
    
    # Cargar variables de entorno para la conexión
    load_dotenv()
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        print("\n[ERROR] Faltan variables de entorno para la base de datos en el archivo .env.")
        sys.exit(1)

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("\n[INFO] Conexión con la base de datos establecida.")
            
            with connection.begin() as transaction:
                
                print("\n--- PASO 1/2: Eliminando columnas antiguas (si existen) ---")
                columnas_a_eliminar = ["q1_rating", "q2_feedback"]
                for col in columnas_a_eliminar:
                    try:
                        connection.execute(text(f"ALTER TABLE feedbacks DROP COLUMN {col};"))
                        print(f"[ÉXITO] Columna antigua '{col}' eliminada.")
                    except Exception as e:
                        # Si la columna no existe, es un aviso, no un error.
                        if "does not exist" in str(e):
                            print(f"[AVISO] La columna '{col}' no existe. Saltando.")
                        else:
                            # Si es otro error, lo mostramos y detenemos
                            raise e

                print("\n--- PASO 2/2: Añadiendo nuevas columnas para la encuesta de 5 pasos ---")
                columnas_a_anadir = {
                    "q1_nps": "VARCHAR(50)",
                    "q2_reason": "TEXT",
                    "q3_priority": "VARCHAR(100)",
                    "q4_magic_wand": "TEXT",
                    "q5_discovery": "VARCHAR(100)"
                }
                for col, tipo in columnas_a_anadir.items():
                    try:
                        connection.execute(text(f"ALTER TABLE feedbacks ADD COLUMN {col} {tipo};"))
                        print(f"[ÉXITO] Columna nueva '{col}' añadida.")
                    except Exception as e:
                        # Si la columna ya existe, es un aviso, no un error.
                        if "already exists" in str(e):
                            print(f"[AVISO] La columna '{col}' ya existe. Saltando.")
                        else:
                            raise e

                transaction.commit()
            
            print("\n======================================================")
            print("=  ¡Migración v2.0 completada con éxito!           =")
            print("=  La tabla 'feedbacks' está lista para la encuesta de 5 preguntas. =")
            print("======================================================")

    except Exception as e:
        print(f"\n!!!!!!!!!!!!!! ERROR DURANTE LA MIGRACIÓN !!!!!!!!!!!!!!")
        print(f"Detalles: {e}")

if __name__ == "__main__":
    run_migration_v2()