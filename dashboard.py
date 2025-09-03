# dashboard.py (VERSIÓN 2.1 - A PRUEBA DE BASE DE DATOS VACÍA)

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# ... (toda la configuración de la página y la conexión a la BD no cambia) ...
st.set_page_config(page_title="Dashboard de Feedback v2.0", page_icon="🚀", layout="wide")
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

@st.cache_data(ttl=30)
def load_data():
    try:
        query = "SELECT * FROM feedbacks WHERE status = 'completed' ORDER BY updated_at DESC;"
        df = pd.read_sql(query, con=engine)
        if not df.empty:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
        return df
    except Exception as e:
        # Si la tabla no existe aún, devolvemos un DataFrame vacío
        if "does not exist" in str(e):
            return pd.DataFrame()
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

# --- TÍTULO PRINCIPAL ---
st.title("🚀 Dashboard de Feedback de la App v2.0")
st.markdown("Análisis detallado de la nueva encuesta de 5 preguntas.")
st.markdown("---")

df_feedback = load_data()

# --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
# Verificamos si el DataFrame está vacío ANTES de intentar usarlo.
if df_feedback.empty:
    st.warning("Aún no hay encuestas completadas. ¡Los datos aparecerán aquí en tiempo real en cuanto un usuario termine la encuesta!")
    st.stop() # Detiene la ejecución del script para que no dé error

# --- CREACIÓN DE PESTAÑAS (El resto del código no cambia) ---
# ... (pega aquí el resto del código del dashboard que te di en el mensaje anterior, desde la línea 'tab1, tab2, tab3 = ...' hasta el final) ...
tab1, tab2, tab3 = st.tabs(["📈 Resumen General", "📊 Análisis Cualitativo", "🗃️ Todas las Respuestas"])

with tab1:
    st.header("📈 Resumen General (NPS y Prioridades)")
    total_encuestas = len(df_feedback)
    promotores = len(df_feedback[df_feedback['q1_nps'] == 'muy probable 👍'])
    pasivos = len(df_feedback[df_feedback['q1_nps'] == 'quizás 🤔'])
    detractores = len(df_feedback[df_feedback['q1_nps'] == 'no muy probable 👎'])
    nps_score = ((promotores / total_encuestas) - (detractores / total_encuestas)) * 100 if total_encuestas > 0 else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Encuestas Completadas", f"{total_encuestas} 📝")
    col2.metric("NPS Score", f"{nps_score:.1f}", help="Net Promoter Score = (% Promotores - % Detractores)")
    col3.metric("Promotores", f"{promotores} 👍")
    col4.metric("Detractores", f"{detractores} 👎")
    st.markdown("---")
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.subheader("¿Qué es lo más importante para los usuarios?")
        priority_counts = df_feedback['q3_priority'].value_counts().reset_index()
        fig_pie = px.pie(priority_counts, names='q3_priority', values='count', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_graf2:
        st.subheader("¿Cómo nos descubren los usuarios?")
        discovery_counts = df_feedback['q5_discovery'].value_counts().reset_index()
        fig_bar = px.bar(discovery_counts, x='q5_discovery', y='count', color='q5_discovery')
        st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.header("📊 Análisis Cualitativo (Texto y Audio)")
    st.subheader("Razones detrás de la calificación (Pregunta 2)")
    for index, row in df_feedback.dropna(subset=['q2_reason']).iterrows():
        nps_icon = "👍" if row['q1_nps'] == 'muy probable 👍' else ("🤔" if row['q1_nps'] == 'quizás 🤔' else "👎")
        with st.expander(f"{nps_icon} **Usuario `{row['user_id'][-4:]}` dijo:** *{row['q2_reason'][:50]}...*"):
            st.write(f"**Calificación NPS:** {row['q1_nps']}")
            st.write(f"**Feedback Completo:**")
            st.info(f"{row['q2_reason']}")
            if pd.notna(row['final_summary']):
                st.write("**Resumen por IA:**")
                st.success(f"{row['final_summary']}")
    st.markdown("---")
    st.subheader("Ideas de los Usuarios (Pregunta 'Varita Mágica')")
    for index, row in df_feedback.dropna(subset=['q4_magic_wand']).iterrows():
        with st.expander(f"💡 **Usuario `{row['user_id'][-4:]}` sugirió:** *{row['q4_magic_wand'][:50]}...*"):
            st.info(f"{row['q4_magic_wand']}")

with tab3:
    st.header("🗃️ Tabla Completa de Respuestas")
    st.info("Aquí puedes ver y buscar en todas las encuestas completadas.")
    columnas_visibles = ['updated_at', 'user_id', 'q1_nps', 'q2_reason', 'q3_priority', 'q4_magic_wand', 'q5_discovery', 'final_sentiment', 'final_summary']
    st.dataframe(df_feedback[columnas_visibles])

st.sidebar.header("Opciones")
if st.sidebar.button('Forzar Actualización'):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.info("Panel de control para el sistema de encuestas de satisfacción v2.0.")