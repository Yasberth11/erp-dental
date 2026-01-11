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
        /* Inputs y Selects Mejorados */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        /* Mensajes */
        .stSuccess { background-color: #D4EDDA; color: #155724; border-left: 5px solid #28a745; }
        .stInfo { background-color: #D1ECF1; color: #0C5460; border-left: 5px solid #17a2b8; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB (ROBUSTA)
# ==========================================
@st.cache_resource(ttl=5)
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
# 3. HELPERS (LÓGICA EXPERTA)
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def calcular_edad(nacimiento):
    hoy = datetime.now().date()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))

def generar_id_unico(nombre, paterno, nacimiento):
    # Formato: 3 letras apellido + 1 letra nombre + Año + 3 random (ej. PER-J-1990-A7X)
    try:
        part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"
        part2 = nombre[0].upper()
        part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except:
        # Fallback simple si fallan los datos
        return f"P-{int(time.time())}"

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
# 4. LOGICA DE ASISTENCIA
# ==========================================
def registrar_movimiento(doctor, tipo):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        # Convertir a string para evitar errores de tipo
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
            return True, f"Entrada registrada: {hora_actual}"
            
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
    st.sidebar.caption(f"Sesión: {get_fecha_mx()}")
    
    # NUEVO ORDEN DE NAVEGACIÓN
    menu = st.sidebar.radio("Navegación", 
        ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Control Asistencia"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()

    # ------------------------------------
    # MÓDULO 1: AGENDA (Visualizador)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        fecha_ver = st.date_input("Consultar Fecha", datetime.now(TZ_MX))
        
        citas_data = sheet_citas.get_all_records()
        df_c = pd.DataFrame(citas_data)
        
        st.markdown(f"**Programación del día: {fecha_ver}**")
        
        col_ag1, col_ag2 = st.columns([1,3])
        with col_ag1:
            st.info("Para agendar tratamientos complejos, ve al módulo '3. Planes de Tratamiento'.")
            
        with col_ag2:
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str)
                df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                
                # Grilla de Tiempo
                slots = generar_slots_tiempo()
                grid_html = ""
                for slot in slots:
                    ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)]
                    bg = "#E3F2FD"
                    content = f"<span style='color:#999'>{slot} - Disponible</span>"
                    
                    if not ocupado.empty:
                        bg = "#FFF3E0"
                        citas_str = ""
                        for _, r in ocupado.iterrows():
                             citas_str += f"🦷 <b>{r['nombre_paciente']}</b>: {r['tratamiento']} ({r['doctor_atendio']})<br>"
                        content = f"<div style='color:#002B5B'>{slot}</div>{citas_str}"
                    
                    st.markdown(f"""
                    <div style="background-color:{bg}; padding:10px; border-bottom:1px solid #ccc; margin-bottom:4px; border-radius:4px;">
                        {content}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Base de datos de citas vacía.")

    # ------------------------------------
    # MÓDULO 2: PACIENTES (Mejorado V11)
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("🦷 Expediente Clínico")
        
        tab_b, tab_n = st.tabs(["🔍 BUSCAR", "➕ NUEVO PACIENTE (ALTA)"])
        
        with tab_b:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw: st.warning("Sin pacientes")
            else:
                lista_busqueda = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    id_sel_str = seleccion.split(" - ")[0]
                    paciente_data = next((p for p in pacientes_raw if str(p['id_paciente']) == id_sel_str), None)
                    
                    if paciente_data:
                        st.markdown(f"""
                        <div class="royal-card">
                            <h3>👤 {paciente_data['nombre']} {paciente_data['apellido_paterno']}</h3>
                            <b>ID Único:</b> {paciente_data['id_paciente']}<br>
                            <b>Tel:</b> {paciente_data['telefono']} | <b>Email:</b> {paciente_data['email']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_legal1, col_legal2 = st.columns(2)
                        with col_legal1:
                            st.caption("Documentación Legal")
                            if st.button("📄 Historia Clínica (PDF)"): st.success("PDF generado.")
                            if st.button("📄 Consentimiento (PDF)"): st.success("PDF generado.")
        
        with tab_n:
            st.markdown("#### Formulario de Alta con ID Inteligente")
            # Usamos form para evitar recargas constantes que rompen el TAB
            with st.form("alta_form_v11", clear_on_submit=True):
                st.subheader("1. Datos Personales")
                col_a, col_b = st.columns(2)
                nombre = col_a.text_input("Nombre(s)")
                paterno = col_b.text_input("Apellido Paterno")
                materno = col_a.text_input("Apellido Materno")
                
                # Cálculo de Edad
                col_nac1, col_nac2 = st.columns([2,1])
                nacimiento = col_nac1.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
                
                # Esto se calculará al enviar, visualmente en Streamlit forms es dificil actualizar en tiempo real sin recargar
                # pero lo mostraremos al guardar.
                
                tel = st.text_input("Teléfono (10 dígitos)")
                email = st.text_input("Email")
                
                st.subheader("2. Fiscal")
                rfc = st.text_input("RFC")
                regimen = st.selectbox("Régimen", get_regimenes_fiscales())
                
                submitted = st.form_submit_button("💾 GENERAR ID Y GUARDAR")
                
                if submitted:
                    if nombre and paterno and len(tel)==10:
                        # 1. Calcular Edad
                        edad = calcular_edad(nacimiento)
                        
                        # 2. Generar ID Único Alfanumérico
                        nuevo_id = generar_id_unico(nombre, paterno, nacimiento)
                        
                        fecha_reg = get_fecha_mx()
                        tel_fmt = formatear_telefono(tel)
                        
                        # Guardar
                        row = [nuevo_id, fecha_reg, nombre, paterno, materno, tel_fmt, email, rfc, regimen, "D01", "", "", "", "Activo", ""]
                        try:
                            sheet_pacientes.append_row(row)
                            st.success(f"✅ Paciente registrado con Éxito.")
                            st.info(f"🆔 ID Generado: {nuevo_id}")
                            st.info(f"🎂 Edad Calculada: {edad} años")
                            time.sleep(3) # Tiempo para leer antes de recargar
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error DB: {e}")
                    else:
                        st.error("Faltan datos obligatorios o teléfono incorrecto.")

    # ------------------------------------
    # MÓDULO 3: PLANES DE TRATAMIENTO (NUEVO)
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Gestión de Tratamientos y Cobranza")
        
        # 1. Seleccionar Paciente
        pacientes_raw = sheet_pacientes.get_all_records()
        if not pacientes_raw:
            st.warning("Registre pacientes primero.")
        else:
            lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
            seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
            
            if seleccion_pac != "Buscar...":
                st.markdown("---")
                id_pac = seleccion_pac.split(" - ")[0]
                nom_pac = seleccion_pac.split(" - ")[1]
                
                col_izq, col_der = st.columns([1, 1])
                
                with col_izq:
                    st.subheader("🛠️ Detalles del Tratamiento")
                    
                    with st.form("form_tratamiento"):
                        # Tratamiento Múltiple
                        tratamiento = st.text_input("Nombre del Tratamiento (Ej. Resina, Endodoncia)")
                        
                        # Diente (Selector inteligente)
                        c_d1, c_d2 = st.columns(2)
                        tipo_dent = c_d1.selectbox("Tipo Dentición", ["Permanente", "Temporal"])
                        
                        # Lógica simplificada de dientes para no saturar
                        diente = c_d2.number_input("Número de Diente (ISO)", min_value=11, max_value=85, step=1)
                        
                        # Datos Financieros y Operativos
                        doctor = st.selectbox("Doctor Asignado", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        col_fin1, col_fin2 = st.columns(2)
                        precio = col_fin1.number_input("Precio Total ($)", min_value=0.0)
                        abono = col_fin2.number_input("Monto a Pagar Hoy ($)", min_value=0.0)
                        
                        metodo = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                        
                        # Workaround para "Número de Citas" (Guardar en Notas ya que la DB es inamovible en columnas)
                        num_citas = st.number_input("Número de Citas Estimadas", min_value=1, value=1)
                        notas = st.text_area("Notas / Detalles de Sesiones")
                        
                        # Calcular estatus
                        estatus_pago = "Pagado" if abono >= precio and precio > 0 else "Pendiente/Parcial"
                        
                        # Agendar automáticamente la PRIMERA cita
                        st.markdown("**Agendar Primera Sesión (Opcional)**")
                        fecha_cita = st.date_input("Fecha Cita", datetime.now(TZ_MX))
                        hora_cita = st.selectbox("Hora Cita", generar_slots_tiempo())
                        
                        btn_guardar_trat = st.form_submit_button("💾 REGISTRAR TRATAMIENTO Y PAGO")
                        
                        if btn_guardar_trat:
                            if tratamiento and precio > 0:
                                nuevo_id_cita = int(time.time()) # Usamos timestamp como ID único de tratamiento/transacción
                                
                                notas_finales = f"Citas Est: {num_citas} | {notas}"
                                
                                # id_cita, fecha, hora, id_paciente, nombre, categoria, tratamiento, diente, doc, precio_lista, precio_final, desc, lab, costo_lab, utilidad, metodo, estado, factura, notas
                                row = [
                                    nuevo_id_cita, str(fecha_cita), hora_cita, id_pac, nom_pac, 
                                    "Tratamiento", tratamiento, diente, doctor, 
                                    precio, abono, 0, "No", 0, (abono*0.6), metodo, estatus_pago, "No", notas_finales
                                ]
                                
                                sheet_citas.append_row(row)
                                st.success("✅ Tratamiento y Pago registrados correctamente.")
                                st.balloons()
                            else:
                                st.error("Ingrese nombre del tratamiento y precio.")

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        col1, col2 = st.columns([1,3])
        with col1:
            st.markdown("### 👨‍⚕️ Dr. Emmanuel")
            if st.button("Entrada Dr. E"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(m)
                else: st.warning(m)
            if st.button("Salida Dr. E"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(m)
                else: st.warning(m)
        with col2:
             st.info("Sistema operando en Tiempo Real CDMX.")

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
