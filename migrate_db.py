# migrate_db.py - Script para migrar y actualizar la base de datos

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database import init_db, SessionLocal

# Cargar variables de entorno
load_dotenv()

def migrate_database():
    """Ejecuta migraciones necesarias para la base de datos"""
    try:
        print("🔄 Iniciando migración de base de datos...")
        
        # Crear tablas si no existen
        print("📋 Creando/actualizando tablas...")
        init_db()
        
        # Obtener sesión de base de datos
        db = SessionLocal()
        
        try:
            # Verificar si las nuevas columnas existen
            print("🔍 Verificando nuevas columnas...")
            
            # Lista de columnas a agregar
            new_columns = [
                ("is_in_followup", "INTEGER DEFAULT 0"),
                ("followup_question", "INTEGER"),
                ("q13b_circunstancias_soledad", "TEXT")
            ]
            
            for column_name, column_type in new_columns:
                try:
                    # Intentar agregar la columna si no existe
                    alter_query = f"ALTER TABLE feedbacks ADD COLUMN {column_name} {column_type};"
                    db.execute(text(alter_query))
                    print(f"✅ Columna agregada: {column_name}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        print(f"ℹ️  Columna ya existe: {column_name}")
                    else:
                        print(f"⚠️  Error agregando {column_name}: {e}")
            
            # Actualizar tipo de columna q13_soledad
            try:
                # En PostgreSQL, cambiar el tipo de columna
                db.execute(text("ALTER TABLE feedbacks ALTER COLUMN q13_soledad TYPE VARCHAR(100);"))
                print("✅ Tipo de columna q13_soledad actualizado")
            except Exception as e:
                print(f"ℹ️  q13_soledad: {e}")
            
            db.commit()
            print("💾 Cambios guardados en la base de datos")
            
        finally:
            db.close()
        
        print("🎉 Migración completada exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✨ Base de datos lista para preguntas condicionales!")
    else:
        print("\n🚫 Migración falló. Revisar errores arriba.")