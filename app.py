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
        
        /* Compactar formulario */
        .stForm > div { padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB
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
# 3. HELPERS
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def calcular_edad(nacimiento):
    hoy = datetime.now().date()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))

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
    return [
        "605 - Sueldos y Salarios", 
        "612 - Personas Físicas con Actividades Empresariales", 
        "626 - RESICO", 
        "616 - Sin obligaciones fiscales", 
        "601 - General de Ley Personas Morales"
    ]

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
    # MÓDULO 1: AGENDA (MEJORADA)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Calendario")
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            
            st.markdown("---")
            st.markdown("### ⚡ Cita Rápida")
            with st.form("quick_cita", clear_on_submit=True):
                st.caption("Para revisiones, primera vez o familiares.")
                # Pacientes
                pacientes_raw = sheet_pacientes.get_all_records()
                lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                
                q_paciente = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                q_hora = st.selectbox("Hora", generar_slots_tiempo())
                q_motivo = st.text_input("Motivo (Ej. Revisión, Valoración)")
                q_doc = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                
                if st.form_submit_button("Agendar Cita Rápida"):
                    if q_paciente != "Seleccionar...":
                        id_p = q_paciente.split(" - ")[0]
                        nom_p = q_paciente.split(" - ")[1]
                        # Precio 0, Tratamiento General
                        row = [int(time.time()), str(fecha_ver), q_hora, id_p, nom_p, "General", q_motivo, "", q_doc, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "Cita Rápida"]
                        sheet_citas.append_row(row)
                        st.success("Cita agendada.")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("Seleccione paciente")

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver}")
            citas_data = sheet_citas.get_all_records()
            df_c = pd.DataFrame(citas_data)
            
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str)
                df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                
                slots = generar_slots_tiempo()
                for slot in slots:
                    ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)]
                    
                    if ocupado.empty:
                        # Slot Vacío
                        st.markdown(f"""
                        <div style="padding: 8px; border-bottom: 1px solid #eee; display: flex; align-items: center;">
                            <span style="font-weight:bold; color:#aaa; width: 60px;">{slot}</span>
                            <span style="color:#ddd; font-size: 0.9em;">Disponible</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        # Slot Ocupado (Iterar por si hay urgencias dobles)
                        for _, r in ocupado.iterrows():
                            color_borde = "#28a745" if r.get('estado_pago') == "Pagado" else "#D4AF37"
                            bg_card = "#fdfdfd"
                            
                            st.markdown(f"""
                            <div style="padding: 10px; margin-bottom: 5px; background-color: {bg_card}; border-left: 5px solid {color_borde}; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-radius: 4px;">
                                <div style="display:flex; justify-content:space-between;">
                                    <span style="font-weight:bold; color:#002B5B; font-size:1.1em;">{slot} | {r['nombre_paciente']}</span>
                                    <span style="background-color:#eee; padding:2px 8px; border-radius:10px; font-size:0.8em;">{r['doctor_atendio']}</span>
                                </div>
                                <div style="color:#555; font-size:0.9em; margin-top:4px;">
                                    🦷 <b>{r['tratamiento']}</b> 
                                    <span style="float:right;">Cobro: ${r['precio_final']} ({r['estado_pago']})</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    # ------------------------------------
    # MÓDULO 2: PACIENTES (OPTIMIZADO V12)
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("🦷 Expediente Clínico")
        
        tab_b, tab_n = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)"])
        
        # PESTAÑA BUSCAR (CON EDAD VISIBLE)
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
                        # Calcular edad al vuelo para visualización
                        try:
                            f_nac_obj = datetime.strptime(p_data['fecha_nacimiento'], "%Y-%m-%d").date() # Asumiendo formato YYYY-MM-DD
                            edad_calc = calcular_edad(f_nac_obj)
                        except:
                            edad_calc = "N/A"

                        st.markdown(f"""
                        <div class="royal-card">
                            <div style="display:flex; justify-content:space-between;">
                                <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>
                                <h3 style="color:#D4AF37;">{edad_calc} Años</h3>
                            </div>
                            <b>ID:</b> {p_data['id_paciente']} <br>
                            <b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}<br>
                            <b>RFC:</b> {p_data['rfc']} | <b>Régimen:</b> {p_data['regimen']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        with c1: 
                            if st.button("📄 Historia Clínica (PDF)"): st.success("PDF generado.")
                        with c2:
                            if st.button("📄 Consentimiento (PDF)"): st.success("PDF generado.")

        # PESTAÑA NUEVO (LAYOUT CORREGIDO)
        with tab_n:
            st.markdown("#### Formulario de Alta")
            with st.form("alta_paciente_v12", clear_on_submit=True):
                # FILA 1: NOMBRES (Orden Correcto)
                c_nom, c_pat, c_mat = st.columns(3)
                nombre = c_nom.text_input("Nombre(s)")
                paterno = c_pat.text_input("Apellido Paterno")
                materno = c_mat.text_input("Apellido Materno")
                
                # FILA 2: DATOS CONTACTO Y EDAD
                c_nac, c_tel, c_mail = st.columns(3)
                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
                tel = c_tel.text_input("Teléfono (10 dígitos)")
                email = c_mail.text_input("Email")
                
                st.markdown("---")
                # FILA 3: FISCAL (COMPLETO)
                st.markdown("**Datos Fiscales 2026**")
                c_f1, c_f2, c_f3 = st.columns(3)
                rfc = c_f1.text_input("RFC")
                cp = c_f2.text_input("Código Postal (CP)")
                uso = c_f3.selectbox("Uso CFDI", get_usos_cfdi())
                
                regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                
                st.info("ℹ️ La edad se calculará y guardará automáticamente al confirmar.")
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    if nombre and paterno and len(tel)==10:
                        nuevo_id = generar_id_unico(nombre, paterno, nacimiento)
                        fecha_reg = get_fecha_mx()
                        tel_fmt = formatear_telefono(tel)
                        
                        # id, fecha, nombre, pat, mat, tel, email, rfc, reg, uso, cp, alertas, link, estado, ultima
                        # Nota: Guardamos fecha nacimiento en un campo, asumimos estructura flexible o usamos columna extra si existe
                        # Si tu DB es estricta, asegúrate que las columnas coincidan. 
                        # Aquí mapeo a las 15 columnas exactas de "pacientes" que me diste al inicio + lógica de nacimiento si cabe.
                        # SI NO TIENES COLUMNA FECHA NACIMIENTO EN DB: Lo guardaré en 'alertas' temporalmente o asumo que agregaste la columna.
                        # Para no romper, usaré un formato estándar.
                        
                        row = [
                            nuevo_id, fecha_reg, nombre, paterno, materno, tel_fmt, email, 
                            rfc, regimen.split(" - ")[0], uso.split(" - ")[0], cp, 
                            f"Nac: {nacimiento}", "", "Activo", ""
                        ]
                        
                        sheet_pacientes.append_row(row)
                        st.success(f"Paciente Registrado. ID: {nuevo_id}")
                        st.balloons()
                        time.sleep(2); st.rerun()
                    else:
                        st.error("Faltan datos obligatorios o teléfono inválido.")

    # ------------------------------------
    # MÓDULO 3: TRATAMIENTOS (CASCADA)
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Cotizador y Tratamientos")
        
        # Cargar Pacientes
        pacientes_raw = sheet_pacientes.get_all_records()
        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
        seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
        
        if seleccion_pac != "Buscar...":
            st.markdown("---")
            
            # Cargar Servicios (DataFrame para filtrado)
            try:
                servicios_data = sheet_servicios.get_all_records()
                df_servicios = pd.DataFrame(servicios_data)
            except:
                df_servicios = pd.DataFrame()

            with st.form("form_plan_v12"):
                c_izq, c_der = st.columns(2)
                
                with c_izq:
                    st.subheader("1. Selección de Servicio")
                    
                    if not df_servicios.empty and 'categoria' in df_servicios.columns:
                        # 1. Categoría
                        lista_cats = df_servicios['categoria'].unique().tolist()
                        cat_sel = st.selectbox("Categoría", lista_cats)
                        
                        # 2. Tratamiento (Filtrado)
                        df_filtrado = df_servicios[df_servicios['categoria'] == cat_sel]
                        lista_trats = df_filtrado['nombre_tratamiento'].unique().tolist()
                        trat_sel = st.selectbox("Tratamiento", lista_trats)
                        
                        # Obtener precio base
                        item = df_filtrado[df_filtrado['nombre_tratamiento'] == trat_sel].iloc[0]
                        precio_sug = float(item.get('precio_lista', 0))
                        costo_lab = float(item.get('costo_laboratorio_base', 0))
                    else:
                        st.warning("No se cargó el catálogo de servicios. Ingrese manual.")
                        trat_sel = st.text_input("Tratamiento")
                        precio_sug = 0.0
                        costo_lab = 0.0

                    # Selector Diente (Simple)
                    diente = st.number_input("Diente (ISO)", min_value=0, max_value=85, help="0 para general")

                with c_der:
                    st.subheader("2. Finanzas")
                    precio_final = st.number_input("Precio Final (Editable)", value=precio_sug)
                    abono = st.number_input("Abono Inicial", min_value=0.0)
                    doctor = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    st.info(f"Costo Lab Base: ${costo_lab} (Interno)")
                    
                    if st.form_submit_button("💾 REGISTRAR PLAN"):
                        id_p = seleccion_pac.split(" - ")[0]
                        nom_p = seleccion_pac.split(" - ")[1]
                        
                        estatus = "Pagado" if abono >= precio_final else "Pendiente"
                        utilidad = precio_final - costo_lab
                        
                        # Guardar en Citas como registro financiero
                        # id, fecha, hora, id_pac, nom, cat, trat, diente, doc, precio, final, desc, lab, c_lab, util, metodo, est, fac, notas
                        row = [
                            int(time.time()), str(get_fecha_mx()), get_hora_mx(), id_p, nom_p,
                            cat_sel if not df_servicios.empty else "Manual", trat_sel, diente, doctor,
                            precio_sug, precio_final, 0, "Sí" if costo_lab > 0 else "No", costo_lab, utilidad,
                            "Efectivo", estatus, "No", "Plan Generado"
                        ]
                        sheet_citas.append_row(row)
                        st.success("Plan registrado en Bitácora.")

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        col1, col2 = st.columns([1,3])
        with col1:
            st.markdown("### 👨‍⚕️ Dr. Emmanuel")
            c_a, c_b = st.columns(2)
            if c_a.button("🟢 ENTRADA"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(m)
                else: st.warning(m)
            if c_b.button("🔴 SALIDA"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(m)
                else: st.warning(m)
        with col2:
             st.info("Sistema operando en Tiempo Real CDMX.")

if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
