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
# 1. CONFIGURACIÓN Y ESTILO ROYAL (MEJORADO)
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')

def cargar_estilo_royal():
    st.markdown("""
        <style>
        /* General */
        .stApp { background-color: #F4F6F6; }
        h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        
        /* Botones */
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; border-radius: 8px; transition: all 0.3s; }
        .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transform: translateY(-2px); }
        
        /* Inputs */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        
        /* TARJETAS (NUEVO UI/UX) */
        .card-paciente {
            background-color: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 6px solid #D4AF37; margin-bottom: 15px;
        }
        .card-cita {
            background-color: white; padding: 15px; border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 5px solid #002B5B; margin-bottom: 10px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .card-prospecto {
            background-color: #FFF8E1; padding: 15px; border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 5px solid #FF9800; margin-bottom: 10px;
        }
        
        /* Semáforos Financieros */
        .semaforo-verde { color: #155724; background-color: #D4EDDA; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.9em; }
        .semaforo-rojo { color: #721c24; background-color: #F8D7DA; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.9em; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB
# ==========================================
@st.cache_resource(ttl=60)
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
# 3. HELPERS & SANITIZACIÓN (MEJORADO)
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def format_date_latino(date_obj):
    return date_obj.strftime("%d/%m/%Y")

def parse_date_latino(date_str):
    if not date_str: return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y"):
        try: return datetime.strptime(str(date_str), fmt).date()
        except: continue
    return None

def limpiar_texto_mayus(texto):
    if not texto: return ""
    remplaces = {'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U', 'á':'A', 'é':'E', 'í':'I', 'ó':'O', 'ú':'U'}
    texto = texto.upper()
    for k, v in remplaces.items(): texto = texto.replace(k, v)
    return texto

def limpiar_email(texto):
    if not texto: return ""
    return texto.lower().strip()

# --- FIX: CÁLCULO DE EDAD ROBUSTO ---
def calcular_edad_completa(nacimiento_input):
    if not nacimiento_input: return "N/A", ""
    try:
        hoy = datetime.now().date()
        nacimiento = parse_date_latino(nacimiento_input)
        if nacimiento:
            edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
            tipo = "👶 MENOR" if edad < 18 else "🧑 ADULTO"
            return edad, tipo
    except: pass
    return "Error", "Fecha Inválida"

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
    hora_actual = datetime.strptime("09:00", "%H:%M")
    hora_fin = datetime.strptime("19:00", "%H:%M")
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
        st.markdown("""<div style="background-color: #002B5B; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.2);">
        <h1 style="color: #D4AF37 !important; margin:0;">ROYAL DENTAL</h1>
        <p style="color: white;">Manager ERP v2.0</p>
        </div><br>""", unsafe_allow_html=True)
        
        tipo = st.selectbox("Seleccione Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña de Acceso", type="password")
        
        if st.button("INGRESAR AL SISTEMA"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("⛔ Credenciales Incorrectas")

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3004/3004458.png", width=80)
        st.markdown("### 🏥 Royal Dental")
        st.caption(f"📅 {get_fecha_mx()}")
        st.markdown("---")
        menu = st.radio("Navegación", 
            ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes & Finanzas", "4. Control Asistencia"])
        st.markdown("---")
        if st.button("🔓 Cerrar Sesión"):
            st.session_state.perfil = None; st.rerun()

    # ------------------------------------
    # MÓDULO 1: AGENDA (VISUALMENTE MEJORADA)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        # --- BUSCADOR GLOBAL ---
        with st.expander("🔍 BUSCADOR DE HISTORIAL (Pacientes/Prospectos)", expanded=False):
            q_cita = st.text_input("Escribe el nombre del paciente:")
            if q_cita:
                try:
                    all_citas = sheet_citas.get_all_records()
                    df_all = pd.DataFrame(all_citas)
                    if not df_all.empty:
                        df_res = df_all[df_all['nombre_paciente'].str.contains(q_cita, case=False, na=False)]
                        if not df_res.empty:
                            st.dataframe(df_res[['fecha', 'hora', 'nombre_paciente', 'tratamiento', 'doctor_atendio', 'estado_pago']], use_container_width=True)
                        else: st.warning("No se encontraron coincidencias.")
                except Exception as e: st.error(f"Error: {e}")

        col_cal1, col_cal2 = st.columns([1.2, 2.8])
        
        with col_cal1:
            st.markdown("### 🛠️ Panel de Control")
            fecha_ver_obj = st.date_input("Ver Agenda del día:", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            st.markdown("---")
            st.caption("Acciones Rápidas")
            with st.popover("➕ Nueva Cita (Registrado)"):
                with st.form("cita_registrada"):
                    pacientes_raw = sheet_pacientes.get_all_records()
                    lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    h_sel = st.selectbox("Hora", generar_slots_tiempo())
                    m_sel = st.text_input("Motivo", "Revisión")
                    d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Agendar Cita"):
                        if p_sel != "Seleccionar...":
                            id_p = p_sel.split(" - ")[0]
                            nom_p = p_sel.split(" - ")[1]
                            row = [int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "", 0, 0, ""]
                            sheet_citas.append_row(row)
                            st.toast("✅ Cita Agendada Exitosamente")
                            time.sleep(1); st.rerun()

            with st.popover("👤 Nuevo Prospecto (1ra Vez)"):
                with st.form("cita_prospecto"):
                    nombre_pros = st.text_input("Nombre Completo")
                    tel_pros = st.text_input("Teléfono", max_chars=10)
                    hora_pros = st.selectbox("Hora Cita", generar_slots_tiempo())
                    motivo_pros = st.text_input("Motivo", "Valoración")
                    precio_pros = st.number_input("Costo Consulta", value=200.0)
                    doc_pros = st.selectbox("Doctor Asignado", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Guardar Prospecto"):
                        if nombre_pros:
                            id_temp = f"PROSPECTO-{int(time.time())}"
                            row = [int(time.time()), fecha_ver_str, hora_pros, id_temp, limpiar_texto_mayus(nombre_pros), "Primera Vez", motivo_pros, "", doc_pros, precio_pros, precio_pros, 0, "No", 0, 0, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}", 0, precio_pros, ""]
                            sheet_citas.append_row(row)
                            st.toast("✅ Prospecto Agendado")
                            time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"### 📆 Calendario: {fecha_ver_str}")
            # Visualización tipo Calendario/Tarjetas
            citas_data = sheet_citas.get_all_records()
            df_c = pd.DataFrame(citas_data)
            
            slots = generar_slots_tiempo()
            
            if not df_c.empty:
                df_c['fecha'] = df_c['fecha'].astype(str)
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
            else: df_dia = pd.DataFrame()

            for slot in slots:
                ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)] if not df_dia.empty else pd.DataFrame()
                
                if ocupado.empty:
                    st.markdown(f"""
                        <div style="padding:10px; margin-bottom:8px; border-bottom:1px dashed #ddd; color:#aaa; display:flex;">
                            <b style="width:70px;">{slot}</b> <span>Disponible</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    for _, r in ocupado.iterrows():
                        es_prospecto = "PROSPECTO" in str(r['id_paciente'])
                        css_class = "card-prospecto" if es_prospecto else "card-cita"
                        icono = "👤❓" if es_prospecto else "🦷"
                        
                        st.markdown(f"""
                        <div class="{css_class}">
                            <div>
                                <strong style="font-size:1.2em; color:#002B5B;">{slot}</strong><br>
                                <span style="color:#666;">{icono} {r['nombre_paciente']}</span>
                            </div>
                            <div style="text-align:right;">
                                <b>{r['tratamiento']}</b><br>
                                <small>{r['doctor_atendio']}</small>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # ------------------------------------
    # MÓDULO 2: PACIENTES (SEXO Y CARDS)
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico")
        
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)", "✏️ EDITAR"])
        
        # --- PESTAÑA BUSCAR (CON CARDS) ---
        with tab_b:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw: st.info("Base de datos vacía.")
            else:
                busqueda = st.text_input("🔍 Buscar por Nombre:", placeholder="Escribe para filtrar...")
                
                for p in pacientes_raw:
                    nombre_completo = f"{p['nombre']} {p['apellido_paterno']} {p['apellido_materno']}"
                    if busqueda.lower() in nombre_completo.lower():
                        # Lógica de Iconos Sexo
                        sexo_icon = "👩" if str(p.get('sexo','')).startswith("F") else "👨"
                        f_nac = p.get('fecha_nacimiento', '')
                        edad, tipo_pac = calcular_edad_completa(f_nac)
                        rfc_val = p.get('rfc', 'N/A')
                        
                        # Card HTML
                        st.markdown(f"""
                        <div class="card-paciente">
                            <h3 style="margin:0;">{sexo_icon} {nombre_completo}</h3>
                            <span class="semaforo-verde">{tipo_pac}: {edad} Años</span>
                            <hr style="margin:10px 0;">
                            <div style="display:flex; justify-content:space-between;">
                                <span>📞 <b>Tel:</b> {p['telefono']}</span>
                                <span>📧 <b>Email:</b> {p['email']}</span>
                                <span>🏛️ <b>RFC:</b> {rfc_val}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # --- PESTAÑA ALTA (CON SEXO) ---
        with tab_n:
            st.subheader("Alta de Paciente")
            requiere_factura = st.checkbox("¿Requiere Factura?", key="chk_alta")
            
            with st.form("alta_paciente_v2", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)")
                paterno = c2.text_input("Apellido Paterno")
                materno = c3.text_input("Apellido Materno")
                
                c4, c5, c6 = st.columns(3)
                sexo = c4.selectbox("Sexo", ["Masculino", "Femenino"])
                nacimiento = c5.date_input("Fecha Nacimiento", min_value=datetime(1930,1,1), max_value=datetime.now(), format="DD/MM/YYYY")
                tel = c6.text_input("Móvil (10 dígitos)", max_chars=10)
                email = st.text_input("Email")

                # Campos Fiscales Condicionales
                if requiere_factura:
                    st.info("📝 Datos Fiscales")
                    fc1, fc2 = st.columns(2)
                    rfc = fc1.text_input("RFC", max_chars=13)
                    cp = fc2.text_input("Código Postal", max_chars=5)
                    regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                    uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                    nota_fiscal = st.text_input("Nota Fiscal / Método Pago SAT", "PUE - Una sola exhibición")
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    if nombre and paterno and len(tel)==10:
                        # Procesar Datos
                        nom_f = limpiar_texto_mayus(nombre)
                        pat_f = limpiar_texto_mayus(paterno)
                        mat_f = limpiar_texto_mayus(materno)
                        f_nac_str = format_date_latino(nacimiento)
                        
                        if requiere_factura:
                            rfc_f = rfc.upper()
                            reg_f = regimen.split(" - ")[0]
                            uso_f = uso.split(" - ")[0]
                            cp_f = cp
                            nota_f = nota_fiscal
                        else:
                            rfc_f, reg_f, uso_f, cp_f, nota_f = "XAXX010101000", "616", "S01", "N/A", ""

                        new_id = generar_id_unico(nom_f, pat_f, nacimiento)
                        # ORDEN EXACTO GOOGLE SHEETS:
                        # id, fecha_reg, nom, pat, mat, tel, email, rfc, reg, uso, cp, nota, SEXO, estado, nacimiento
                        row = [new_id, get_fecha_mx(), nom_f, pat_f, mat_f, formatear_telefono(tel), limpiar_email(email),
                               rfc_f, reg_f, uso_f, cp_f, nota_f, sexo, "Activo", f_nac_str]
                        
                        sheet_pacientes.append_row(row)
                        st.success(f"✅ Paciente {nom_f} registrado con éxito.")
                        time.sleep(1.5); st.rerun()
                    else:
                        st.error("Faltan datos obligatorios (Nombre, Apellido, Teléfono 10 dígitos)")

        # --- PESTAÑA EDITAR (CON BOTÓN FISCAL) ---
        with tab_e:
            st.subheader("✏️ Modificar / Completar Datos")
            lista_edit = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
            sel_edit = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_edit)
            
            if sel_edit != "Buscar...":
                id_target = sel_edit.split(" - ")[0]
                p_edit = next((p for p in pacientes_raw if str(p['id_paciente']) == id_target), None)
                
                if p_edit:
                    with st.form("form_editar"):
                        col_e1, col_e2 = st.columns(2)
                        e_nom = col_e1.text_input("Nombre", p_edit['nombre'])
                        e_pat = col_e2.text_input("Apellido Paterno", p_edit['apellido_paterno'])
                        e_tel = st.text_input("Teléfono", p_edit['telefono'])
                        
                        # --- MEJORA: AGREGAR FISCALES SI NO TIENE ---
                        rfc_actual = p_edit.get('rfc', '')
                        agregar_fiscal = False
                        
                        if rfc_actual == "XAXX010101000" or rfc_actual == "":
                            st.warning("Este paciente no tiene datos fiscales personalizados.")
                            agregar_fiscal = st.checkbox("📝 Agregar Datos Fiscales Ahora")
                        
                        e_rfc_new = rfc_actual
                        e_cp_new = p_edit.get('cp', '')
                        
                        if agregar_fiscal or (rfc_actual != "XAXX010101000" and rfc_actual != ""):
                            col_f1, col_f2 = st.columns(2)
                            e_rfc_new = col_f1.text_input("RFC", p_edit.get('rfc', ''))
                            e_cp_new = col_f2.text_input("C.P.", p_edit.get('cp', ''))

                        if st.form_submit_button("ACTUALIZAR"):
                            cell = sheet_pacientes.find(id_target)
                            row_idx = cell.row
                            # Actualizar celdas específicas
                            sheet_pacientes.update_cell(row_idx, 3, e_nom) # Nombre
                            sheet_pacientes.update_cell(row_idx, 4, e_pat) # Paterno
                            sheet_pacientes.update_cell(row_idx, 6, formatear_telefono(e_tel)) # Tel
                            if e_rfc_new != rfc_actual:
                                sheet_pacientes.update_cell(row_idx, 8, e_rfc_new.upper()) # RFC
                                sheet_pacientes.update_cell(row_idx, 11, e_cp_new) # CP
                            st.success("✅ Registro actualizado.")
                            time.sleep(1); st.rerun()

    # ------------------------------------
    # MÓDULO 3: FINANZAS (CON COBRANZA)
    # ------------------------------------
    elif menu == "3. Planes & Finanzas":
        st.title("💰 Finanzas & Cobranza")
        
        tab_plan, tab_abono = st.tabs(["🦷 NUEVO PLAN (PRESUPUESTO)", "💳 CAJA (ABONAR A DEUDA)"])

        pacientes = sheet_pacientes.get_all_records()
        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes]
        
        # --- SUBMÓDULO DE COBRANZA (NUEVO) ---
        with tab_abono:
            st.subheader("Registro de Pagos (Sin Cita Médica)")
            st.info("Utilice esta sección cuando el paciente viene solo a pagar una deuda anterior.")
            
            p_abono = st.selectbox("Seleccionar Deudor:", ["Buscar..."] + lista_pac, key="abono_sel")
            
            if p_abono != "Buscar...":
                id_p_abono = p_abono.split(" - ")[0]
                citas_raw = sheet_citas.get_all_records()
                df_fin = pd.DataFrame(citas_raw)
                
                # Filtrar deudas pendientes
                if not df_fin.empty:
                    # Asegurar tipos numéricos
                    df_fin['saldo_pendiente'] = pd.to_numeric(df_fin['saldo_pendiente'], errors='coerce').fillna(0)
                    df_fin['monto_pagado'] = pd.to_numeric(df_fin['monto_pagado'], errors='coerce').fillna(0)
                    
                    deudas = df_fin[(df_fin['id_paciente'].astype(str) == id_p_abono) & (df_fin['saldo_pendiente'] > 0)]
                    
                    if not deudas.empty:
                        st.write(f"Deudas encontradas: {len(deudas)}")
                        
                        opciones_deuda = []
                        for idx, row in deudas.iterrows():
                            txt = f"Fecha: {row['fecha']} | Tx: {row['tratamiento']} | Debe: ${row['saldo_pendiente']}"
                            opciones_deuda.append((idx, txt)) # Guardamos el index original del DF
                        
                        seleccion_deuda = st.selectbox("Seleccione la deuda a abonar:", [x[1] for x in opciones_deuda])
                        
                        # Recuperar el índice seleccionado
                        idx_sel = next(x[0] for x in opciones_deuda if x[1] == seleccion_deuda)
                        row_sel = deudas.loc[idx_sel]
                        
                        monto_pendiente = float(row_sel['saldo_pendiente'])
                        
                        with st.form("form_abono"):
                            st.metric("Saldo Actual de esta nota", f"${monto_pendiente:,.2f}")
                            abono_input = st.number_input("Monto a Abonar HOY", min_value=1.0, max_value=monto_pendiente)
                            metodo_abono = st.selectbox("Forma de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                            
                            if st.form_submit_button("💵 REGISTRAR PAGO"):
                                # Calcular nuevos valores
                                nuevo_pagado = float(row_sel['monto_pagado']) + abono_input
                                nuevo_pendiente = monto_pendiente - abono_input
                                nuevo_estado = "Pagado" if nuevo_pendiente <= 0 else "Pendiente"
                                nueva_fecha_pago = get_fecha_mx()
                                
                                # Encontrar la fila en Google Sheets
                                # Usamos el ID de cita (columna 1) para mayor precisión si existe, si no, combinación fecha/hora
                                # Aquí asumimos búsqueda por timestamp 'id' que es Columna A (1)
                                try:
                                    cell_find = sheet_citas.find(str(row_sel['id']))
                                    r_idx = cell_find.row
                                    
                                    # Actualizar columnas (Indices basados en estructura Hoja Citas)
                                    # monto_pagado (T - 20), saldo_pendiente (U - 21), fecha_pago (V - 22), estado_pago (Q - 17)
                                    # REVISAR ESTRUCTURA EN SECCIÓN 1B DEL PROMPT:
                                    # A=1... monto_pagado=20, saldo_pendiente=21, fecha_pago=22
                                    # estado_pago=17
                                    
                                    sheet_citas.update_cell(r_idx, 20, nuevo_pagado)
                                    sheet_citas.update_cell(r_idx, 21, nuevo_pendiente)
                                    sheet_citas.update_cell(r_idx, 22, nueva_fecha_pago)
                                    sheet_citas.update_cell(r_idx, 17, nuevo_estado)
                                    
                                    st.balloons()
                                    st.success(f"✅ Abono de ${abono_input} registrado correctamente.")
                                    time.sleep(2); st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar BD: {e}")
                    else:
                        st.success("🎉 Este paciente NO tiene deudas pendientes.")

        # --- PLAN DE TRATAMIENTO (CON CAMPO PARA AGENDAR) ---
        with tab_plan:
            st.subheader("Nuevo Presupuesto")
            seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac, key="plan_sel")
            
            if seleccion_pac != "Buscar...":
                id_p = seleccion_pac.split(" - ")[0]
                nom_p = seleccion_pac.split(" - ")[1]
                
                c1, c2, c3 = st.columns(3)
                # Cargar servicios si existen
                try:
                    servicios = pd.DataFrame(sheet_servicios.get_all_records())
                    if not servicios.empty:
                        cat = c1.selectbox("Categoría", servicios['categoria'].unique())
                        trat = c2.selectbox("Tratamiento", servicios[servicios['categoria']==cat]['nombre_tratamiento'].unique())
                        p_list = float(servicios[servicios['nombre_tratamiento']==trat]['precio_lista'].values[0])
                    else:
                        trat = c2.text_input("Tratamiento")
                        p_list = c3.number_input("Precio Lista", 0.0)
                except:
                     trat = c2.text_input("Tratamiento")
                     p_list = c3.number_input("Precio Lista", 0.0)

                with st.form("form_plan"):
                    col_p1, col_p2, col_p3 = st.columns(3)
                    p_final = col_p1.number_input("Precio Final", value=p_list)
                    p_abono = col_p2.number_input("Anticipo Hoy", min_value=0.0)
                    doctor = col_p3.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    st.markdown(f"**Saldo a Crédito:** ${p_final - p_abono:,.2f}")
                    
                    agendar_cita = st.checkbox("📅 ¿Agendar la cita de este tratamiento de una vez?")
                    if agendar_cita:
                        fc_cita = st.date_input("Fecha Cita", datetime.now(TZ_MX))
                        hc_cita = st.selectbox("Hora Cita", generar_slots_tiempo(), key="h_plan")

                    if st.form_submit_button("💾 CREAR PLAN"):
                        saldo = p_final - p_abono
                        estatus = "Pagado" if saldo <= 0 else "Pendiente"
                        row_fin = [
                            int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, 
                            "Plan", trat, 0, doctor, p_list, p_final, 0, "No", 0, 0, 
                            "Efectivo", estatus, "No", "Plan Generado", p_abono, saldo, get_fecha_mx()
                        ]
                        sheet_citas.append_row(row_fin)
                        
                        if agendar_cita:
                            row_cita = [
                                int(time.time())+1, format_date_latino(fc_cita), hc_cita, id_p, nom_p,
                                "Tratamiento", trat, 0, doctor, 0,0,0,"No",0,0,"N/A","N/A","No","",0,0,""
                            ]
                            sheet_citas.append_row(row_cita)
                            st.success("Plan financiero y Cita guardados.")
                        else:
                            st.success("Plan financiero guardado (Solo deuda).")
                        time.sleep(2); st.rerun()

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        col1, col2 = st.columns([1,3])
        with col1:
            st.markdown("""<div style="background-color:white; padding:20px; border-radius:10px; text-align:center; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <h3>Dr. Emmanuel</h3>
            <p>Control de Horario</p>
            </div>""", unsafe_allow_html=True)
            
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
        st.info("Vista Administrativa en Construcción")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
