# dashboard.py

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
        query = "SELECT * FROM feedbacks ORDER BY created_at DESC;"
        df = pd.read_sql(query, con=engine)
        # Aseguramos que la columna de fecha esté en el formato correcto
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame() # Devuelve un DataFrame vacío si hay error

# --- TÍTULO PRINCIPAL ---
st.title("🧠 Dashboard de Análisis de Opiniones")
st.markdown("---")

# --- CARGA DE DATOS ---
df_feedback = load_data()

# Si no hay datos, mostramos un mensaje y paramos la ejecución.
if df_feedback.empty:
    st.warning("No se han encontrado datos de feedback todavía. ¡Envía un mensaje para empezar!")
    st.stop()


# --- PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Resumen General", "📊 Visualizaciones", "📝 Quejas y Sugerencias", "🗃️ Datos Crudos"])


# --- Pestaña 1: Resumen General (KPIs) ---
with tab1:
    st.header("📈 Resumen General")
    
    # Métricas clave
    total_feedbacks = len(df_feedback)
    positivos = len(df_feedback[df_feedback['sentiment'] == 'Positivo'])
    negativos = len(df_feedback[df_feedback['sentiment'] == 'Negativo'])
    neutrales = len(df_feedback[df_feedback['sentiment'] == 'Neutral'])

    # Calculamos porcentajes de forma segura
    porc_positivos = (positivos / total_feedbacks * 100) if total_feedbacks > 0 else 0
    porc_negativos = (negativos / total_feedbacks * 100) if total_feedbacks > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Opiniones Recibidas", f"{total_feedbacks} 💬")
    col2.metric("Opiniones Positivas", f"{positivos} 👍", f"{porc_positivos:.1f}%")
    col3.metric("Opiniones Negativas", f"{negativos} 👎", f"{porc_negativos:.1f}%")

    st.markdown("---")

    st.subheader("Última Opinión Recibida")
    ultima_opinion = df_feedback.iloc[0]
    texto_mostrar = ultima_opinion['original_text'] if pd.notna(ultima_opinion['original_text']) else ultima_opinion['transcribed_text']
    st.info(f"**Usuario:** `{ultima_opinion['user_id']}` | **Sentimiento:** `{ultima_opinion['sentiment']}`")
    st.markdown(f"> _{texto_mostrar}_")


# --- Pestaña 2: Visualizaciones ---
with tab2:
    st.header("📊 Visualizaciones Detalladas")
    
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        # Gráfico de Pastel
        sentiment_counts = df_feedback['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['sentiment', 'count']
        fig_pie = px.pie(sentiment_counts, 
                     names='sentiment', 
                     values='count', 
                     title='Distribución de Sentimientos',
                     color='sentiment',
                     color_discrete_map={'Positivo':'#2ECC71', 'Negativo':'#E74C3C', 'Neutral':'#3498DB'},
                     hole=0.3) # Gráfico de dona para un look más moderno
        fig_pie.update_layout(legend_title_text='Sentimiento')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_graf2:
        # Gráfico de Barras de Feedback por Día
        df_feedback['fecha'] = df_feedback['created_at'].dt.date
        feedback_por_dia = df_feedback['fecha'].value_counts().sort_index().reset_index()
        feedback_por_dia.columns = ['fecha', 'cantidad']
        fig_bar = px.bar(feedback_por_dia, 
                      x='fecha', 
                      y='cantidad',
                      title='Volumen de Opiniones por Día',
                      labels={'fecha': 'Fecha', 'cantidad': 'Nº de Opiniones'})
        st.plotly_chart(fig_bar, use_container_width=True)

# --- Pestaña 3: Quejas y Sugerencias ---
with tab3:
    st.header("📝 Quejas y Sugerencias (Análisis por IA)")
    df_negativos = df_feedback[df_feedback['sentiment'] == 'Negativo'].copy()

    if not df_negativos.empty and 'summary' in df_negativos.columns and not df_negativos['summary'].dropna().empty:
        st.info("A continuación se muestran los resúmenes de las quejas más comunes, generados automáticamente por Gemini.")
        
        for index, row in df_negativos.dropna(subset=['summary']).iterrows():
            with st.expander(f"🗣️ **{row['summary']}**"):
                texto_original = row['original_text'] if pd.notna(row['original_text']) else row['transcribed_text']
                st.write(f"**Opinión Original del Usuario `{row['user_id']}`:**")
                st.write(f"> _{texto_original}_")
    else:
        st.success("¡Buenas noticias! No se han encontrado resúmenes de quejas generados por la IA.")


# --- Pestaña 4: Datos Crudos ---
with tab4:
    st.header("🗃️ Tabla de Datos Crudos")
    st.info("Aquí puedes ver y buscar en todas las opiniones recibidas.")
    
    columnas_visibles = [
        'created_at', 
        'user_id', 
        'message_type', 
        'sentiment', 
        'original_text', 
        'transcribed_text',
        'summary'
    ]

    columnas_existentes = [col for col in columnas_visibles if col in df_feedback.columns]
    
    st.dataframe(df_feedback[columnas_existentes])


# --- Sidebar ---
st.sidebar.header("Opciones")
if st.sidebar.button('Forzar Actualización de Datos'):
    st.cache_data.clear() # Limpia la caché para forzar la recarga
    st.rerun() # Vuelve a ejecutar el script

st.sidebar.markdown("---")
st.sidebar.info(
    "Esta aplicación recopila feedback de usuarios vía WhatsApp y lo analiza "
    "usando la API de Gemini de Google para extraer insights de forma automática."
)