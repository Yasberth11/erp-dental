import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import pytz # Para la hora de México
from streamlit_drawable_canvas import st_canvas # Para la firma
import time

# ==========================================
# 1. CONFIGURACIÓN VISUAL Y CSS (DISEÑO ROYAL)
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="collapsed")

# Zona Horaria México
TZ_MX = pytz.timezone('America/Mexico_City')

def cargar_estilo_royal():
    st.markdown("""
        <style>
        .stApp { background-color: #F4F6F6; }
        .royal-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-bottom: 20px; }
        h1, h2, h3 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; }
        .stButton>button:hover { background-color: #B5952F; color: white; }
        section[data-testid="stSidebar"] { background-color: #002B5B; }
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span { color: white !important; }
        /* Ajuste para inputs */
        .stTextInput>div>div>input { border-radius: 5px; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource
def get_database_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client.open("ERP_DENTAL_DB")

try:
    db = get_database_connection()
    sheet_pacientes = db.worksheet("pacientes")
    sheet_citas = db.worksheet("citas")
    sheet_asistencia = db.worksheet("asistencia")
    sheet_servicios = db.worksheet("servicios")
except Exception as e:
    st.error(f"❌ Error de conexión DB: {e}")
    st.stop()

# ==========================================
# 3. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 40px; border-radius: 15px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3);"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div>""", unsafe_allow_html=True)
        st.markdown("### 🔐 Acceso Seguro")
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Clave", type="password")
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"
                st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"
                st.rerun()
            else: st.error("Clave incorrecta")

# ==========================================
# 4. FUNCIONES OPERATIVAS (Asistencia, Pacientes)
# ==========================================
def get_hora_mx():
    return datetime.now(TZ_MX).strftime("%H:%M:%S")

def get_fecha_mx():
    return datetime.now(TZ_MX).strftime("%Y-%m-%d")

