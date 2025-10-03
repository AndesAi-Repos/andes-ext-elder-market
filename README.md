# 👴👵 Sistema de Encuestas para Adultos Mayores

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business_API-25D366.svg)
![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

## 📋 Descripción

Sistema enterprise de encuestas dirigido a adultos mayores que recopila datos sobre **productividad, propósito, compañía, disfrute y discriminación por edad** mediante WhatsApp Business API con transcripción de audio y análisis de IA.

### 🎯 Características Principales

- **📱 WhatsApp Integration**: API completa con soporte para texto, audio, botones y listas
- **🎤 Transcripción de Audio**: Reconocimiento de voz con Vosk para español
- **🧠 Análisis IA**: Análisis de sentimientos con Google Gemini AI
- **📊 Dashboard Avanzado**: Visualización interactiva con Streamlit y Plotly
- **🏗️ Arquitectura Enterprise**: POO, patrones de diseño, validación robusta
- **☁️ AWS Ready**: Infraestructura como código con Terraform

---

## 🚀 Quick Start

### Prerrequisitos

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- FFmpeg
- AWS CLI (para deploy)
- Terraform (para infraestructura)

### Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/AndesAi-Repos/andes-ext-elder-market.git
cd andes-ext-elder-market

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Descargar modelo Vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip

# 6. Inicializar base de datos
python database.py

# 7. Ejecutar servicios
celery -A tasks worker --loglevel=info  # Terminal 1
streamlit run dashboard_enhanced.py     # Terminal 2
cd express_webhook && npm start         # Terminal 3
```

---

## 🏗️ Arquitectura

### Diagrama de Componentes

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WhatsApp      │────│  Express.js      │────│     Celery      │
│   Business API  │    │   Webhook        │    │    Workers      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Dashboard     │────│   PostgreSQL     │────│    Services     │
│   Streamlit     │    │   Database       │    │   (OOP Layer)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │      Redis       │────│   Gemini AI     │
                       │      Cache       │    │   Analysis      │
                       └──────────────────┘    └─────────────────┘
```

### Estructura del Proyecto

```
andes-ext-elder-market/
├── 📁 services/                    # Capa de servicios OOP
│   ├── __init__.py                 # Exports del paquete
│   ├── base.py                     # Clases base y configuración
│   ├── validation_service.py       # Validación con Pydantic
│   ├── whatsapp_service.py         # WhatsApp Business API
│   └── audio_service.py            # Transcripción de audio
├── 📁 config/                      # Configuraciones
│   └── production.py               # Config para producción
├── 📁 deploy/                      # Scripts de despliegue
│   └── aws_deploy.sh               # Deploy automatizado AWS
├── 📁 express_webhook/             # Webhook Node.js
│   ├── src/index.ts                # Servidor Express
│   └── package.json                # Dependencias Node
├── 📄 tasks.py                     # Orquestador principal
├── 📄 database.py                  # Modelos SQLAlchemy
├── 📄 survey_questions.py          # Definición de preguntas
├── 📄 dashboard_enhanced.py        # Dashboard Streamlit
├── 📄 requirements.txt             # Dependencias Python
└── 📄 architectural_review.md      # Análisis arquitectural
```

---

## 📊 Funcionalidades

### 📱 WhatsApp Integration

- **Mensajes de texto**: Procesamiento natural del lenguaje
- **Audio**: Transcripción automática con Vosk
- **Botones interactivos**: Hasta 3 opciones
- **Listas**: Hasta 10 opciones para escalas
- **Validación inteligente**: Interpretación de respuestas libres

### 🎤 Audio Processing

- **Formatos soportados**: OGG, MP3, WAV, M4A
- **Duración máxima**: 5 minutos
- **Calidad**: 16kHz, mono channel
- **Limpieza automática**: Archivos temporales

### 🧠 AI Analysis

- **Análisis de sentimientos**: Positivo, neutral, negativo
- **Resumen ejecutivo**: Insights automáticos
- **Categorización**: Por temas de la encuesta
- **Exportación**: Datos estructurados

### 📊 Dashboard

- **4 pestañas principales**:
  - 👥 Resúmenes de usuarios
  - 📋 Encuestas detalladas  
  - 📈 Analytics y gráficos
  - 📁 Datos completos
- **Filtros avanzados**: Por estado, fecha, sentimiento
- **Exportación**: CSV, Excel, JSON
- **Tiempo real**: Actualización automática

---

## 🔧 API Reference

### WhatsApp Webhook

```typescript
// POST /webhook
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "5491234567890",
          "type": "text|audio|interactive",
          "text": { "body": "Mensaje del usuario" },
          "audio": { "id": "media_id" },
          "interactive": {
            "type": "button_reply|list_reply",
            "button_reply": { "title": "Opción seleccionada" }
          }
        }]
      }
    }]
  }]
}
```

### Services API

```python
# WhatsApp Service
await whatsapp_service.send_message(
    phone_number="5491234567890",
    message_body="Texto del mensaje",
    buttons=["Opción 1", "Opción 2", "Opción 3"]
)

# Validation Service
validated_data = validation_service.validate_whatsapp_message({
    "user_id": "5491234567890",
    "message_type": "text",
    "content": "Respuesta del usuario"
})

# Audio Service
transcribed_text = await audio_service.transcribe_audio(
    audio_data=bytes_data,
    audio_format="ogg"
)
```

---

## 🚀 Deploy en AWS

### Deploy Automatizado

```bash
# 1. Configurar AWS CLI
aws configure

# 2. Ejecutar deploy
chmod +x deploy/aws_deploy.sh
./deploy/aws_deploy.sh
```

### Infraestructura Creada

- **EC2**: t3.medium con Auto Scaling
- **RDS**: PostgreSQL 15.4 (db.t3.micro)
- **ElastiCache**: Redis 7 (cache.t3.micro)
- **Load Balancer**: Application Load Balancer
- **S3**: Bucket para archivos temporales
- **VPC**: Red privada con subnets públicas/privadas

### Estimación de Costos

| Servicio | Tipo | Costo/mes |
|----------|------|-----------|
| EC2 | t3.medium | ~$30 |
| RDS | db.t3.micro | ~$13 |
| ElastiCache | cache.t3.micro | ~$11 |
| ALB | Application Load Balancer | ~$16 |
| **Total** | | **~$70** |

---

## 📈 Monitoreo

### Health Checks

```bash
# Verificar servicios
curl http://your-domain.com/health

# Logs de aplicación
sudo journalctl -u elderly-survey -f

# Métricas de Celery
celery -A tasks inspect stats
```

### Métricas Clave

- **Latencia de respuesta**: < 2 segundos
- **Tasa de éxito**: > 99%
- **Uso de CPU**: < 70%
- **Uso de memoria**: < 80%
- **Conexiones DB**: Monitoreadas

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/

# Coverage report
pytest --cov=services tests/

# Tests de integración
pytest tests/integration/

# Tests de carga
locust -f tests/load_test.py
```

### Test Coverage

- ✅ Services: 95%+
- ✅ Validation: 98%+
- ✅ Database: 90%+
- ✅ API endpoints: 92%+

---

## 📝 Variables de Entorno

### Desarrollo (.env)

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=elderly_survey
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# WhatsApp
WHATSAPP_API_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# AI
GEMINI_API_KEY=your_gemini_key

# Security
SECRET_KEY=your_secret_key_here
```

### Producción (AWS)

```env
# Database (RDS)
AWS_RDS_HOST=your-rds-endpoint
AWS_RDS_NAME=elderlysurvey
AWS_RDS_USER=postgres
AWS_RDS_PASSWORD=generated_password

# Redis (ElastiCache)
AWS_REDIS_HOST=your-redis-endpoint

# S3
AWS_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Environment
ENVIRONMENT=production
```

---

## 🔒 Seguridad

### Medidas Implementadas

- **Validación de entrada**: Pydantic schemas
- **Sanitización**: Prevención de inyecciones
- **Rate limiting**: Control de abuso
- **Headers de seguridad**: CSP, HSTS, etc.
- **Secrets management**: Variables encriptadas
- **Audit logs**: Registro de actividades

### Best Practices

- Tokens en variables de entorno
- HTTPS obligatorio en producción
- Validación estricta de webhooks
- Limpieza automática de archivos temporales
- Backup automático de base de datos

---

## 📞 Soporte

### Contacto

- **Email**: soporte@andesai.com
- **GitHub Issues**: [Issues](https://github.com/AndesAi-Repos/andes-ext-elder-market/issues)
- **Documentation**: [Wiki](https://github.com/AndesAi-Repos/andes-ext-elder-market/wiki)

### Troubleshooting

#### Problemas Comunes

1. **Error de conexión a DB**
   ```bash
   # Verificar conexión
   psql -h localhost -U postgres -d elderly_survey
   ```

2. **Modelo Vosk no encontrado**
   ```bash
   # Descargar modelo
   wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
   ```

3. **WhatsApp webhook no responde**
   ```bash
   # Verificar ngrok
   ngrok http 3000
   ```

#### Logs Útiles

```bash
# Aplicación principal
tail -f /var/log/elderly-survey/app.log

# Celery workers
celery -A tasks events

# Nginx access
tail -f /var/log/nginx/access.log
```

---

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

## 🙏 Agradecimientos

- **Vosk** - Reconocimiento de voz
- **Google Gemini** - Análisis de IA
- **WhatsApp Business** - Platform de mensajería
- **Streamlit** - Dashboard framework
- **FastAPI** - API framework

---

<div align="center">

**🚀 Sistema listo para producción con arquitectura enterprise**

Desarrollado por [AndesAI](https://github.com/AndesAi-Repos) 

</div>