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

st.set_page_config(page_title="Royal Dental Manager", page_icon="📂", layout="wide", initial_sidebar_state="expanded")

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

        

        /* Tablas */

        div[data-testid="stDataFrame"] { border: 1px solid #ddd; border-radius: 5px; }

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

# 3. HELPERS & SANITIZACIÓN (FORMATO LATINO)

# ==========================================

def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")

def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")



def format_date_latino(date_obj):

    return date_obj.strftime("%d/%m/%Y")



def parse_date_latino(date_str):

    try: return datetime.strptime(date_str, "%d/%m/%Y").date()

    except:

        try: return datetime.strptime(date_str, "%Y-%m-%d").date()

        except: return None



def limpiar_texto_mayus(texto):

    if not texto: return ""

    remplaces = {'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U', 'á':'A', 'é':'E', 'í':'I', 'ó':'O', 'ú':'U'}

    texto = texto.upper()

    for k, v in remplaces.items(): texto = texto.replace(k, v)

    return texto



def limpiar_email(texto):

    if not texto: return ""

    return texto.lower().strip()



def calcular_edad_completa(nacimiento_input):

    hoy = datetime.now().date()

    nacimiento = parse_date_latino(nacimiento_input) if isinstance(nacimiento_input, str) else nacimiento_input

    if nacimiento:

        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))

        tipo = "MENOR DE EDAD" if edad < 18 else "ADULTO"

        return edad, tipo

    return "N/A", ""



