import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import pytz
import re
import time

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO ROYAL
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')

def cargar_estilo_royal():
    st.markdown("""
        <style>
        .stApp { background-color: #F4F6F6; }
        .royal-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-bottom: 20px; }
        h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; transition: all 0.3s; }
        .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #002B5B; }
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label { color: white !important; }
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB (ROBUSTA)
# ==========================================
@st.cache_resource(ttl=5) # TTL muy bajo para ver cambios casi inmediatos
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
except Exception as e:
    st.error(f"❌ Error Crítico de Conexión: {e}")
    st.stop()

# ==========================================
# 3. HELPERS (FECHAS, VALIDACIONES)
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def validar_email(email):
    if not email: return True
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def formatear_telefono(numero):
    limpio = re.sub(r'\D', '', str(numero))
    if len(limpio) == 10:
        return f"{limpio[:2]}-{limpio[2:6]}-{limpio[6:]}"
    return numero

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("18:30", "%H:%M")
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales():
    return ["605 - Sueldos y Salarios", "612 - Personas Físicas con Actividades Empresariales", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]

def get_usos_cfdi():
    return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general"]

# ==========================================
# 4. LOGICA DE ASISTENCIA (RESTAURADA)
# ==========================================
def registrar_movimiento(doctor, tipo):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        if tipo == "Entrada":
            # Verificar si ya entró hoy y no ha salido
            if not df.empty:
                # Convertimos a string para asegurar compatibilidad
                df['fecha'] = df['fecha'].astype(str)
                df['doctor'] = df['doctor'].astype(str)
                
                check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
                if not check.empty: return False, "Ya tienes una sesión abierta."
            
            # Nuevo registro
            nuevo_id = int(time.time()) # ID único basado en tiempo
            row = [nuevo_id, hoy, doctor, hora_actual, "", "", "Pendiente"]
            sheet_asistencia.append_row(row)
            return True, f"Entrada registrada: {hora_actual}"
            
        elif tipo == "Salida":
            if df.empty: return False, "No hay registros."
            
            # Buscar sesión abierta
            df['fecha'] = df['fecha'].astype(str)
            df['doctor'] = df['doctor'].astype(str)
            
            # Buscar la fila donde fecha es hoy, doctor es X y hora_salida está vacía
            # NOTA: En pandas leer de gspread, celdas vacias pueden ser strings vacios
            check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
            
            if check.empty: return False, "No encontré entrada abierta hoy."
            
            # Obtener el ID del registro para actualizar en GSheets
            id_reg = check.iloc[-1]['id_registro'] # Asumiendo columna id_registro
            entrada = check.iloc[-1]['hora_entrada']
            
            # Calcular horas
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(entrada, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            # Encontrar la fila en Sheets (gspread es 1-based)
            cell = sheet_asistencia.find(str(id_reg))
            row_idx = cell.row
            
            sheet_asistencia.update_cell(row_idx, 5, hora_actual) # Col E Salida
            sheet_asistencia.update_cell(row_idx, 6, horas)       # Col F Horas
            
            return True, f"Salida: {hora_actual} ({horas}h)"
            
    except Exception as e: return False, str(e)

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 30px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div><br>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("Acceso Denegado")

# ==========================================
# 6. VISTA CONSULTORIO (PRINCIPAL)
# ==========================================
def vista_consultorio():
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Sesión: {get_fecha_mx()}")
    
    # Navegación Vertical Completa
    menu = st.sidebar.radio("Menú Principal", ["Agenda & Citas", "Gestión Pacientes", "Control Asistencia"], index=0)
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()

    # ------------------------------------
    # MÓDULO: AGENDA
    # ------------------------------------
    if menu == "Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        col_c1, col_c2 = st.columns([1, 2])
        
        fecha_ver = col_c1.date_input("Fecha", datetime.now(TZ_MX))
        
        with col_c1:
            with st.expander("➕ Agendar Cita", expanded=True):
                with st.form("form_cita", clear_on_submit=True):
                    # Cargar pacientes seguros
                    pacientes_raw = sheet_pacientes.get_all_records()
                    # CORRECCIÓN DE ID: Convertimos a string para evitar errores
                    lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    
                    pac_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    hora_sel = st.selectbox("Hora", generar_slots_tiempo())
                    motivo = st.text_input("Tratamiento/Motivo")
                    doc = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    urgencia = st.checkbox("🚨 Urgencia (Sobrecupo)")
                    
                    if st.form_submit_button("Confirmar Cita"):
                        if pac_sel != "Seleccionar...":
                            # Guardar
                            id_p = pac_sel.split(" - ")[0] # Esto ahora es string seguro
                            nom_p = pac_sel.split(" - ")[1]
                            row = [int(time.time()), str(fecha_ver), hora_sel, id_p, nom_p, "General", motivo, "", doc, 0, 0, 0, "No", 0, 0, "", "Pendiente", "No", ""]
                            sheet_citas.append_row(row)
                            st.success("Cita Agendada")
                            time.sleep(1); st.rerun()
                        else: st.error("Seleccione paciente")

        with col_c2:
            st.markdown(f"**Citas del día: {fecha_ver}**")
            # Visualización rápida
            citas_data = sheet_citas.get_all_records()
            df_c = pd.DataFrame(citas_data)
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str) # Forzar string
                df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                
                # Renderizar Slots
                for slot in generar_slots_tiempo():
                    ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)]
                    bg = "#E3F2FD"
                    info = "Disponible"
                    if not ocupado.empty:
                        bg = "#FFF3E0" # Naranja suave
                        info = ""
                        for idx, r in ocupado.iterrows():
                            info += f"🦷 {r['nombre_paciente']} ({r['tratamiento']}) - {r['doctor_atendio']}<br>"
                    
                    st.markdown(f"""
                    <div style="background-color: {bg}; border: 1px solid #ccc; border-radius: 5px; padding: 10px; margin-bottom: 5px;">
                        <b>{slot}</b>: {info}
                    </div>
                    """, unsafe_allow_html=True)

    # ------------------------------------
    # MÓDULO: PACIENTES (CORREGIDO ERROR ID)
    # ------------------------------------
    elif menu == "Gestión Pacientes":
        st.title("🦷 Expediente Clínico")
        
        tab_b, tab_n = st.tabs(["🔍 BUSCAR", "➕ NUEVO"])
        
        with tab_b:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw: st.warning("Sin pacientes")
            else:
                # CORRECCIÓN DE ID: Convertimos explícitamente a string (str)
                lista_busqueda = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    # CORRECCIÓN CRÍTICA: NO USAR INT()
                    id_sel_str = seleccion.split(" - ")[0] 
                    
                    # Buscar en la lista raw comparando strings
                    paciente_data = next((p for p in pacientes_raw if str(p['id_paciente']) == id_sel_str), None)
                    
                    if paciente_data:
                        st.markdown(f"### 👤 {paciente_data['nombre']} {paciente_data['apellido_paterno']}")
                        st.info(f"📞 {paciente_data['telefono']} | 📧 {paciente_data['email']}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Documentación Legal:**")
                            if st.button("📄 Historia Clínica"): st.success("Generando PDF HC...")
                            if st.button("📄 Consentimiento"): st.success("Generando PDF Consentimiento...")
                            if st.button("📄 Aviso Privacidad"): st.success("Generando PDF Privacidad...")
        
        with tab_n:
            with st.form("alta_form", clear_on_submit=True):
                st.subheader("Datos Personales")
                col1, col2 = st.columns(2)
                nombre = col1.text_input("Nombre(s)")
                paterno = col2.text_input("Apellido Paterno")
                materno = col1.text_input("Apellido Materno")
                nacimiento = col2.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1))
                
                tel = st.text_input("Teléfono (10 dígitos)")
                email = st.text_input("Email")
                
                st.subheader("Fiscal 2026")
                rfc = st.text_input("RFC")
                regimen = st.selectbox("Régimen", get_regimenes_fiscales())
                uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                cp = st.text_input("C.P.")
                
                if st.form_submit_button("Guardar Expediente"):
                    if nombre and paterno and len(tel) == 10:
                        # Generar ID
                        nuevo_id = len(pacientes_raw) + 1
                        fecha = get_fecha_mx()
                        tel_fmt = formatear_telefono(tel)
                        # id, fecha, nombre, pat, mat, tel, email, rfc, reg, uso, cp, alertas...
                        row = [nuevo_id, fecha, nombre, paterno, materno, tel_fmt, email, rfc, regimen, uso, cp, "", "", "Activo", ""]
                        sheet_pacientes.append_row(row)
                        st.success("Paciente Guardado Correctamente")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("Verifique Nombre, Apellido y Teléfono (10 dígitos)")

    # ------------------------------------
    # MÓDULO: ASISTENCIA (RESTAURADO)
    # ------------------------------------
    elif menu == "Control Asistencia":
        st.title("⏱️ Reloj Checador")
        st.markdown("Control de asistencia para pago de nómina.")
        
        col_dr, col_extra = st.columns([1, 2])
        
        with col_dr:
            st.markdown("""
            <div class="royal-card">
                <h3 style="text-align: center;">👨‍⚕️ Dr. Emmanuel</h3>
                <p style="text-align: center; color: #666;">Control de Horario</p>
            </div>
            """, unsafe_allow_html=True)
            
            c_ent, c_sal = st.columns(2)
            if c_ent.button("🟢 ENTRADA", key="btn_ent_em"):
                ok, msg = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(msg)
                else: st.warning(msg)
                
            if c_sal.button("🔴 SALIDA", key="btn_sal_em"):
                ok, msg = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(msg)
                else: st.warning(msg)
        
        with col_extra:
            st.info(f"📅 Fecha: {get_fecha_mx()}")
            st.info(f"🕒 Hora CDMX: {get_hora_mx()}")
            st.write("El sistema registra la hora exacta del servidor sincronizado con México.")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
