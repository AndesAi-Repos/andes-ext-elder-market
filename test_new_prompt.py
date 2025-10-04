import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar API
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

print("🧪 Probando el nuevo prompt mejorado...")

# Simular datos reales más completos
informacion_usuario = [
    "• Edad: 73 años",
    "• Estado de salud: Buena",
    "• Nivel de productividad: 4 - Muy productivo", 
    "• Uso de tecnología: Ocasionalmente",
    "• Actividad principal: Cuidar nietos y jardinería",
    "• Apoyo familiar: Excelente",
    "• Participación social: Participa en club de lectura",
    "• Habilidades digitales: Básicas",
    "• Situación económica: Estable",
    "• Comentarios adicionales: Me gusta aprender cosas nuevas"
]

# Nuevo prompt mejorado
prompt = f"""Dame un resumen empático y personalizado de esta persona según la información de su encuesta:

{chr(10).join(informacion_usuario)}

Genera un perfil de máximo 80 palabras que destaque:
- Sus fortalezas y aspectos positivos
- Su personalidad y estilo de vida
- Sus habilidades y experiencias
- Su actitud hacia la vida

Enfoque: comprensivo, respetuoso y que resalte sus cualidades."""

try:
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    response = model.generate_content(prompt, generation_config={"temperature": 0.3})
    print(f"🎯 Nuevo perfil generado:")
    print(f"{response.text}")
    print(f"\n📊 Palabras: {len(response.text.split())}")
except Exception as e:
    print(f"❌ Error en test: {e}")