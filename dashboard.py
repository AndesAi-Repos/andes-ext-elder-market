import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import SessionLocal, Feedback
from datetime import datetime, timedelta
import numpy as np
import os
from dotenv import load_dotenv
import warnings
import logging

# --- CONFIGURACIÓN INICIAL PARA UN ENTORNO LIMPIO ---
# Suprimir warnings de deprecación de Plotly y otros
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Suprimir logs de ALTS de las librerías de Google (método más efectivo)
# Esto debe ir ANTES de cualquier importación de google
os.environ['GRPC_VERBOSITY'] = 'NONE'
os.environ['GRPC_TRACE'] = ''

# Deshabilitar los logs del logger raíz de gRPC
logging.getLogger('grpc').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

# Importar Gemini después de configurar los logs
import google.generativeai as genai

# Cargar variables de entorno
load_dotenv()

# Configurar Gemini (verificación básica)
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("⚠️ Warning: GEMINI_API_KEY no encontrada en .env")

# Configuración de la página
st.set_page_config(
    page_title="Encuestas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E86AB;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2E86AB;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def generar_perfil_usuario_gemini(usuario_data):
    """Genera un perfil breve del usuario usando Gemini - OPTIMIZADO para menos tokens"""
    try:
        # Verificar si Gemini está configurado
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            return "🔑 API key de Gemini no configurada"
        
        # Solo usar los campos MÁS importantes para minimizar tokens
        respuestas_clave = []
        campos_esenciales = [
            ('q18_edad', 'edad'),
            ('q3_nivel_productividad', 'productividad'), 
            ('q4_uso_tecnologia', 'tecnología'),
            ('q13_soledad', 'social')
        ]
        
        for campo, key in campos_esenciales:
            if campo in usuario_data and usuario_data[campo] and str(usuario_data[campo]).strip() != '':
                # Acortar las respuestas para ahorrar tokens
                respuesta = str(usuario_data[campo])[:50]  # Máximo 50 caracteres
                respuestas_clave.append(f"{key}: {respuesta}")
        
        if len(respuestas_clave) < 2:  # Mínimo 2 respuestas para perfil
            return "📝 Necesita más respuestas para análisis IA"
        
        # Configurar modelo aquí para evitar problemas de inicialización
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-pro')  # Cambiar a modelo estable
        generation_config = {"temperature": 0.3}
        
        # Prompt ultra-compacto para ahorrar tokens
        prompt = f"""Perfil empático de adulto mayor (máx 60 palabras):
{' | '.join(respuestas_clave)}
Enfoque: fortalezas y actitud positiva."""
        
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return "❌ Error: Modelo Gemini no disponible. Verifica configuración API."
        elif "permission" in error_msg.lower():
            return "🔐 Error: Sin permisos API. Verifica tu API key de Gemini."
        elif "quota" in error_msg.lower():
            return "⚠️ Error: Cuota API agotada. Intenta más tarde."
        else:
            return f"⚠️ Error IA: {str(e)[:50]}..."

@st.cache_data
def load_data():
    """Cargar datos de la base de datos"""
    db = SessionLocal()
    try:
        # Obtener todas las encuestas
        surveys = db.query(Feedback).all()
        
        if not surveys:
            return pd.DataFrame()
        
        # Convertir a DataFrame
        data = []
        for survey in surveys:
            row = {
                'id': survey.id,
                'user_id': survey.user_id,
                'status': survey.status,
                'current_step': survey.current_step,
                'created_at': survey.created_at,
                'updated_at': survey.updated_at,
                
                # Respuestas de la encuesta
                'q1_actividades_productivas': survey.q1_actividades_productivas,
                'q2_experiencia_valor': survey.q2_experiencia_valor,
                'q3_nivel_productividad': survey.q3_nivel_productividad,
                'q4_uso_tecnologia': survey.q4_uso_tecnologia,
                'q5_aprendizaje_tecnologia': survey.q5_aprendizaje_tecnologia,
                'q6_oportunidades_digitales': survey.q6_oportunidades_digitales,
                'q7_actividades_proposito': survey.q7_actividades_proposito,
                'q8_importancia_utilidad': survey.q8_importancia_utilidad,
                'q9_nivel_proposito': survey.q9_nivel_proposito,
                'q10_situacion_vivienda': survey.q10_situacion_vivienda,
                'q11_entorno_cercano': survey.q11_entorno_cercano,
                'q12_frecuencia_social': survey.q12_frecuencia_social,
                'q13_soledad': survey.q13_soledad,
                'q14_nivel_apoyo_social': survey.q14_nivel_apoyo_social,
                'q15_actividades_disfrute': survey.q15_actividades_disfrute,
                'q16_frecuencia_placer': survey.q16_frecuencia_placer,
                'q17_satisfaccion_disfrute': survey.q17_satisfaccion_disfrute,
                'q18_edad': survey.q18_edad,
                'q19_experiencias_discriminacion': survey.q19_experiencias_discriminacion,
                'q20_espacios_discriminacion': survey.q20_espacios_discriminacion,
                'q21_frecuencia_discriminacion': survey.q21_frecuencia_discriminacion,
                'q22_filosofia_vida': survey.q22_filosofia_vida,
                'q23_mensaje_generaciones': survey.q23_mensaje_generaciones,
                'q24_compartir_adicional': survey.q24_compartir_adicional,
                'q25_experiencias_recientes': survey.q25_experiencias_recientes,
                'q26_servicios_necesarios': survey.q26_servicios_necesarios,
                'q27_limitaciones_fisicas': survey.q27_limitaciones_fisicas,
                
                # Análisis
                'final_sentiment': survey.final_sentiment,
                'final_summary': survey.final_summary
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    finally:
        db.close()

def main():
    # Título principal
    st.markdown('<div class="main-header">📊 Dashboard - Encuesta Adultos Mayores</div>', unsafe_allow_html=True)
    
    # Cargar datos
    df = load_data()
    
    if df.empty:
        st.warning("⚠️ No hay datos disponibles en la base de datos.")
        return
    
    # Header con métricas principales y botón de actualizar
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    
    with col1:
        total_encuestas = len(df)
        st.metric("📊 Total Encuestas", total_encuestas)
    
    with col2:
        encuestas_completadas = len(df[df['status'] == 'completed'])
        st.metric("✅ Completadas", encuestas_completadas)
    
    with col3:
        usuarios_unicos = df['user_id'].nunique()
        st.metric("👥 Usuarios", usuarios_unicos)
    
    with col4:
        if total_encuestas > 0:
            tasa_completion = (encuestas_completadas / total_encuestas) * 100
            st.metric("📈 Tasa Éxito", f"{tasa_completion:.1f}%")
        else:
            st.metric("📈 Tasa Éxito", "0%")
    
    with col5:
        if st.button("🔄 Actualizar", help="Recargar datos desde la base de datos"):
            st.cache_data.clear()
            st.rerun()
    
    # Sidebar con filtros
    st.sidebar.title("🔧 Filtros")
    
    # Filtro por estado
    estados_disponibles = df['status'].unique().tolist()
    estado_seleccionado = st.sidebar.selectbox(
        "Estado de la encuesta:",
        ["Todos"] + estados_disponibles
    )
    
    # Filtro por fecha
    fecha_inicio = st.sidebar.date_input(
        "Fecha inicio:",
        value=df['created_at'].min().date() if not df.empty else datetime.now().date()
    )
    fecha_fin = st.sidebar.date_input(
        "Fecha fin:",
        value=df['created_at'].max().date() if not df.empty else datetime.now().date()
    )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if estado_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['status'] == estado_seleccionado]
    
    df_filtrado = df_filtrado[
        (df_filtrado['created_at'].dt.date >= fecha_inicio) &
        (df_filtrado['created_at'].dt.date <= fecha_fin)
    ]
    
    # Crear pestañas
    tab1, tab2, tab3 = st.tabs([
        "📈 Análisis y Métricas", 
        "👤 Perfiles de Usuarios", 
        "📋 Datos Completos"
    ])
    
    # TAB 1: Análisis y Métricas Generales
    with tab1:
        st.markdown('<div class="section-header">📈 Métricas Detalladas</div>', unsafe_allow_html=True)
        
        # Gráficos generales
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de estados
            if not df_filtrado.empty:
                status_counts = df_filtrado['status'].value_counts()
                fig_status = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Distribución por Estado de Encuesta"
                )
                fig_status.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Gráfico de progreso
            if not df_filtrado.empty:
                step_counts = df_filtrado['current_step'].value_counts().sort_index()
                fig_steps = px.bar(
                    x=step_counts.index,
                    y=step_counts.values,
                    title="Distribución por Paso de Encuesta",
                    labels={'x': 'Paso', 'y': 'Cantidad'}
                )
                st.plotly_chart(fig_steps, use_container_width=True)
        
        # Análisis de respuestas específicas
        st.markdown('<div class="section-header">📊 Análisis de Respuestas</div>', unsafe_allow_html=True)
        
        df_con_respuestas = df_filtrado[df_filtrado['current_step'] > 1]
        
        if not df_con_respuestas.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Análisis de productividad (Q3)
                if 'q3_nivel_productividad' in df_con_respuestas.columns:
                    productividad = df_con_respuestas['q3_nivel_productividad'].dropna()
                    if not productividad.empty:
                        fig_prod = px.histogram(
                            productividad,
                            title="Nivel de Productividad (Q3)",
                            labels={'value': 'Respuesta', 'count': 'Cantidad'}
                        )
                        st.plotly_chart(fig_prod, use_container_width=True)
                
                # Análisis de propósito (Q9)
                if 'q9_nivel_proposito' in df_con_respuestas.columns:
                    proposito = df_con_respuestas['q9_nivel_proposito'].dropna()
                    if not proposito.empty:
                        fig_prop = px.histogram(
                            proposito,
                            title="Nivel de Propósito (Q9)",
                            labels={'value': 'Respuesta', 'count': 'Cantidad'}
                        )
                        st.plotly_chart(fig_prop, use_container_width=True)
            
            with col2:
                # Análisis de uso de tecnología (Q4)
                if 'q4_uso_tecnologia' in df_con_respuestas.columns:
                    tecnologia = df_con_respuestas['q4_uso_tecnologia'].dropna()
                    if not tecnologia.empty:
                        tech_counts = tecnologia.value_counts()
                        fig_tech = px.pie(
                            values=tech_counts.values,
                            names=tech_counts.index,
                            title="Uso de Tecnología (Q4)"
                        )
                        st.plotly_chart(fig_tech, use_container_width=True)
                
                # Análisis de sentimientos integrado
                if 'final_sentiment' in df_filtrado.columns:
                    sentimientos = df_filtrado['final_sentiment'].dropna()
                    if not sentimientos.empty:
                        sentiment_counts = sentimientos.value_counts()
                        fig_sentiment = px.bar(
                            x=sentiment_counts.index,
                            y=sentiment_counts.values,
                            title="Análisis de Sentimientos",
                            labels={'x': 'Sentimiento', 'y': 'Cantidad'},
                            color=sentiment_counts.values,
                            color_continuous_scale='RdYlGn'
                        )
                        st.plotly_chart(fig_sentiment, use_container_width=True)
        else:
            st.info("No hay suficientes respuestas para mostrar análisis.")
    
    # TAB 2: Perfiles de Usuarios generados por Gemini
    with tab2:
        st.markdown('<div class="section-header">👤 Perfiles de Usuarios</div>', unsafe_allow_html=True)
        
        if not df_filtrado.empty:
            # Filtrar usuarios con al menos 5 respuestas
            usuarios_con_respuestas = df_filtrado[df_filtrado['current_step'] >= 5]
            
            if not usuarios_con_respuestas.empty:
                st.write(f"**{len(usuarios_con_respuestas)} usuarios disponibles para análisis IA:**")
                
                # Advertencia sobre el uso de API
                st.info("🔥 **Uso Responsable de IA:** Los perfiles se generan bajo demanda para optimizar el uso de la API de Gemini")
                
                # Mostrar usuarios en cards compactas
                for idx, usuario in usuarios_con_respuestas.head(10).iterrows():  # Limitar a 10 para no sobrecargar
                    with st.expander(f"👤 Usuario {usuario['user_id'][-6:]} - Paso {usuario['current_step']}", expanded=False):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write("**Información básica:**")
                            st.write(f"• **Estado:** {usuario['status']}")
                            st.write(f"• **Progreso:** {usuario['current_step']}/27")
                            st.write(f"• **Inicio:** {usuario['created_at'].strftime('%Y-%m-%d')}")
                            
                            # Mostrar algunas respuestas clave
                            if usuario['q18_edad']:
                                st.write(f"• **Edad:** {usuario['q18_edad']}")
                            if usuario['q3_nivel_productividad']:
                                st.write(f"• **Productividad:** {usuario['q3_nivel_productividad']}")
                            if usuario['q4_uso_tecnologia']:
                                st.write(f"• **Tecnología:** {usuario['q4_uso_tecnologia']}")
                        
                        with col2:
                            # Botón para generar perfil individual
                            if st.button(f"🤖 Generar Perfil IA", key=f"gen_{idx}"):
                                with st.spinner("Generando perfil con Gemini..."):
                                    perfil = generar_perfil_usuario_gemini(usuario.to_dict())
                                    st.session_state[f"perfil_{idx}"] = perfil
                        
                        with col3:
                            # Mostrar perfil si ya fue generado
                            if f"perfil_{idx}" in st.session_state:
                                st.write("**Perfil IA:**")
                                st.write(st.session_state[f"perfil_{idx}"])
                
                if len(usuarios_con_respuestas) > 10:
                    st.info(f"Mostrando los primeros 10 usuarios de {len(usuarios_con_respuestas)} totales para optimizar rendimiento.")
            else:
                st.info("No hay usuarios con suficientes respuestas para generar perfiles.")
        else:
            st.info("No hay datos de usuarios disponibles.")
    
    # TAB 3: Datos Completos
    with tab3:
        st.markdown('<div class="section-header">📋 Datos Completos</div>', unsafe_allow_html=True)
        
        if not df_filtrado.empty:
            st.write(f"**Total de registros:** {len(df_filtrado)}")
            
            # Mostrar todas las columnas
            columnas_completas = [
                'user_id', 'status', 'current_step', 'created_at', 'updated_at',
                'q1_actividades_productivas', 'q2_experiencia_valor', 'q3_nivel_productividad',
                'q4_uso_tecnologia', 'q5_aprendizaje_tecnologia', 'q6_oportunidades_digitales',
                'q7_actividades_proposito', 'q8_importancia_utilidad', 'q9_nivel_proposito',
                'q10_situacion_vivienda', 'q11_entorno_cercano', 'q12_frecuencia_social',
                'q13_soledad', 'q14_nivel_apoyo_social', 'q15_actividades_disfrute',
                'q16_frecuencia_placer', 'q17_satisfaccion_disfrute', 'q18_edad',
                'q19_experiencias_discriminacion', 'q20_espacios_discriminacion',
                'q21_frecuencia_discriminacion', 'q22_filosofia_vida', 'q23_mensaje_generaciones',
                'q24_compartir_adicional', 'q25_experiencias_recientes',
                'q26_servicios_necesarios', 'q27_limitaciones_fisicas',
                'final_sentiment', 'final_summary'
            ]
            
            # Filtrar solo las columnas que existen en el DataFrame
            columnas_existentes = [col for col in columnas_completas if col in df_filtrado.columns]
            
            # Ordenar por fecha de actualización (más recientes primero)
            df_ordenado = df_filtrado[columnas_existentes].sort_values('updated_at', ascending=False)
            
            st.dataframe(
                df_ordenado,
                width='stretch',
                hide_index=True
            )
            
            # Botón de descarga
            csv = df_ordenado.to_csv(index=False)
            st.download_button(
                label="📥 Descargar datos completos (CSV)",
                data=csv,
                file_name=f"encuesta_datos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay datos para mostrar.")

if __name__ == "__main__":
    main()