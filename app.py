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

def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    # Robustez para leer diferentes formatos de fecha
    if isinstance(nacimiento_input, str):
        try:
            nacimiento = datetime.strptime(nacimiento_input, "%Y-%m-%d").date()
        except:
            return "N/A", ""
    else:
        nacimiento = nacimiento_input
        
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
    # MÓDULO 1: AGENDA (CON CANCELACIONES)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            
            # --- AGENDAR ---
            with st.expander("➕ Agendar Cita Nueva", expanded=True):
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
                                row = [int(time.time()), str(fecha_ver), h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "", 0, 0, ""]
                                sheet_citas.append_row(row)
                                st.success("Agendado")
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
                                    int(time.time()), str(fecha_ver), hora_pros, id_temp, nom_final, 
                                    "Primera Vez", motivo_pros, "", doc_pros, 
                                    precio_pros, precio_pros, 0, "No", 0, precio_pros, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}",
                                    0, precio_pros, ""
                                ]
                                sheet_citas.append_row(row)
                                st.success("Agendado")
                                time.sleep(1); st.rerun()
                            else: st.error("Datos incorrectos")
            
            # --- CANCELAR / REAGENDAR ---
            st.markdown("### 🗑️ Cancelar Citas")
            citas_data = sheet_citas.get_all_records()
            df_c = pd.DataFrame(citas_data)
            
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str)
                df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                
                if not df_dia.empty:
                    # Lista de citas del día para seleccionar
                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['tratamiento']})" for i, r in df_dia.iterrows()]
                    cita_a_borrar = st.selectbox("Seleccionar cita para cancelar:", ["Seleccionar..."] + lista_citas_dia)
                    
                    if cita_a_borrar != "Seleccionar...":
                        if st.button("❌ Eliminar Cita Definitivamente"):
                            # Buscar ID o parámetros únicos para borrar
                            hora_target = cita_a_borrar.split(" - ")[0]
                            nombre_target = cita_a_borrar.split(" - ")[1].split(" (")[0]
                            
                            # Encontrar celda en Sheet
                            cell = sheet_citas.find(nombre_target) # Busqueda aproximada
                            # Validar que coincida fecha y hora para no borrar homonimos
                            if cell:
                                # Esto es una simplificación. Lo ideal es buscar por ID único oculto.
                                # Dado que gspread find retorna la primera coincidencia, iteramos para asegurar
                                try:
                                    # Obtener todas las filas y buscar indice
                                    all_vals = sheet_citas.get_all_values()
                                    # index 0 is headers
                                    for idx, row in enumerate(all_vals):
                                        # row[1] fecha, row[2] hora, row[4] nombre
                                        if row[1] == str(fecha_ver) and row[2] == hora_target and row[4] == nombre_target:
                                            sheet_citas.delete_rows(idx + 1)
                                            st.success("Cita eliminada.")
                                            time.sleep(1); st.rerun()
                                            break
                                except Exception as e: st.error(f"Error borrando: {e}")
                else:
                    st.info("No hay citas para cancelar hoy.")

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver}")
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

    # ------------------------------------
    # MÓDULO 2: PACIENTES
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico") # CAMBIO DE ÍCONO
        
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
                        # CORRECCION EDAD: Usamos el parser robusto
                        edad, tipo_pac = calcular_edad_completa(p_data['fecha_nacimiento'])

                        st.markdown(f"""
                        <div class="royal-card">
                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>
                            <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span>
                            <br><br><b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}
                            <br><b>RFC:</b> {p_data['rfc']}
                        </div>""", unsafe_allow_html=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            
            # --- INTERRUPTOR FUERA DEL FORMULARIO (DINÁMICO) ---
            st.info("Los nombres se guardarán en MAYÚSCULAS automáticamente.")
            requiere_factura = st.checkbox("¿Requiere Factura? (Mostrar campos fiscales SAT)")
            
            with st.form("alta_paciente_v17", clear_on_submit=True):
                c_nom, c_pat, c_mat = st.columns(3)
                nombre = c_nom.text_input("Nombre(s)")
                paterno = c_pat.text_input("Apellido Paterno")
                materno = c_mat.text_input("Apellido Materno")
                
                c_nac, c_tel, c_mail = st.columns(3)
                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
                tel = c_tel.text_input("Teléfono (10 dígitos)", max_chars=10)
                email = c_mail.text_input("Email")
                
                # --- CAMPOS DINÁMICOS (Solo visibles si se activó el checkbox arriba) ---
                if requiere_factura:
                    st.markdown("---")
                    st.markdown("**Datos Fiscales (SAT)**")
                    c_f1, c_f2 = st.columns(2)
                    rfc = c_f1.text_input("RFC")
                    cp = c_f2.text_input("C.P.")
                    regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                    uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                    metodo_pago_sat = st.selectbox("Método de Pago SAT", ["PUE - Pago en una sola exhibición", "PPD - Pago en parcialidades o diferido"])
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    errores = []
                    if not tel.isdigit() or len(tel) != 10: errores.append("❌ El teléfono debe contener EXACTAMENTE 10 números.")
                    if not nombre or not paterno: errores.append("❌ Nombre y Apellido son obligatorios.")
                        
                    if errores:
                        for e in errores: st.error(e)
                    else:
                        nom_f = limpiar_texto_mayus(nombre)
                        pat_f = limpiar_texto_mayus(paterno)
                        mat_f = limpiar_texto_mayus(materno)
                        mail_f = limpiar_email(email)
                        
                        # Lógica Fiscal Condicional
                        if requiere_factura:
                            rfc_final = rfc.upper()
                            cp_final = cp
                            reg_final = regimen.split(" - ")[0]
                            uso_final = uso.split(" - ")[0]
                            # Guardamos metodo de pago en notas o campo extra si no hay columna
                            nota_fiscal = f"Método SAT: {metodo_pago_sat}"
                        else:
                            rfc_final = "XAXX010101000"
                            cp_final = "N/A"
                            reg_final = "616"
                            uso_final = "S01"
                            nota_fiscal = ""
                        
                        nuevo_id = generar_id_unico(nom_f, pat_f, nacimiento)
                        fecha_reg = get_fecha_mx()
                        tel_fmt = f"{tel[:2]}-{tel[2:6]}-{tel[6:]}"
                        
                        # Guardamos fecha nacimiento como string YYYY-MM-DD para evitar errores de lectura
                        f_nac_str = nacimiento.strftime("%Y-%m-%d")
                        
                        row = [
                            nuevo_id, fecha_reg, nom_f, pat_f, mat_f, tel_fmt, mail_f, 
                            rfc_final, reg_final, uso_final, cp_final, 
                            nota_fiscal, "", "Activo", f_nac_str # Usamos la ultima columna o reutilizamos para fecha nac real
                        ]
                        # NOTA: Asegúrate que en Sheets la columna 15 sea 'fecha_nacimiento' o similar, 
                        # si no, el sistema guardará la fecha en 'ultima_visita' u otra.
                        # Ajustando para mantener estructura 15 cols:
                        # id, fecha, nom, pat, mat, tel, email, rfc, reg, uso, cp, notas(alertas), link, estado, FECHA_NAC
                        
                        sheet_pacientes.append_row(row)
                        st.success(f"✅ Paciente {nom_f} guardado.")
                        time.sleep(1.5); st.rerun()

    # ------------------------------------
    # MÓDULO 3: PLANES
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes de Tratamiento") # CAMBIO DE TÍTULO
        
        try:
            pacientes = sheet_pacientes.get_all_records()
            servicios = pd.DataFrame(sheet_servicios.get_all_records())
            citas_raw = sheet_citas.get_all_records()
            df_finanzas = pd.DataFrame(citas_raw)
        except: 
            st.error("Error cargando base de datos.")
            st.stop()
            
        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes]
        seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
        
        if seleccion_pac != "Buscar...":
            id_p = seleccion_pac.split(" - ")[0]
            nom_p = seleccion_pac.split(" - ")[1]
            
            # --- SEMÁFORO ---
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            if not df_finanzas.empty:
                historial = df_finanzas[df_finanzas['id_paciente'].astype(str) == id_p]
                if not historial.empty:
                    if 'saldo_pendiente' not in historial.columns: historial['saldo_pendiente'] = 0
                    deuda_total = pd.to_numeric(historial['saldo_pendiente'], errors='coerce').fillna(0).sum()
                    col_sem1, col_sem2 = st.columns(2)
                    col_sem1.metric("Deuda Total", f"${deuda_total:,.2f}")
                    if deuda_total > 0: col_sem2.error("🚨 SALDO PENDIENTE")
                    else: col_sem2.success("✅ AL CORRIENTE")
            
            st.markdown("---")
            st.subheader("Nuevo Plan Integral")
            
            c1, c2, c3 = st.columns(3)
            cat_sel = "General"
            trat_sel = ""
            precio_lista_sug = 0.0
            
            if not servicios.empty and 'categoria' in servicios.columns:
                cats = servicios['categoria'].unique()
                cat_sel = c1.selectbox("1. Categoría", cats)
                filt = servicios[servicios['categoria'] == cat_sel]
                trat_sel = c2.selectbox("2. Tratamiento", filt['nombre_tratamiento'].unique())
                item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]
                precio_lista_sug = float(item.get('precio_lista', 0))
            else:
                trat_sel = c2.text_input("Tratamiento Manual")
                precio_lista_sug = c3.number_input("Precio Lista", 0.0)
                
            c3.metric("Precio de Lista Sugerido", f"${precio_lista_sug:,.2f}")
            
            st.markdown("#### 💳 Definición de Cobro")
            col_f1, col_f2, col_f3 = st.columns(3)
            precio_final = col_f1.number_input("Precio Final a Cobrar", value=precio_lista_sug, min_value=0.0, format="%.2f")
            abono = col_f2.number_input("Abono Inicial", min_value=0.0, format="%.2f")
            
            saldo_real = precio_final - abono
            col_f3.metric("Saldo Pendiente (Deuda)", f"${saldo_real:,.2f}", delta_color="inverse")

            with st.form("form_plan_final"):
                col_d1, col_d2, col_d3 = st.columns(3)
                doctor = col_d1.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                diente = col_d2.number_input("Diente (ISO)", min_value=0, max_value=85)
                metodo = col_d3.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia", "N/A (Garantía)"])
                
                num_citas = st.number_input("Número de Sesiones Estimadas", min_value=1, value=1)
                
                st.markdown("---")
                agendar_ahora = st.checkbox("📅 ¿Agendar Primera Sesión/Cita Ahora?")
                
                f_cita_prox = st.date_input("Fecha de Cita", datetime.now(TZ_MX))
                h_cita_prox = st.selectbox("Hora Cita", generar_slots_tiempo())
                
                if st.form_submit_button("💾 REGISTRAR PLAN Y CITA"):
                    if precio_final > precio_lista_sug:
                        pct = 0; nota = f"Sobrecosto: ${precio_final - precio_lista_sug}"
                    else:
                        diff = precio_lista_sug - precio_final
                        pct = (diff/precio_lista_sug*100) if precio_lista_sug > 0 else 0
                        nota = f"Sesiones Est: {num_citas}"

                    fecha_pago = get_fecha_mx() if abono > 0 else ""
                    estatus = "Pagado" if saldo_real <= 0 else "Pendiente"
                    
                    row_fin = [
                        int(time.time()), str(get_fecha_mx()), get_hora_mx(), id_p, nom_p,
                        cat_sel, trat_sel, diente, doctor,
                        precio_lista_sug, precio_final, pct, "No", 0, (precio_final*0.4),
                        metodo, estatus, "No", nota,
                        abono, saldo_real, fecha_pago
                    ]
                    sheet_citas.append_row(row_fin)
                    
                    msg_extra = ""
                    if agendar_ahora:
                        row_cita = [
                            int(time.time())+1, str(f_cita_prox), h_cita_prox, id_p, nom_p,
                            "Seguimiento", f"{trat_sel} (Sesión 1)", diente, doctor,
                            0, 0, 0, "No", 0, 0, "N/A", "N/A", "No", "Cita generada desde Plan", 0, 0, ""
                        ]
                        sheet_citas.append_row(row_cita)
                        msg_extra = f" y Cita Agendada para el {f_cita_prox}"
                    
                    st.success(f"✅ Plan Registrado{msg_extra}")
                    time.sleep(2); st.rerun()

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

if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
