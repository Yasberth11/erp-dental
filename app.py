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
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="collapsed")
TZ_MX = pytz.timezone('America/Mexico_City')

def cargar_estilo_royal():
    st.markdown("""
        <style>
        .stApp { background-color: #F4F6F6; }
        .royal-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-bottom: 20px; }
        h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; transition: all 0.3s; }
        .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        /* Inputs y Selects */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        .stSuccess { background-color: #D4EDDA; color: #155724; border-left: 5px solid #28a745; }
        .stError { background-color: #F8D7DA; color: #721c24; border-left: 5px solid #dc3545; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB (SIN CACHÉ AGRESIVO PARA VER CAMBIOS REALES)
# ==========================================
# Usamos ttl=0 para forzar recarga si hay problemas de sincronización, 
# o un ttl bajo (60s) para balancear.
@st.cache_resource(ttl=10) 
def get_database_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client.open("ERP_DENTAL_DB")

try:
    db = get_database_connection()
    # Mapeo de Hojas
    sheet_pacientes = db.worksheet("pacientes")
    sheet_citas = db.worksheet("citas")
    sheet_asistencia = db.worksheet("asistencia")
    sheet_servicios = db.worksheet("servicios")
except Exception as e:
    st.error(f"❌ Error Crítico de Conexión: {e}")
    st.stop()

# ==========================================
# 3. HELPERS Y LÓGICA DE NEGOCIO
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def validar_email(email):
    if not email: return True # Permitir vacío si no es obligatorio, o cambiar a False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def formatear_telefono(numero):
    limpio = re.sub(r'\D', '', str(numero))
    if len(limpio) == 10:
        return f"{limpio[:2]}-{limpio[2:6]}-{limpio[6:]}"
    return numero

def generar_slots_tiempo():
    # De 8:00 AM a 6:30 PM (última cita), intervalos de 30 min
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("18:30", "%H:%M")
    
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales():
    # Lista 2026 actualizada
    return [
        "605 - Sueldos y Salarios e Ingresos Asimilados",
        "612 - Personas Físicas con Actividades Empresariales y Profesionales",
        "626 - Régimen Simplificado de Confianza (RESICO)",
        "616 - Sin obligaciones fiscales",
        "601 - General de Ley Personas Morales"
    ]

def get_usos_cfdi():
    return ["D01 - Honorarios médicos, dentales y gastos hospitalarios", "S01 - Sin efectos fiscales", "G03 - Gastos en general"]

# ==========================================
# 4. TEXTOS LEGALES (GENERADOR)
# ==========================================
def mostrar_texto_legal(tipo, nombre_paciente):
    if tipo == "Privacidad":
        return f"""
        **AVISO DE PRIVACIDAD - ROYAL DENTAL**
        
        En cumplimiento con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP), 
        ROYAL DENTAL hace de su conocimiento que los datos personales recabados del paciente **{nombre_paciente}** serán utilizados exclusivamente para los siguientes fines:
        1. Prestación de servicios odontológicos.
        2. Creación y manejo del expediente clínico.
        3. Facturación y cobro.
        
        Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse (Derechos ARCO) al tratamiento de sus datos.
        Fecha de emisión: {get_fecha_mx()}
        """
    elif tipo == "Consentimiento":
        return f"""
        **CONSENTIMIENTO INFORMADO**
        
        Yo, **{nombre_paciente}**, declaro haber sido informado/a de manera clara sobre el diagnóstico, 
        pronóstico y riesgos del tratamiento dental a realizar en ROYAL DENTAL.
        
        Autorizo al personal médico a realizar los procedimientos necesarios. Entiendo que la medicina y 
        odontología no son ciencias exactas y no se me ha garantizado un resultado específico, sino el 
        uso de los medios adecuados para mi salud.
        """
    return ""

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 30px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        tipo = st.selectbox("Seleccione Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        
        if st.button("INGRESAR AL SISTEMA"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("⛔ Credenciales incorrectas.")

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    st.sidebar.title("🏥 Royal Dental")
    st.sidebar.markdown(f"User: **{st.session_state.perfil}**")
    
    # Menú reestructurado
    menu = st.sidebar.radio("Navegación", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Control Asistencia"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()

    # ------------------------------------------------------------------
    # MÓDULO 1: AGENDA (Tiempo Real + Citas)
    # ------------------------------------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        col_cal1, col_cal2 = st.columns([1, 2])
        
        # Selección de fecha
        fecha_ver = col_cal1.date_input("Seleccionar Día", datetime.now(TZ_MX))
        
        # AGENDAR NUEVA CITA
        with col_cal1:
            with st.expander("➕ AGENDAR CITA NUEVA", expanded=True):
                with st.form("form_agendar", clear_on_submit=True):
                    # Cargar lista de pacientes
                    pacientes_raw = sheet_pacientes.get_all_records()
                    lista_pac = [f"{p['id_paciente']} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    
                    paciente_cita = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    
                    # Slots de tiempo
                    slots = generar_slots_tiempo()
                    hora_cita = st.selectbox("Hora (30 min)", slots)
                    
                    tratamiento_cita = st.text_input("Motivo / Tratamiento")
                    doc_cita = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    es_urgencia = st.checkbox("🚨 Es Urgencia / Sobrecupo (Permitir duplicar hora)")
                    
                    btn_agendar = st.form_submit_button("Confirmar Cita")
                    
                    if btn_agendar:
                        if paciente_cita != "Seleccionar..." and tratamiento_cita:
                            # Validar disponibilidad
                            citas_data = sheet_citas.get_all_records()
                            df_citas = pd.DataFrame(citas_data)
                            ocupado = False
                            
                            if not df_citas.empty:
                                # Filtrar fecha y hora exacta
                                # Asegurar tipos string
                                df_citas['fecha'] = df_citas['fecha'].astype(str)
                                df_citas['hora'] = df_citas['hora'].astype(str)
                                
                                # Hora viene HH:MM, en db puede estar HH:MM:SS, normalizar a HH:MM
                                match = df_citas[
                                    (df_citas['fecha'] == str(fecha_ver)) & 
                                    (df_citas['hora'].str.startswith(hora_cita))
                                ]
                                if not match.empty:
                                    ocupado = True
                            
                            if ocupado and not es_urgencia:
                                st.error(f"⚠️ El horario {hora_cita} ya está ocupado. Marque 'Urgencia' para sobrecupo.")
                            else:
                                # Guardar
                                id_pac = paciente_cita.split(" - ")[0]
                                nom_pac = paciente_cita.split(" - ")[1]
                                nuevo_id_cita = int(time.time())
                                
                                # id_cita, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, diente, doc...
                                row = [nuevo_id_cita, str(fecha_ver), hora_cita, id_pac, nom_pac, 
                                       "General", tratamiento_cita, "", doc_cita, 0, 0, 0, "No", 0, 0, "", "Pendiente", "No", ""]
                                sheet_citas.append_row(row)
                                st.success(f"Cita agendada: {hora_cita} - {nom_pac}")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("Falta seleccionar paciente o tratamiento.")

        # VISUALIZADOR DE AGENDA (GRILLA)
        with col_cal2:
            st.markdown(f"#### 🗓️ Visualización: {fecha_ver}")
            
            # Obtener citas del día
            citas_data = sheet_citas.get_all_records()
            df_c = pd.DataFrame(citas_data)
            dict_agenda = {}
            
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str)
                # Filtrar dia
                df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                # Crear diccionario Hora -> Info
                for idx, row in df_dia.iterrows():
                    # Normalizar hora a HH:MM
                    h = str(row['hora'])[:5] 
                    info = f"👤 {row['nombre_paciente']}<br>🦷 {row['tratamiento']}<br>👨‍⚕️ {row['doctor_atendio']}"
                    # Si ya hay cita (urgencia), concatenar
                    if h in dict_agenda:
                        dict_agenda[h] += f"<br><hr style='margin:2px 0; border-top: 1px dashed red;'>🚨 <b>URGENCIA:</b><br>{info}"
                    else:
                        dict_agenda[h] = info

            # Renderizar Slots
            slots_visuales = generar_slots_tiempo()
            
            for slot in slots_visuales:
                ocupado = slot in dict_agenda
                bg_color = "#FFEBEE" if ocupado else "#E3F2FD" # Rojo suave ocupado, Azul suave libre
                border_color = "#FFCDD2" if ocupado else "#BBDEFB"
                contenido = dict_agenda[slot] if ocupado else "<span style='color:#888; font-size:0.8em;'>Disponible</span>"
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 5px; padding: 8px; margin-bottom: 5px; display: flex; align-items: center;">
                    <div style="font-weight: bold; color: #002B5B; width: 60px; font-size: 1.1em;">{slot}</div>
                    <div style="margin-left: 10px; font-size: 0.9em; color: #333;">{contenido}</div>
                </div>
                """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # MÓDULO 2: GESTIÓN DE PACIENTES (Alta + Legal)
    # ------------------------------------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("🦷 Expediente Clínico Digital")
        
        tab1, tab2 = st.tabs(["🔍 BUSCAR / GESTIONAR PACIENTE", "➕ NUEVO PACIENTE (ALTA)"])
        
        # --- PESTAÑA 1: GESTIÓN EXISTENTE ---
        with tab1:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw:
                st.warning("No hay pacientes registrados.")
            else:
                lista_busqueda = [f"{p['id_paciente']} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
                seleccion = st.selectbox("Seleccionar Paciente para Gestión:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    # Obtener datos del paciente seleccionado
                    id_sel = int(seleccion.split(" - ")[0])
                    # Buscar en la lista raw (es más rápido que filtrar DF a veces)
                    paciente_data = next((item for item in pacientes_raw if item["id_paciente"] == id_sel), None)
                    
                    if paciente_data:
                        st.markdown(f"### 📂 Expediente: {paciente_data['nombre']} {paciente_data['apellido_paterno']}")
                        
                        col_legal1, col_legal2 = st.columns(2)
                        
                        with col_legal1:
                            st.info("📄 **Generación de Documentos Legales**")
                            doc_accion = st.radio("Seleccionar Documento:", ["Historia Clínica", "Consentimiento Informado", "Aviso de Privacidad"], horizontal=True)
                            
                            if st.button(f"Generar {doc_accion}"):
                                texto = mostrar_texto_legal(doc_accion.split()[0], f"{paciente_data['nombre']} {paciente_data['apellido_paterno']}")
                                st.markdown("---")
                                st.markdown(texto)
                                st.success("Documento listo para imprimir/firmar (Simulación PDF).")
                        
                        with col_legal2:
                            st.info("🦷 **Historial de Tratamientos**")
                            # Filtrar citas de este paciente
                            citas_raw = sheet_citas.get_all_records()
                            df_hist = pd.DataFrame(citas_raw)
                            if not df_hist.empty:
                                df_p = df_hist[df_hist['id_paciente'].astype(str) == str(id_sel)]
                                if not df_p.empty:
                                    st.dataframe(df_p[['fecha', 'tratamiento', 'doctor_atendio', 'precio_final']])
                                else:
                                    st.caption("Sin tratamientos previos.")

        # --- PESTAÑA 2: ALTA NUEVA (CORREGIDA Y COMPLETA) ---
        with tab2:
            st.markdown("#### Formulario de Alta (Campos Obligatorios *)")
            
            # Form con clear_on_submit=True para evitar duplicados al volver a clickear
            with st.form("alta_paciente_full", clear_on_submit=True):
                
                # SECCIÓN 1: DATOS PERSONALES
                st.subheader("1. Datos Personales")
                col_a, col_b, col_c = st.columns([1,1,1])
                nombre = col_a.text_input("Nombre(s) *")
                ap_pat = col_b.text_input("Apellido Paterno *")
                ap_mat = col_c.text_input("Apellido Materno")
                
                col_d, col_e = st.columns(2)
                f_nac = col_d.date_input("Fecha de Nacimiento", min_value=datetime(1920, 1, 1), max_value=datetime.now())
                
                # Teléfono
                tel_input = col_e.text_input("Teléfono Móvil (10 dígitos) *", placeholder="5512345678")
                
                email = st.text_input("Correo Electrónico")
                
                # SECCIÓN 2: DATOS FISCALES (RESTAURADOS)
                st.markdown("---")
                st.subheader("2. Datos Fiscales (Facturación)")
                
                col_f1, col_f2 = st.columns(2)
                rfc = col_f1.text_input("RFC (Opcional)")
                cp = col_f2.text_input("Código Postal (CP)")
                
                regimen = col_f1.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                uso_cfdi = col_f2.selectbox("Uso de CFDI", get_usos_cfdi())
                
                # SECCIÓN 3: MÉDICOS
                st.markdown("---")
                st.subheader("3. Alertas Médicas")
                alertas = st.text_area("Alergias / Padecimientos", placeholder="Ninguna")
                
                submit_btn = st.form_submit_button("💾 CREAR EXPEDIENTE")
                
                if submit_btn:
                    errores = []
                    # Validaciones básicas
                    if not nombre or not ap_pat: errores.append("Nombre y Apellido Paterno son obligatorios.")
                    
                    # Validar Tel
                    tel_clean = re.sub(r'\D', '', tel_input)
                    if len(tel_clean) != 10: errores.append("El teléfono debe tener 10 dígitos exactos.")
                    
                    if errores:
                        for err in errores: st.error(err)
                    else:
                        # Chequeo anti-duplicados básico
                        existe = False
                        if pacientes_raw:
                            for p in pacientes_raw:
                                if str(p['nombre']).lower() == nombre.lower() and str(p['apellido_paterno']).lower() == ap_pat.lower():
                                    existe = True
                                    break
                        
                        if existe:
                            st.error("⚠️ ERROR: Ya existe un paciente con ese Nombre y Apellido Paterno.")
                        else:
                            # Preparar datos
                            nuevo_id = len(pacientes_raw) + 1 if pacientes_raw else 1
                            fecha_reg = get_fecha_mx()
                            tel_fmt = formatear_telefono(tel_clean)
                            
                            # ESTRUCTURA EXACTA 15 COLUMNAS
                            # id, fecha, nombre, pat, mat, tel, email, rfc, regimen, uso, cp, alertas, link, estado, ultima
                            row_new = [
                                nuevo_id, 
                                fecha_reg, 
                                nombre, 
                                ap_pat, 
                                ap_mat, 
                                tel_fmt, 
                                email, 
                                rfc, 
                                regimen.split(" - ")[0], # Solo código
                                uso_cfdi.split(" - ")[0], # Solo código
                                cp, 
                                alertas, 
                                "", "Activo", ""
                            ]
                            
                            try:
                                sheet_pacientes.append_row(row_new)
                                st.success(f"✅ Paciente {nombre} {ap_pat} registrado correctamente.")
                                st.toast(f"Teléfono formateado: {tel_fmt}")
                                time.sleep(1.5) # Espera breve para asegurar escritura
                                st.rerun() # Recargar para limpiar form y actualizar listas
                            except Exception as ex:
                                st.error(f"Error al escribir en Google Sheets: {ex}")

    # ------------------------------------------------------------------
    # MÓDULO 3: ASISTENCIA (Simplificado)
    # ------------------------------------------------------------------
    elif menu == "3. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        col1, col2 = st.columns([1,3])
        with col1:
             if st.button("Marcaje Rápido (Entrada)"):
                 st.success("Entrada registrada (Demo)")
        with col2:
             st.info("Para reportes detallados, ingresar como Administrador.")

# ==========================================
# 7. VISTA ADMINISTRACIÓN
# ==========================================
def vista_admin():
    st.title("Panel Director")
    if st.button("Salir"): st.session_state.perfil=None; st.rerun()
    st.write("Aquí van las finanzas y nómina compleja.")

# ==========================================
# MAIN APP
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        vista_admin()