def registrar_asistencia(doctor, tipo):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        if tipo == "Entrada":
            # Verificar si ya entró hoy
            if not df.empty:
                check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
                if not check.empty: return False, "Ya tienes una sesión abierta hoy."
            
            row = [len(data)+1, hoy, doctor, hora_actual, "", "", "Pendiente"]
            sheet_asistencia.append_row(row)
            return True, f"Entrada: {hora_actual}"
            
        elif tipo == "Salida":
            # Buscar sesión abierta
            if df.empty: return False, "No hay registros."
            check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
            if check.empty: return False, "No has registrado entrada hoy o ya saliste."
            
            idx_row = check.index[-1] + 2 # +2 por header y 1-based index de gspread
            
            # Calcular horas
            entrada = check.iloc[-1]['hora_entrada']
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(entrada, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            sheet_asistencia.update_cell(idx_row, 5, hora_actual)
            sheet_asistencia.update_cell(idx_row, 6, horas)
            return True, f"Salida: {hora_actual} ({horas}h)"
    except Exception as e: return False, str(e)

# ==========================================
# 5. VISTAS
# ==========================================

def vista_consultorio():
    st.sidebar.title("🏥 Menú Clínica")
    menu = st.sidebar.radio("Navegación", ["Panel Principal", "Pacientes", "Agenda"])
    if st.sidebar.button("Salir"): st.session_state.perfil = None; st.rerun()

    if menu == "Panel Principal":
        st.title("Panel Operativo Royal Dental")
        st.markdown("---")
        
        # SOLO DR. EMMANUEL EN ASISTENCIA
        st.markdown("### ⏱️ Control de Asistencia: Dr. Emmanuel")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("""<div class="royal-card"><h3 style="text-align: center;">👨‍⚕️ Dr. Emmanuel</h3></div>""", unsafe_allow_html=True)
            c_a, c_b = st.columns(2)
            if c_a.button("🟢 ENTRADA"):
                ok, msg = registrar_asistencia("Dr. Emmanuel", "Entrada")
                if ok: st.success(msg)
                else: st.warning(msg)
            if c_b.button("🔴 SALIDA"):
                ok, msg = registrar_asistencia("Dr. Emmanuel", "Salida")
                if ok: st.success(msg)
                else: st.warning(msg)
        
        with col2:
            st.info(f"📅 Fecha actual: {get_fecha_mx()} | 🕒 Hora CDMX: {get_hora_mx()}")
            st.write("El sistema registra la hora exacta de Ciudad de México para fines de nómina.")

    elif menu == "Pacientes":
        st.header("🦷 Gestión de Pacientes")
        
        # 1. BUSCADOR INTELIGENTE
        busqueda = st.text_input("🔍 Buscar Paciente (Nombre o Apellido)", placeholder="Escribe para buscar...")
        
        paciente_encontrado = False
        df_pacientes = pd.DataFrame(sheet_pacientes.get_all_records())
        
        if busqueda:
            if not df_pacientes.empty:
                # Filtrar
                mask = df_pacientes.apply(lambda row: busqueda.lower() in str(row['nombre']).lower() or busqueda.lower() in str(row['apellido_paterno']).lower(), axis=1)
                resultados = df_pacientes[mask]
                
                if not resultados.empty:
                    st.success(f"Se encontraron {len(resultados)} coincidencias.")
                    st.dataframe(resultados[['id_paciente', 'nombre', 'apellido_paterno', 'telefono']])
                    paciente_encontrado = True
                    # Aquí podrías poner un selectbox para elegir uno y ver detalles
                else:
                    st.warning("No se encontró el paciente.")
        
        st.markdown("---")
        
        # 2. ALTA DE PACIENTE (Solo si se quiere registrar uno nuevo)
        if not paciente_encontrado or st.checkbox("➕ Registrar Nuevo Paciente"):
            with st.expander("📝 Formulario de Nuevo Expediente", expanded=True):
                with st.form("form_alta"):
                    col_p1, col_p2 = st.columns(2)
                    nombre = col_p1.text_input("Nombre(s)")
                    ap_pat = col_p2.text_input("Apellido Paterno")
                    ap_mat = col_p1.text_input("Apellido Materno")
                    telefono = col_p2.text_input("Teléfono (10 dígitos)")
                    email = col_p1.text_input("Email")
                    f_nac = col_p2.date_input("Fecha de Nacimiento", min_value=datetime(1920, 1, 1), max_value=datetime.now())
                    
                    st.subheader("Datos Fiscales 2026")
                    rfc = st.text_input("RFC")
                    regimen = st.selectbox("Régimen Fiscal", ["Sueldos y Salarios", "Persona Física con Actividad Empresarial", "Sin Obligaciones Fiscales", "RESICO"])
                    
                    st.subheader("Antecedentes Médicos (Alertas)")
                    alertas = st.text_area("Alergias / Enfermedades Crónicas / Medicamentos")
                    
                    # VALIDACIÓN DE MENOR DE EDAD PARA CONSENTIMIENTO
                    es_menor = st.checkbox("El paciente es menor de edad")
                    tutor = ""
                    if es_menor:
                        tutor = st.text_input("Nombre del Padre/Madre o Tutor Legal")
                    
                    st.subheader("✍️ Firma de Consentimiento y Privacidad")
                    st.write("Firma usando el mouse o dedo:")
                    # CANVAS PARA FIRMA
                    firma_data = st_canvas(
                        stroke_width=2,
                        stroke_color="#000000",
                        background_color="#FFFFFF",
                        height=150,
                        width=400,
                        drawing_mode="freedraw",
                        key="canvas_firma"
                    )
                    
                    submitted = st.form_submit_button("💾 Guardar Expediente")
                    
                    if submitted:
                        if nombre and ap_pat and telefono:
                            # Validar duplicados exactos antes de guardar
                            if not df_pacientes.empty:
                                existe = df_pacientes[
                                    (df_pacientes['nombre'].str.lower() == nombre.lower()) & 
                                    (df_pacientes['apellido_paterno'].str.lower() == ap_pat.lower())
                                ]
                                if not existe.empty:
                                    st.error("⚠️ Error: Ya existe un paciente con este nombre y apellido.")
                                    st.stop()
                            
                            # Guardar
                            nuevo_id = len(df_pacientes) + 1
                            fecha_reg = get_fecha_mx()
                            # id, fecha, nombre, ap_pat, ap_mat, tel, email, rfc, reg, uso, cp, alertas, link, estado, ultima
                            # Ajustar columnas a tu DB real
                            row_paciente = [
                                nuevo_id, fecha_reg, nombre, ap_pat, ap_mat, telefono, email, rfc, regimen, 
                                "D01", "", alertas, "", "Activo", ""
                            ]
                            sheet_pacientes.append_row(row_paciente)
                            st.success(f"Paciente {nombre} {ap_pat} registrado correctamente.")
                            
                            # AQUÍ GENERARÍAMOS LOS PDFS (Lógica pendiente para no saturar este bloque)
                            st.info("Generando PDFs de Historia Clínica y Privacidad... (Simulado)")
                        else:
                            st.error("Faltan datos obligatorios (Nombre, Apellido, Teléfono)")

    elif menu == "Agenda":
        st.header("📅 Agenda y Citas")
        
        # SELECTOR DE DIENTES (ODONTOGRAMA LÓGICO)
        st.subheader("Selección de Tratamiento")
        
        col_d1, col_d2 = st.columns(2)
        tipo_paciente = col_d1.radio("Tipo de Dentición", ["Adulto (Permanente)", "Niño (Decidua/Temporal)"])
        
        diente_selec = None
        
        if tipo_paciente == "Adulto (Permanente)":
            cuadrante = col_d2.selectbox("Cuadrante", ["1 (Superior Derecho)", "2 (Superior Izquierdo)", "3 (Inferior Izquierdo)", "4 (Inferior Derecho)"])
            diente_num = st.selectbox("Diente", [1,2,3,4,5,6,7,8])
            # Construir número ISO
            base = int(cuadrante[0]) * 10
            diente_final = base + diente_num
            st.info(f"Diente Seleccionado: {diente_final}")
            
        else: # Niño
            cuadrante = col_d2.selectbox("Cuadrante", ["5 (Superior Derecho)", "6 (Superior Izquierdo)", "7 (Inferior Izquierdo)", "8 (Inferior Derecho)"])
            diente_num = st.selectbox("Diente", [1,2,3,4,5])
            base = int(cuadrante[0]) * 10
            diente_final = base + diente_num
            st.info(f"Diente Seleccionado (Niño): {diente_final}")

        st.write("Formulario de cita pendiente de conectar con botón guardar...")


def vista_administracion():
    st.title("Panel Director")
    st.write("Modo Administración Activo")
    if st.button("Salir"): st.session_state.perfil = None; st.rerun()

# ==========================================
# 6. MAIN
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        vista_administracion()