def generar_id_unico(nombre, paterno, nacimiento):

    try:

        part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"

        part2 = nombre[0].upper()

        part3 = str(nacimiento.year)

        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

        return f"{part1}{part2}-{part3}-{random_chars}"

    except: return f"P-{int(time.time())}"



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

    # MÓDULO 1: AGENDA (CON BUSCADOR GLOBAL)

    # ------------------------------------

    if menu == "1. Agenda & Citas":

        st.title("📅 Agenda del Consultorio")

        

        # --- BUSCADOR GLOBAL DE CITAS ---

        with st.expander("🔍 BUSCADOR DE CITAS (¿Cuándo le toca a...?)", expanded=False):

            st.info("Escribe el nombre del paciente para ver su historial completo de citas.")

            q_cita = st.text_input("Nombre del Paciente:")

            if q_cita:

                try:

                    all_citas = sheet_citas.get_all_records()

                    df_all = pd.DataFrame(all_citas)

                    if not df_all.empty:

                        # Filtrar

                        df_res = df_all[df_all['nombre_paciente'].str.contains(q_cita, case=False, na=False)]

                        if not df_res.empty:

                            st.write(f"Encontradas {len(df_res)} citas:")

                            # Mostrar tabla simplificada

                            st.dataframe(df_res[['fecha', 'hora', 'nombre_paciente', 'tratamiento', 'doctor_atendio', 'estado_pago']])

                        else:

                            st.warning("No se encontraron citas con ese nombre.")

                except Exception as e:

                    st.error(f"Error en búsqueda: {e}")



        st.markdown("---")

        

        col_cal1, col_cal2 = st.columns([1, 2.5])

        

        with col_cal1:

            st.markdown("### 📆 Gestión")

            # FECHA CON FORMATO LATINO VISUAL

            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")

            fecha_ver_str = format_date_latino(fecha_ver_obj)

            

            # --- AGENDAR ---

            with st.expander("➕ Agendar Cita Nueva", expanded=False):

                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])

                

                with tab_reg:

                    with st.form("cita_registrada"):

                        pacientes_raw = sheet_pacientes.get_all_records()

                        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []

                        

                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)

                        h_sel = st.selectbox("Hora", generar_slots_tiempo())

                        m_sel = st.text_input("Motivo", "Revisión / Continuación")

                        d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])

                        

                        if st.form_submit_button("Agendar"):

                            if p_sel != "Seleccionar...":

                                id_p = p_sel.split(" - ")[0]

                                nom_p = p_sel.split(" - ")[1]

                                row = [int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "", 0, 0, ""]

                                sheet_citas.append_row(row)

                                st.success(f"Agendado el {fecha_ver_str}")

                                time.sleep(1); st.rerun()

                            else: st.error("Seleccione paciente")



                with tab_new:

                    with st.form("cita_prospecto"):

                        nombre_pros = st.text_input("Nombre")

                        tel_pros = st.text_input("Tel (10)", max_chars=10)

                        hora_pros = st.selectbox("Hora", generar_slots_tiempo())

                        motivo_pros = st.text_input("Motivo", "Revisión 1ra Vez")

                        precio_pros = st.number_input("Costo", value=100.0, min_value=0.0)

                        doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])

                        

                        if st.form_submit_button("Agendar Prospecto"):

                            if nombre_pros and len(tel_pros) == 10:

                                id_temp = f"PROSPECTO-{int(time.time())}"

                                nom_final = limpiar_texto_mayus(nombre_pros)

                                row = [

                                    int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, 

                                    "Primera Vez", motivo_pros, "", doc_pros, 

                                    precio_pros, precio_pros, 0, "No", 0, precio_pros, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}",

                                    0, precio_pros, ""

                                ]

                                sheet_citas.append_row(row)

                                st.success("Agendado")

                                time.sleep(1); st.rerun()

                            else: st.error("Datos incorrectos")

            

            # --- MODIFICAR CITAS ---

            st.markdown("### 🔄 Modificar Agenda")

            citas_data = sheet_citas.get_all_records()

            df_c = pd.DataFrame(citas_data)

            

            if not df_c.empty:

                df_c['fecha'] = df_c['fecha'].astype(str)

                df_dia = df_c[df_c['fecha'] == fecha_ver_str]

                

                if not df_dia.empty:

                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['tratamiento']})" for i, r in df_dia.iterrows()]

                    cita_sel = st.selectbox("Seleccionar Cita:", ["Seleccionar..."] + lista_citas_dia)

                    

                    if cita_sel != "Seleccionar...":

                        hora_target = cita_sel.split(" - ")[0]

                        nombre_target = cita_sel.split(" - ")[1].split(" (")[0]

                        

                        tab_del, tab_res = st.tabs(["❌ Cancelar", "🗓️ Reagendar"])

                        

                        with tab_del:

                            if st.button("Eliminar Cita Definitivamente"):

                                all_vals = sheet_citas.get_all_values()

                                for idx, row in enumerate(all_vals):

                                    if row[1] == fecha_ver_str and row[2] == hora_target and row[4] == nombre_target:

                                        sheet_citas.delete_rows(idx + 1)

                                        st.success("Cita eliminada y horario liberado.")

                                        time.sleep(1); st.rerun()

                                        break

                        

                        with tab_res:

                            st.info(f"Cita Actual: {hora_target} del {fecha_ver_str}")

                            with st.form("form_reagendar"):

                                nueva_fecha_obj = st.date_input("Nueva Fecha", format="DD/MM/YYYY")

                                nueva_hora = st.selectbox("Nueva Hora", generar_slots_tiempo())

                                

                                if st.form_submit_button("Confirmar Cambio"):

                                    nueva_fecha_str = format_date_latino(nueva_fecha_obj)

                                    all_vals = sheet_citas.get_all_values()

                                    for idx, row in enumerate(all_vals):

                                        if row[1] == fecha_ver_str and row[2] == hora_target and row[4] == nombre_target:

                                            row_gs = idx + 1

                                            sheet_citas.update_cell(row_gs, 2, nueva_fecha_str)

                                            sheet_citas.update_cell(row_gs, 3, nueva_hora)

                                            st.success(f"✅ Horario {hora_target} LIBERADO. Nuevo horario: {nueva_hora} ({nueva_fecha_str}) ASIGNADO.")

                                            time.sleep(2); st.rerun()

                                            break

                else:

                    st.info("No hay citas este día.")



        with col_cal2:

            st.markdown(f"#### 📋 Programación: {fecha_ver_str}")

            if not df_c.empty:

                df_c['fecha'] = df_c['fecha'].astype(str)

                df_dia = df_c[df_c['fecha'] == fecha_ver_str]

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



    # ------------------------------------

    # MÓDULO 2: PACIENTES

    # ------------------------------------

    elif menu == "2. Gestión Pacientes":

        st.title("📂 Expediente Clínico")

        

        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)", "✏️ EDITAR"])

        

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

                        f_nac_raw = p_data.get('fecha_nacimiento', '') 

                        edad, tipo_pac = calcular_edad_completa(f_nac_raw)

                        rfc_show = p_data.get('rfc', 'N/A')

                        st.markdown(f"""

                        <div class="royal-card">

                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>

                            <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span>

                            <br><br><b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}

                            <br><b>RFC:</b> {rfc_show}

                        </div>""", unsafe_allow_html=True)

        

        with tab_n:

            st.markdown("#### Formulario de Alta")

            requiere_factura = st.checkbox("¿Requiere Factura? (Mostrar campos fiscales SAT)", key="chk_alta")

            

            with st.form("alta_paciente_v20", clear_on_submit=True):

                c_nom, c_pat, c_mat = st.columns(3)

                nombre = c_nom.text_input("Nombre(s)")

                paterno = c_pat.text_input("Apellido Paterno")

                materno = c_mat.text_input("Apellido Materno")

                

                c_nac, c_tel, c_mail = st.columns(3)

                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now(), format="DD/MM/YYYY")

                tel = c_tel.text_input("Teléfono (10 dígitos)", max_chars=10)

                email = c_mail.text_input("Email")

                

                if requiere_factura:

                    st.markdown("---")

                    st.markdown("**Datos Fiscales (SAT)**")

                    c_f1, c_f2 = st.columns(2)

                    rfc = c_f1.text_input("RFC", max_chars=13)

                    cp = c_f2.text_input("C.P.", max_chars=5)

                    regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())

                    uso = st.selectbox("Uso CFDI", get_usos_cfdi())

                    metodo_pago_sat = st.selectbox("Método de Pago SAT", ["PUE - Pago en una sola exhibición", "PPD - Pago en parcialidades"])

                

                if st.form_submit_button("💾 GUARDAR PACIENTE"):

                    errores = []

                    if not tel.isdigit() or len(tel) != 10: errores.append("❌ Teléfono incorrecto.")

                    if not nombre or not paterno: errores.append("❌ Nombre/Apellido obligatorios.")

                    

                    if errores:

                        for e in errores: st.error(e)

                    else:

                        nom_f = limpiar_texto_mayus(nombre)

                        pat_f = limpiar_texto_mayus(paterno)

                        mat_f = limpiar_texto_mayus(materno)

                        mail_f = limpiar_email(email)

                        

                        if requiere_factura:

                            rfc_final = rfc.upper()

                            cp_final = cp

                            reg_final = regimen.split(" - ")[0]

                            uso_final = uso.split(" - ")[0]

                            nota_fiscal = f"Método SAT: {metodo_pago_sat}"

                        else:

                            rfc_final = "XAXX010101000"

                            cp_final = "N/A"
