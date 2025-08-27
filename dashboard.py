# dashboard.py (VERSIÓN FINAL COMPATIBLE CON LA BASE DE DATOS DE ENCUESTAS)

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Feedback",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONEXIÓN A LA BASE DE DATOS ---
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# --- FUNCIÓN PARA CARGAR DATOS ---
@st.cache_data(ttl=30)
def load_data():
    try:
        query = "SELECT * FROM feedbacks WHERE status = 'completed' ORDER BY updated_at DESC;"
        df = pd.read_sql(query, con=engine)
        if not df.empty:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

# --- TÍTULO PRINCIPAL ---
st.title("🧠 Dashboard de Análisis de Encuestas")
st.markdown("---")

df_feedback = load_data()

if df_feedback.empty:
    st.warning("No se han encontrado encuestas completadas todavía. ¡Completa una encuesta para ver los datos!")
    st.stop()

# --- CREACIÓN DE PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Resumen General", "📊 Visualizaciones", "📝 Quejas y Sugerencias", "🗃️ Datos Crudos"])

# --- Pestaña 1: Resumen General (KPIs) ---
with tab1:
    st.header("📈 Resumen General")
    
    # --- MÉTRICAS USANDO LAS NUEVAS COLUMNAS ---
    total_feedbacks = len(df_feedback)
    positivos = len(df_feedback[df_feedback['final_sentiment'] == 'Positivo'])
    negativos = len(df_feedback[df_feedback['final_sentiment'] == 'Negativo'])

    porc_positivos = (positivos / total_feedbacks * 100) if total_feedbacks > 0 else 0
    porc_negativos = (negativos / total_feedbacks * 100) if total_feedbacks > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Encuestas Completadas", f"{total_feedbacks} 📝")
    col2.metric("Opiniones Positivas", f"{positivos} 👍", f"{porc_positivos:.1f}%")
    col3.metric("Opiniones Negativas", f"{negativos} 👎", f"{porc_negativos:.1f}%")

    st.markdown("---")

    st.subheader("Última Opinión Recibida")
    ultima_opinion = df_feedback.iloc[0]
    st.info(f"**Usuario:** `{ultima_opinion['user_id']}` | **Calificación:** `{int(ultima_opinion['q1_rating'])}/5` | **Sentimiento Final:** `{ultima_opinion['final_sentiment']}`")
    st.markdown(f"> _{ultima_opinion['q2_feedback']}_")

# --- Pestaña 2: Visualizaciones ---
with tab2:
    st.header("📊 Visualizaciones Detalladas")
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        # --- GRÁFICO CON LA NUEVA COLUMNA ---
        sentiment_counts = df_feedback['final_sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['final_sentiment', 'count']
        fig_pie = px.pie(sentiment_counts, 
                     names='final_sentiment', 
                     values='count', 
                     title='Distribución de Sentimientos',
                     color='final_sentiment',
                     color_discrete_map={'Positivo':'#2ECC71', 'Negativo':'#E74C3C', 'Neutral':'#3498DB'},
                     hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_graf2:
        df_feedback['fecha'] = df_feedback['updated_at'].dt.date
        feedback_por_dia = df_feedback['fecha'].value_counts().sort_index().reset_index()
        feedback_por_dia.columns = ['fecha', 'cantidad']
        fig_bar = px.bar(feedback_por_dia, x='fecha', y='cantidad', title='Volumen de Encuestas por Día')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- Pestaña 3: Quejas y Sugerencias ---
with tab3:
    st.header("📝 Quejas y Sugerencias (Análisis por IA)")
    # --- LÓGICA CON LAS NUEVAS COLUMNAS ---
    df_negativos = df_feedback[df_feedback['final_sentiment'] == 'Negativo'].copy()

    if not df_negativos.empty and 'final_summary' in df_negativos.columns and not df_negativos['final_summary'].dropna().empty:
        st.info("A continuación se muestran los resúmenes de las quejas más comunes, generados por Gemini.")
        for index, row in df_negativos.dropna(subset=['final_summary']).iterrows():
            with st.expander(f"🗣️ **{row['final_summary']}**"):
                st.write(f"**Opinión Original del Usuario `{row['user_id']}` (Calificación: {int(row['q1_rating'])}/5):**")
                st.write(f"> _{row['q2_feedback']}_")
    else:
        st.success("¡Buenas noticias! No se han encontrado resúmenes de quejas generados por la IA.")

# --- Pestaña 4: Datos Crudos ---
with tab4:
    st.header("🗃️ Tabla de Datos Crudos")
    st.info("Aquí puedes ver y buscar en todas las encuestas completadas.")
    
    # --- COLUMNAS ACTUALIZADAS ---
    columnas_visibles = [
        'updated_at', 'user_id', 'status', 'q1_rating', 
        'q2_feedback', 'final_sentiment', 'final_summary'
    ]
    columnas_existentes = [col for col in columnas_visibles if col in df_feedback.columns]
    st.dataframe(df_feedback[columnas_existentes])

# --- Barra Lateral (Sidebar) ---
st.sidebar.header("Opciones")
if st.sidebar.button('Forzar Actualización de Datos'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Panel de control para el sistema de encuestas de satisfacción de Andes AI.")