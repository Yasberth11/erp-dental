import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import time

# ==========================================
# 1. CONFIGURACIÓN VISUAL Y CSS (DISEÑO ROYAL)
# ==========================================
st.set_page_config(
    page_title="Royal Dental Manager",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed" # Colapsado al inicio para login limpio
)

# Colores: Azul #002B5B, Dorado #D4AF37, Blanco #FFFFFF, Gris Claro #F4F6F6
def cargar_estilo_royal():
    st.markdown("""
        <style>
        /* IMPORTANTE: Estilos para la pantalla de LOGIN (Fondo Azul) */
        .stApp {
            background-color: #F4F6F6; /* Gris muy claro para la app interna */
        }
        
        /* Estilos personalizados para contenedores */
        .royal-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #D4AF37;
            margin-bottom: 20px;
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #002B5B !important;
            font-family: 'Helvetica Neue', sans-serif;
        }
        
        /* Botones Dorados */
        .stButton>button {
            background-color: #D4AF37;
            color: #002B5B;
            border: none;
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #B5952F;
            color: white;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #002B5B;
        }
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS (DB)
# ==========================================
@st.cache_resource
def get_database_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client.open("ERP_DENTAL_DB")

try:
    db = get_database_connection()
    sheet_pacientes = db.worksheet("pacientes")
    sheet_citas = db.worksheet("citas")
    sheet_asistencia = db.worksheet("asistencia")
except Exception as e:
    st.error(f"❌ Error crítico de conexión: {e}")
    st.stop()

# ==========================================
# 3. SISTEMA DE LOGIN MEJORADO
# ==========================================
if 'perfil' not in st.session_state:
    st.session_state.perfil = None

def pantalla_login():
    # Truco de diseño: Usar columnas para centrar y fondo oscuro solo en esta sección
    # Nota: Streamlit no permite cambiar el fondo de body dinámicamente fácil, 
    # pero usaremos un contenedor visual fuerte.
    
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    
    with col_centro:
        # Contenedor estilo tarjeta flotante
        st.markdown("""
        <div style="background-color: #002B5B; padding: 40px; border-radius: 15px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
            <h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2>
            <p style="color: white;">Sistema de Gestión Integral v6.2</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.image("logo.png", use_container_width=True) # El logo se verá bien si tiene transparencia, si no, el contenedor azul ayuda.
        
        st.markdown("### 🔐 Seleccione Portal de Acceso")
        
        tipo_acceso = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        password = st.text_input("Clave de Acceso", type="password")
        
        if st.button("INGRESAR AL SISTEMA"):
            if tipo_acceso == "🏥 CONSULTORIO" and password == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"
                st.toast("✅ Acceso Correcto: Modo Operativo")
                time.sleep(1)
                st.rerun()
            elif tipo_acceso == "💼 ADMINISTRACIÓN" and password == "ROYALADMIN":
                st.session_state.perfil = "Administracion"
                st.toast("✅ Acceso Correcto: Modo Director")
                time.sleep(1)
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta o perfil no seleccionado.")

# ==========================================
# 4. FUNCIONES DE ASISTENCIA (LOGICA INTERNA)
# ==========================================
def registrar_entrada(doctor_nombre):
    try:
        data = sheet_asistencia.get_all_records()
        nuevo_id = len(data) + 1
        hoy = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        
        # id_registro, fecha, doctor, hora_entrada, hora_salida, horas_totales, pago_dia_validado
        row = [nuevo_id, hoy, doctor_nombre, hora, "", "", "Pendiente"]
        sheet_asistencia.append_row(row)
        return True, hora
    except Exception as e:
        return False, str(e)

def registrar_salida(doctor_nombre):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Buscar el último registro abierto de hoy para este doctor
        # Asumiendo que id_registro es único y secuencial
        registros_hoy = df[(df['fecha'] == hoy) & (df['doctor'] == doctor_nombre)]
        
        if registros_hoy.empty:
            return False, "No hay entrada registrada hoy."
            
        ultimo_registro = registros_hoy.iloc[-1]
        
        if ultimo_registro['hora_salida'] != "":
            return False, "Ya has registrado tu salida hoy."
            
        # Calcular horas
        hora_salida = datetime.now().strftime("%H:%M:%S")
        fmt = "%H:%M:%S"
        t_entrada = datetime.strptime(ultimo_registro['hora_entrada'], fmt)
        t_salida = datetime.strptime(hora_salida, fmt)
        horas = round((t_salida - t_entrada).total_seconds() / 3600, 2)
        
        # Actualizar celda (Busqueda por ID)
        cell = sheet_asistencia.find(str(ultimo_registro['id_registro']))
        row_idx = cell.row
        
        sheet_asistencia.update_cell(row_idx, 5, hora_salida) # Col E
        sheet_asistencia.update_cell(row_idx, 6, horas)       # Col F
        
        return True, f"{hora_salida} ({horas} hrs)"
        
    except Exception as e:
        return False, str(e)

# ==========================================
# 5. VISTA: CONSULTORIO (OPERATIVA)
# ==========================================
def vista_consultorio():
    st.sidebar.title("🏥 Menú Clínica")
    menu = st.sidebar.radio("Ir a:", ["Panel Principal", "Pacientes", "Agenda"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None
        st.rerun()

    if menu == "Panel Principal":
        st.title("Bienvenido al Consultorio Royal Dental")
        st.markdown("---")
        
        # PANEL DE ASISTENCIA RÁPIDA
        st.markdown("### ⏱️ Control de Asistencia del Día")
        
        col1, col2 = st.columns(2)
        
        # TARJETA DR. EMMANUEL
        with col1:
            st.markdown("""
            <div class="royal-card">
                <h3 style="text-align: center;">👨‍⚕️ Dr. Emmanuel</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Lógica visual simple para botones
            col_a, col_b = st.columns(2)
            if col_a.button("🟢 ENTRADA", key="ent_emma"):
                ok, msg = registrar_entrada("Dr. Emmanuel")
                if ok: st.success(f"Entrada: {msg}")
                else: st.error(msg)
                
            if col_b.button("🔴 SALIDA", key="sal_emma"):
                ok, msg = registrar_salida("Dr. Emmanuel")
                if ok: st.success(f"Salida: {msg}")
                else: st.warning(msg)

        # TARJETA DRA. MÓNICA
        with col2:
            st.markdown("""
            <div class="royal-card">
                <h3 style="text-align: center;">👩‍⚕️ Dra. Mónica</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col_c, col_d = st.columns(2)
            if col_c.button("🟢 ENTRADA", key="ent_moni"):
                ok, msg = registrar_entrada("Dra. Mónica")
                if ok: st.success(f"Entrada: {msg}")
                else: st.error(msg)
                
            if col_d.button("🔴 SALIDA", key="sal_moni"):
                ok, msg = registrar_salida("Dra. Mónica")
                if ok: st.success(f"Salida: {msg}")
                else: st.warning(msg)
        
        st.info("ℹ️ Recuerden marcar su entrada al llegar. El sistema registra la hora exacta para nómina.")

    elif menu == "Pacientes":
        st.header("🦷 Gestión de Pacientes")
        st.write("Aquí cargaremos el módulo de Alta de Pacientes optimizado.")
        # Aquí irá el código de Alta Pacientes

    elif menu == "Agenda":
        st.header("📅 Agenda del Día")
        # Aquí irá el código de Citas

# ==========================================
# 6. VISTA: ADMINISTRACIÓN (DIRECTOR)
# ==========================================
def vista_administracion():
    st.sidebar.markdown("## 💼 DIRECTOR")
    st.sidebar.markdown(f"Usuario: **Yasberth**")
    
    opcion = st.sidebar.radio("Gestión:", ["Dashboard Financiero", "Nómina", "Configuración"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None
        st.rerun()
        
    st.title(f"Panel Director - {opcion}")
    
    if opcion == "Dashboard Financiero":
        st.write("Gráficas de Ingresos vs Gastos (Pendiente de conectar a Plotly)")
        
    elif opcion == "Nómina":
        st.write("Cálculo de Pagos Quincenales")
        st.write("Aquí veremos las horas trabajadas del Dr. Emmanuel jaladas de la hoja 'asistencia'")
        
        # Previsualización rápida de asistencia
        st.subheader("Registro de Asistencia en Tiempo Real")
        try:
            df_asist = pd.DataFrame(sheet_asistencia.get_all_records())
            st.dataframe(df_asist)
        except:
            st.write("No hay datos aún.")

# ==========================================
# 7. MAIN
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        vista_administracion()
