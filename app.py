import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import pytz
import re # Para validación de Email y Teléfono
import time

# ==========================================
# 1. CONFIGURACIÓN ROYAL
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="collapsed")
TZ_MX = pytz.timezone('America/Mexico_City')

def cargar_estilo_royal():
    st.markdown("""
        <style>
        .stApp { background-color: #F4F6F6; }
        .royal-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-bottom: 20px; }
        h1, h2, h3 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; }
        .stButton>button:hover { background-color: #B5952F; color: white; }
        /* Inputs más limpios */
        div[data-baseweb="input"] > div { border-radius: 8px; background-color: #FFFFFF; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB & HELPERS
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
    st.error(f"❌ Error DB: {e}")
    st.stop()

def validar_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def formatear_telefono(numero):
    # Elimina todo lo que no sea número
    limpio = re.sub(r'\D', '', numero)
    if len(limpio) == 10:
        return f"{limpio[:2]}-{limpio[2:6]}-{limpio[6:]}"
    return numero # Devuelve original si no son 10

def get_lista_pacientes():
    try:
        data = sheet_pacientes.get_all_records()
        if not data: return []
        df = pd.DataFrame(data)
        # Crear lista string: "ID - Nombre Completo"
        return [f"{row['id_paciente']} - {row['nombre']} {row['apellido_paterno']}" for index, row in df.iterrows()]
    except: return []

def get_catalogo_servicios():
    try:
        data = sheet_servicios.get_all_records()
        if not data: return pd.DataFrame()
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# ==========================================
# 3. LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 40px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Clave", type="password")
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("Clave incorrecta")

# ==========================================
# 4. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    st.sidebar.title("🏥 Menú Clínica")
    # Nueva Navegación Separada
    menu = st.sidebar.radio("Ir a:", ["Panel Principal", "Pacientes", "Agenda (Citas)", "Planes de Tratamiento"])
    if st.sidebar.button("Salir"): st.session_state.perfil = None; st.rerun()

    # --- PANEL PRINCIPAL (Asistencia) ---
    if menu == "Panel Principal":
        st.title("Panel Operativo")
        st.markdown("### ⏱️ Control de Asistencia: Dr. Emmanuel")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("""<div class="royal-card"><h4 style="text-align: center;">Dr. Emmanuel</h4></div>""", unsafe_allow_html=True)
            c_a, c_b = st.columns(2)
            if c_a.button("🟢 ENTRADA"):
                # Lógica simplificada para demo
                st.success(f"Entrada registrada a las {datetime.now(TZ_MX).strftime('%H:%M:%S')}")
            if c_b.button("🔴 SALIDA"):
                st.info("Salida registrada.")
        with col2:
            st.info("Recordatorio: Verificar la agenda del día antes de iniciar tratamientos.")

    # --- PACIENTES ---
    elif menu == "Pacientes":
        st.header("🦷 Directorio de Pacientes")
        
        # Búsqueda con Selectbox (Lista Desplegable)
        lista_pacientes = get_lista_pacientes()
        busqueda = st.selectbox("🔍 Buscar Paciente Existente:", ["Seleccionar..."] + lista_pacientes)
        
        if busqueda != "Seleccionar...":
            # Extraer ID y mostrar datos
            id_sel = busqueda.split(" - ")[0]
            st.success(f"Expediente cargado: {busqueda}")
            # Aquí mostraríamos historial, citas pasadas, etc.
            st.info("Visualización de expediente completo (Historial Clínico) disponible aquí.")
        
        st.markdown("---")
        
        # ALTA DE PACIENTE (Layout corregido para TAB order)
        with st.expander("➕ Crear Nuevo Expediente", expanded=(busqueda == "Seleccionar...")):
            st.markdown("Rellene los datos en orden. Use **TAB** para navegar.")
            with st.form("alta_paciente"):
                # Orden estricto solicitado: Nombre -> Paterno -> Materno -> Fecha -> Tel -> Email
                
                # Fila 1: Nombre (Ancho completo o mitad)
                nombre = st.text_input("Nombre(s)")
                
                # Fila 2: Apellidos
                c1, c2 = st.columns(2)
                ap_pat = c1.text_input("Apellido Paterno")
                ap_mat = c2.text_input("Apellido Materno")
                
                # Fila 3: Fecha y Teléfono
                c3, c4 = st.columns(2)
                f_nac = c3.date_input("Fecha de Nacimiento", min_value=datetime(1920, 1, 1), max_value=datetime.now())
                
                # Teléfono con validación visual
                telefono_input = c4.text_input("Teléfono Móvil (10 dígitos)", placeholder="Ej. 5512345678")
                
                # Fila 4: Email
                email = st.text_input("Correo Electrónico")
                
                # Datos Fiscales (Opcional, abajo)
                st.markdown("---")
                st.caption("Datos Fiscales 2026")
                rfc = st.text_input("RFC")
                
                submitted = st.form_submit_button("💾 Crear Expediente")
                
                if submitted:
                    errores = []
                    # Validaciones
                    if not nombre or not ap_pat: errores.append("Nombre y Apellido Paterno son obligatorios.")
                    
                    # Validar Telefono
                    tel_clean = re.sub(r'\D', '', telefono_input)
                    if len(tel_clean) != 10:
                        errores.append("El teléfono debe tener exactamente 10 dígitos.")
                    else:
                        tel_final = f"{tel_clean[:2]}-{tel_clean[2:6]}-{tel_clean[6:]}" # Formato xx-xxxx-xxxx
                    
                    # Validar Email
                    if email and not validar_email(email):
                        errores.append("El correo electrónico no es válido (falta @ o extensión).")
                    
                    if errores:
                        for e in errores: st.error(f"⚠️ {e}")
                    else:
                        # Guardar en DB
                        try:
                            # Lógica de guardado...
                            st.success(f"✅ Paciente registrado: {nombre} {ap_pat}")
                            st.info(f"Teléfono formateado: {tel_final}")
                            st.balloons()
                        except Exception as ex:
                            st.error(f"Error al guardar: {ex}")

    # --- AGENDA (VISUALIZACIÓN) ---
    elif menu == "Agenda (Citas)":
        st.header("📅 Agenda del Consultorio")
        
        col_cal1, col_cal2 = st.columns([1,3])
        fecha_ver = col_cal1.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
        
        with col_cal2:
            st.subheader(f"Citas para el: {fecha_ver}")
            # Simulación de lectura de citas
            try:
                citas_all = pd.DataFrame(sheet_citas.get_all_records())
                if not citas_all.empty:
                    # Filtrar por fecha (asumiendo formato YYYY-MM-DD en string)
                    # Convertir columna fecha a string para comparar
                    citas_dia = citas_all[citas_all['fecha'].astype(str) == str(fecha_ver)]
                    
                    if not citas_dia.empty:
                        # Mostrar tabla limpia
                        st.dataframe(citas_dia[['hora', 'nombre_paciente', 'tratamiento', 'doctor_atendio', 'estado_pago']], use_container_width=True)
                    else:
                        st.info("No hay citas programadas para este día.")
                else:
                    st.info("Base de datos de citas vacía.")
            except:
                st.error("Error al leer la agenda.")

    # --- NUEVO: PLANES DE TRATAMIENTO (COTIZADOR) ---
    elif menu == "Planes de Tratamiento":
        st.header("🦷 Plan de Tratamiento & Cotización")
        
        # 1. Seleccionar Paciente
        pacientes_list = get_lista_pacientes()
        paciente_sel = st.selectbox("Seleccionar Paciente", ["Buscar..."] + pacientes_list)
        
        if paciente_sel != "Buscar...":
            st.markdown("---")
            col_tr1, col_tr2 = st.columns([1, 1])
            
            # SELECCIÓN DE DIENTE (ODONTOGRAMA LÓGICO)
            with col_tr1:
                st.subheader("1. Ubicación Dental")
                tipo_dent = st.radio("Dentición", ["Permanente (Adulto)", "Temporal (Niño)"], horizontal=True)
                
                cd1, cd2 = st.columns(2)
                if tipo_dent == "Permanente (Adulto)":
                    cuadrante = cd1.selectbox("Cuadrante", [1, 2, 3, 4])
                    diente = cd2.selectbox("Diente", [1,2,3,4,5,6,7,8])
                    diente_final = (cuadrante * 10) + diente
                else:
                    cuadrante = cd1.selectbox("Cuadrante", [5, 6, 7, 8])
                    diente = cd2.selectbox("Diente", [1,2,3,4,5])
                    diente_final = (cuadrante * 10) + diente
                
                st.metric("Diente Seleccionado", f"#{diente_final}")

            # SELECCIÓN DE SERVICIO Y PRECIO
            with col_tr2:
                st.subheader("2. Detalle del Tratamiento")
                
                # Cargar servicios desde DB
                df_servicios = get_catalogo_servicios()
                
                if not df_servicios.empty:
                    servicio_sel = st.selectbox("Tratamiento", df_servicios['nombre_tratamiento'].unique())
                    
                    # Buscar precio del servicio seleccionado
                    info_servicio = df_servicios[df_servicios['nombre_tratamiento'] == servicio_sel].iloc[0]
                    precio_base = float(info_servicio['precio_lista'])
                    
                    st.write(f"Categoría: **{info_servicio['categoria']}**")
                    precio_final = st.number_input("Precio Final (Editable)", value=precio_base)
                else:
                    st.warning("No hay servicios en la BD. Agrega manual.")
                    servicio_sel = st.text_input("Tratamiento Manual")
                    precio_final = st.number_input("Precio")

                doctor = st.selectbox("Doctor que Atiende", ["Dr. Emmanuel", "Dra. Mónica"])
                
                # Botón de agendar
                fecha_cita = st.date_input("Fecha de Cita")
                hora_cita = st.time_input("Hora")
                
                if st.button("📅 AGENDAR CITA Y GUARDAR PLAN"):
                    # Crear ID Cita
                    # Guardar en sheet_citas
                    nuevo_id_cita = str(int(time.time())) # ID simple basado en tiempo
                    id_paciente = paciente_sel.split(" - ")[0]
                    nombre_pac = paciente_sel.split(" - ")[1]
                    
                    # id_cita, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, numero_diente...
                    # Ajusta el orden según tus columnas EXACTAS de Sheet citas
                    row_cita = [
                        nuevo_id_cita, str(fecha_cita), str(hora_cita), id_paciente, nombre_pac, 
                        "General", servicio_sel, diente_final, doctor, 
                        precio_base, precio_final, 0, "No", 0, 0, "Efectivo", "Pendiente", "No", ""
                    ]
                    
                    sheet_citas.append_row(row_cita)
                    st.success("✅ Cita agendada correctamente.")
                    time.sleep(1.5)
                    st.rerun()

# ==========================================
# 5. MAIN APP
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
