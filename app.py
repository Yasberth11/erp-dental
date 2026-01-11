import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import plotly.express as px
import time

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO ROYAL
# ==========================================
st.set_page_config(
    page_title="Royal Dental Manager",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores Corporativos: Azul #002B5B, Dorado #D4AF37, Blanco #FFFFFF
def cargar_estilo_royal():
    st.markdown("""
        <style>
        /* Fondo general y fuentes */
        .stApp {
            background-color: #F8F9FA;
        }
        
        /* Sidebar Personalizado */
        section[data-testid="stSidebar"] {
            background-color: #002B5B;
        }
        section[data-testid="stSidebar"] h1, h2, h3, label, .stMarkdown {
            color: #FFFFFF !important;
        }
        
        /* Botones Principales (Dorado) */
        .stButton>button {
            background-color: #D4AF37;
            color: #002B5B;
            border-radius: 8px;
            border: none;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #B5952F;
            color: #FFFFFF;
        }

        /* Títulos */
        h1, h2, h3 {
            color: #002B5B;
            font-family: 'Helvetica', sans-serif;
        }
        
        /* Métricas */
        div[data-testid="stMetricValue"] {
            color: #D4AF37;
        }
        
        /* Mensajes de éxito/error */
        .stSuccess {
            background-color: #D4EDDA;
            color: #155724;
        }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN A GOOGLE SHEETS (DB INAMOVIBLE)
# ==========================================
@st.cache_resource
def get_database_connection():
    # Asegúrate de configurar tus secrets en Streamlit Cloud
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client.open("ERP_DENTAL_DB") # Nombre exacto del archivo

try:
    db = get_database_connection()
    # Mapeo de hojas existentes (NO CAMBIAR NOMBRES DE COLUMNAS)
    sheet_pacientes = db.worksheet("pacientes")
    sheet_citas = db.worksheet("citas")
    sheet_servicios = db.worksheet("servicios")
    # Verificar si existe asistencia, si no, crearla o conectarla
    try:
        sheet_asistencia = db.worksheet("asistencia")
    except:
        # Si no existe, podrías crearla manualmente en Sheets primero con las columnas:
        # id_registro, fecha, doctor, hora_entrada, hora_salida, horas_totales, pago_dia_validado
        st.error("⚠️ La hoja 'asistencia' no existe en el Google Sheet. Por favor créala.")
        st.stop()
except Exception as e:
    st.error(f"Error de conexión con la Base de Datos: {e}")
    st.stop()

# ==========================================
# 3. LÓGICA DE SESIÓN Y LOGIN
# ==========================================
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

def login():
    st.markdown("## 🔐 Acceso Royal Dental")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("logo.png", width=150) # Asegúrate de que logo.png esté en la raíz
    with col2:
        usuario = st.selectbox("Seleccione Usuario", ["Director Yasberth", "Dr. Emmanuel", "Dra. Mónica"])
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar"):
            # Lógica simple de contraseñas (En prod usar hash)
            if usuario == "Director Yasberth" and password == "ROYALADMIN":
                st.session_state.usuario = usuario
                st.session_state.rol = "Director"
                st.rerun()
            elif usuario == "Dr. Emmanuel" and password == "DOC123":
                st.session_state.usuario = usuario
                st.session_state.rol = "Doctor"
                st.rerun()
            elif usuario == "Dra. Mónica" and password == "DRAMONI":
                st.session_state.usuario = usuario
                st.session_state.rol = "Operativo"
                st.rerun()
            else:
                st.error("Contraseña incorrecta")

# ==========================================
# 4. MÓDULO DE ASISTENCIA (SIDEBAR)
# ==========================================
def sidebar_asistencia():
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👨‍⚕️ Hola, {st.session_state.usuario}")
    
    # Solo mostrar reloj checador a Doctores y Director (modo prueba)
    if st.session_state.rol in ["Doctor", "Director"]:
        st.sidebar.subheader("⏱️ Reloj Checador")
        
        # Lógica para determinar estado actual (Entró o Salió)
        # Traemos los últimos registros de asistencia
        data_asistencia = sheet_asistencia.get_all_records()
        df_asistencia = pd.DataFrame(data_asistencia)
        
        hoy = datetime.now().strftime("%Y-%m-%d")
        usuario_actual = st.session_state.usuario
        
        # Filtrar registros de hoy para este usuario
        estado_actual = "Fuera"
        ultimo_id = 0
        
        if not df_asistencia.empty:
            registros_hoy = df_asistencia[
                (df_asistencia['fecha'] == hoy) & 
                (df_asistencia['doctor'] == usuario_actual)
            ]
            if not registros_hoy.empty:
                ultimo_registro = registros_hoy.iloc[-1]
                if ultimo_registro['hora_salida'] == "" or pd.isna(ultimo_registro['hora_salida']):
                    estado_actual = "Trabajando"
                    ultimo_id = ultimo_registro['id_registro']
        
        if estado_actual == "Fuera":
            if st.sidebar.button("🟢 MARCAR ENTRADA"):
                nuevo_id = len(data_asistencia) + 1
                hora_entrada = datetime.now().strftime("%H:%M:%S")
                # id_registro, fecha, doctor, hora_entrada, hora_salida, horas_totales, pago_dia_validado
                nuevo_registro = [nuevo_id, hoy, usuario_actual, hora_entrada, "", "", "Pendiente"]
                sheet_asistencia.append_row(nuevo_registro)
                st.sidebar.success(f"Entrada: {hora_entrada}")
                time.sleep(1)
                st.rerun()
        else:
            st.sidebar.info(f"En turno desde: {registros_hoy.iloc[-1]['hora_entrada']}")
            if st.sidebar.button("🔴 MARCAR SALIDA"):
                hora_salida = datetime.now().strftime("%H:%M:%S")
                
                # Calcular horas totales
                fmt = "%H:%M:%S"
                t_entrada = datetime.strptime(registros_hoy.iloc[-1]['hora_entrada'], fmt)
                t_salida = datetime.strptime(hora_salida, fmt)
                duracion = t_salida - t_entrada
                horas_totales = round(duracion.total_seconds() / 3600, 2)
                
                # Actualizar en Google Sheets (Buscar la fila correcta)
                # OJO: gspread usa index 1-based. 
                # Buscamos la fila basándonos en el ID.
                cell = sheet_asistencia.find(str(ultimo_id))
                row_idx = cell.row
                
                # Columnas: E=5 (salida), F=6 (horas)
                sheet_asistencia.update_cell(row_idx, 5, hora_salida)
                sheet_asistencia.update_cell(row_idx, 6, horas_totales)
                
                st.sidebar.success(f"Salida: {hora_salida}. Total: {horas_totales} hrs")
                time.sleep(1)
                st.rerun()

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.usuario = None
        st.session_state.rol = None
        st.rerun()

# ==========================================
# 5. ESTRUCTURA PRINCIPAL (MENÚ)
# ==========================================
def main_app():
    sidebar_asistencia()
    
    # Menú de Navegación según Rol
    menu_options = ["🏠 Inicio", "🦷 Pacientes", "📅 Agenda"]
    
    if st.session_state.rol == "Director":
        menu_options.extend(["💰 Finanzas", "📊 Director Dashboard", "⚖️ Legal"])
    
    # Usamos radio buttons estilizados en el sidebar para navegación
    selection = st.sidebar.radio("Navegación", menu_options)
    
    st.title(f"Royal Dental Manager - {selection}")
    st.markdown("---")

    # --- RUTEO DE VISTAS ---
    if selection == "🏠 Inicio":
        st.info(f"Bienvenido al sistema v6.2. Panel de control de {st.session_state.usuario}.")
        # Aquí pondremos tarjetas resumen más adelante
        
    elif selection == "🦷 Pacientes":
        st.write("Módulo de Pacientes (Aquí iría tu código existente de Alta de Pacientes)")
        # TODO: Pegar aquí tu lógica de AltaPacientes existente
        
    elif selection == "📅 Agenda":
        st.write("Agenda del Consultorio")
        # TODO: Pegar aquí tu lógica de Citas/Agenda
        
    elif selection == "💰 Finanzas":
        st.warning("Zona Restringida: Finanzas y Nómina")
        # TODO: Aquí desarrollaremos el cálculo de nómina del Dr. Emmanuel
        
    elif selection == "⚖️ Legal":
        st.write("Generación de Documentos Legales")
        if st.button("📄 Generar Aviso de Privacidad"):
            st.success("Generando PDF... (Lógica pendiente de implementar)")

# ==========================================
# 6. EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    if st.session_state.usuario is None:
        login()
    else:
        main_app()
