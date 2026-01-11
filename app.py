import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import pytz
import re
import time
import random
import string

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
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        
        /* Semáforos Financieros */
        .semaforo-verde { color: #155724; background-color: #D4EDDA; padding: 5px; border-radius: 5px; font-weight: bold; }
        .semaforo-rojo { color: #721c24; background-color: #F8D7DA; padding: 5px; border-radius: 5px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB
# ==========================================
@st.cache_resource(ttl=10)
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
    st.error(f"❌ Error Crítico de Conexión: {e}")
    st.stop()

# ==========================================
# 3. HELPERS & SANITIZACIÓN
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def limpiar_texto_mayus(texto):
    if not texto: return ""
    remplaces = {'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U', 'á':'A', 'é':'E', 'í':'I', 'ó':'O', 'ú':'U'}
    texto = texto.upper()
    for k, v in remplaces.items():
        texto = texto.replace(k, v)
    return texto

def limpiar_email(texto):
    if not texto: return ""
    return texto.lower().strip()

def calcular_edad_completa(nacimiento):
    hoy = datetime.now().date()
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    tipo = "MENOR DE EDAD" if edad < 18 else "ADULTO"
    return edad, tipo

def generar_id_unico(nombre, paterno, nacimiento):
    try:
        part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"
        part2 = nombre[0].upper()
        part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except:
        return f"P-{int(time.time())}"

def formatear_telefono(numero):
    return re.sub(r'\D', '', str(numero))

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
    return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]

# ==========================================
# 4. LOGICA ASISTENCIA
# ==========================================
def registrar_movimiento(doctor, tipo):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        if not df.empty:
            df['fecha'] = df['fecha'].astype(str)
            df['doctor'] = df['doctor'].astype(str)
            df['hora_salida'] = df['hora_salida'].astype(str)

        if tipo == "Entrada":
            if not df.empty:
                check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
                if not check.empty: return False, "Ya tienes una sesión abierta."
            
            nuevo_id = int(time.time())
            row = [nuevo_id, hoy, doctor, hora_actual, "", "", "Pendiente"]
            sheet_asistencia.append_row(row)
            return True, f"Entrada: {hora_actual}"
            
        elif tipo == "Salida":
            if df.empty: return False, "No hay registros."
            check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
            if check.empty: return False, "No encontré entrada abierta hoy."
            
            id_reg = check.iloc[-1]['id_registro']
            entrada = check.iloc[-1]['hora_entrada']
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(entrada, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            cell = sheet_asistencia.find(str(id_reg))
            sheet_asistencia.update_cell(cell.row, 5, hora_actual)
            sheet_asistencia.update_cell(cell.row, 6, horas)
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
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    
    menu = st.sidebar.radio("Menú", 
        ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Control Asistencia"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()

    # ------------------------------------
    # MÓDULO 1: AGENDA
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Calendario")
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            st.markdown("---")
            
            tab_reg, tab_new = st.tabs(["Paciente Registrado", "Prospecto/Nuevo"])
            
            with tab_reg:
                with st.form("cita_registrada"):
                    pacientes_raw = sheet_pacientes.get_all_records()
                    lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    
                    p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    h_sel = st.selectbox("Hora", generar_slots_tiempo())
                    m_sel = st.text_input("Motivo", "Revisión / Continuación")
                    d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Agendar Paciente"):
                        if p_sel != "Seleccionar...":
                            id_p = p_sel.split(" - ")[0]
                            nom_p = p_sel.split(" - ")[1]
                            # Columnas Financieras: 0 Pagado, 0 Saldo (Es solo cita operativa)
                            row = [int(time.time()), str(fecha_ver), h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "", 0, 0, ""]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita Agendada")
                            time.sleep(1); st.rerun()
                        else: st.error("Seleccione un paciente")

            with tab_new:
                st.caption("Pacientes sin expediente (Solo revisión).")
                with st.form("cita_prospecto"):
                    nombre_pros = st.text_input("Nombre Completo")
                    tel_pros = st.text_input("Teléfono", max_chars=10, help="Solo 10 números")
                    hora_pros = st.selectbox("Hora", generar_slots_tiempo())
                    motivo_pros = st.text_input("Motivo", "Revisión (Primera Vez)")
                    precio_pros = st.number_input("Costo Estimado", value=100.0, min_value=0.0)
                    doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Agendar Prospecto"):
                        if nombre_pros and len(tel_pros) == 10:
                            id_temp = f"PROSPECTO-{int(time.time())}"
                            nom_final = limpiar_texto_mayus(nombre_pros)
                            row = [
                                int(time.time()), str(fecha_ver), hora_pros, id_temp, nom_final, 
                                "Primera Vez", motivo_pros, "", doc_pros, 
                                precio_pros, precio_pros, 0, "No", 0, precio_pros, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}",
                                0, precio_pros, ""
                            ]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita de Prospecto Agendada")
                            time.sleep(1); st.rerun()
                        else: st.error("Nombre obligatorio y Teléfono debe ser de 10 dígitos")

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver}")
            try:
                citas_data = sheet_citas.get_all_records()
                df_c = pd.DataFrame(citas_data)
                
                if not df_c.empty:
                    df_c['fecha'] = df_c['fecha'].astype(str)
                    df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                    slots = generar_slots_tiempo()
                    for slot in slots:
                        ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)]
                        if ocupado.empty:
                            st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)
                        else:
                            for _, r in ocupado.iterrows():
                                es_prospecto = "PROSPECTO" in str(r['id_paciente'])
                                color = "#FF5722" if es_prospecto else "#002B5B"
                                st.markdown(f"""
                                <div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;">
                                    <b>{slot} | {r['nombre_paciente']}</b><br>
                                    <span style="color:#666; font-size:0.9em;">{r['tratamiento']} - {r['doctor_atendio']}</span>
                                </div>""", unsafe_allow_html=True)
            except: st.warning("Error leyendo agenda.")

    # ------------------------------------
    # MÓDULO 2: PACIENTES
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("🦷 Expediente Clínico")
        
        tab_b, tab_n = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)"])
        
        with tab_b:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw: st.warning("Sin pacientes")
            else:
                lista_busqueda = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    id_sel_str = seleccion.split(" - ")[0]
                    p_data = next((p for p in pacientes_raw if str(p['id_paciente']) == id_sel_str), None)
                    if p_data:
                        try:
                            f_obj = datetime.strptime(p_data['fecha_nacimiento'], "%Y-%m-%d").date()
                            edad, tipo_pac = calcular_edad_completa(f_obj)
                        except: edad, tipo_pac = "N/A", ""

                        st.markdown(f"""
                        <div class="royal-card">
                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>
                            <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span>
                            <br><br><b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}
                            <br><b>RFC:</b> {p_data['rfc']}
                        </div>""", unsafe_allow_html=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            with st.form("alta_paciente_v16", clear_on_submit=True):
                st.info("Los nombres se guardarán en MAYÚSCULAS automáticamente.")
                c_nom, c_pat, c_mat = st.columns(3)
                nombre = c_nom.text_input("Nombre(s)")
                paterno = c_pat.text_input("Apellido Paterno")
                materno = c_mat.text_input("Apellido Materno")
                
                c_nac, c_tel, c_mail = st.columns(3)
                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
                tel = c_tel.text_input("Teléfono (10 dígitos)", max_chars=10)
                email = c_mail.text_input("Email")
                
                st.markdown("---")
                requiere_factura = st.checkbox("¿Requiere Factura? (Habilitar campos fiscales)")
                st.caption("Llenar datos fiscales SOLO si marcó la casilla anterior:")
                c_f1, c_f2 = st.columns(2)
                rfc = c_f1.text_input("RFC")
                cp = c_f2.text_input("C.P.")
                regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                
                if
