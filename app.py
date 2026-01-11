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
        
        /* Estilos para validación */
        .error-msg { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px; border: 1px solid #f5c6cb; margin-bottom: 10px; }
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
    # Solo acepta numeros
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
    # MÓDULO 1: AGENDA (PACIENTES NUEVOS)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Calendario")
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            
            st.markdown("---")
            
            # Pestañas para tipos de Citas
            tab_reg, tab_new = st.tabs(["Paciente Registrado", "Prospecto/Nuevo"])
            
            # CITA PACIENTE REGISTRADO
            with tab_reg:
                with st.form("cita_registrada", clear_on_submit=True):
                    pacientes_raw = sheet_pacientes.get_all_records()
                    lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    
                    p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    h_sel = st.selectbox("Hora", generar_slots_tiempo(), key="h_reg")
                    m_sel = st.text_input("Motivo", "Revisión / Continuación")
                    d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"], key="d_reg")
                    
                    if st.form_submit_button("Agendar Paciente"):
                        if p_sel != "Seleccionar...":
                            id_p = p_sel.split(" - ")[0]
                            nom_p = p_sel.split(" - ")[1]
                            row = [int(time.time()), str(fecha_ver), h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", ""]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita Agendada")
                            time.sleep(1); st.rerun()
                        else: st.error("Seleccione un paciente")

            # CITA PROSPECTO (SOLUCIÓN A TU PROBLEMA)
            with tab_new:
                st.caption("Usar para pacientes que llaman por primera vez (Revisión $100). No crea expediente completo aún.")
                with st.form("cita_prospecto", clear_on_submit=True):
                    nombre_pros = st.text_input("Nombre Completo")
                    tel_pros = st.text_input("Teléfono de Contacto")
                    hora_pros = st.selectbox("Hora", generar_slots_tiempo(), key="h_pros")
                    motivo_pros = st.text_input("Motivo", "Revisión (Primera Vez)")
                    precio_pros = st.number_input("Costo Estimado", value=100.0)
                    doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"], key="d_pros")
                    
                    if st.form_submit_button("Agendar Prospecto"):
                        if nombre_pros and tel_pros:
                            # ID Temporal
                            id_temp = f"PROSPECTO-{int(time.time())}"
                            # id, fecha, hora, id_pac, nom, cat, trat, diente, doc, precio...
                            row = [
                                int(time.time()), str(fecha_ver), hora_pros, id_temp, nombre_pros, 
                                "Primera Vez", motivo_pros, "", doc_pros, 
                                precio_pros, precio_pros, 0, "No", 0, precio_pros, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}"
                            ]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita de Prospecto Agendada")
                            time.sleep(1); st.rerun()
                        else:
                            st.error("Nombre y Teléfono obligatorios")

        # VISUALIZACIÓN DE AGENDA
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
                                # Distinción visual si es prospecto
                                es_prospecto = "PROSPECTO" in str(r['id_paciente'])
                                color_borde = "#FF5722" if es_prospecto else ("#28a745" if r.get('estado_pago') == "Pagado" else "#D4AF37")
                                etiqueta = "🆕 NUEVO" if es_prospecto else "👤 PACIENTE"
                                
                                st.markdown(f"""
                                <div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color_borde}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;">
                                    <div style="display:flex; justify-content:space-between;">
                                        <span style="font-weight:bold; color:#002B5B;">{slot} | {r['nombre_paciente']}</span>
                                        <span style="background-color:#eee; padding:2px 6px; border-radius:4px; font-size:0.7em;">{etiqueta}</span>
                                    </div>
                                    <div style="color:#555; font-size:0.9em;">
                                        {r['tratamiento']} (${r['precio_final']}) - {r['doctor_atendio']}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
            except:
                st.warning("No se pudo leer la base de citas.")

    # ------------------------------------
    # MÓDULO 2: PACIENTES (VALIDACIÓN ESTRICTA)
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
                        # Calcular edad
                        try:
                            f_obj = datetime.strptime(p_data['fecha_nacimiento'], "%Y-%m-%d").date() # Asume YYYY-MM-DD
                            edad, tipo_pac = calcular_edad_completa(f_obj)
                        except:
                            edad, tipo_pac = "N/A", ""

                        st.markdown(f"""
                        <div class="royal-card">
                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3>
                            <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span><br><br>
                            <b>Tel:</b> {p_data['telefono']}
                        </div>
                        """, unsafe_allow_html=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            
            # NOTA: No usamos st.form aquí porque queremos validación en tiempo real o checkbox interactivo
            # Pero para el submit final si es mejor encapsular lo que se pueda.
            # Haremos validación manual al presionar botón.
            
            c_nom, c_pat, c_mat = st.columns(3)
            nombre = c_nom.text_input("Nombre(s)")
            paterno = c_pat.text_input("Apellido Paterno")
            materno = c_mat.text_input("Apellido Materno")
            
            c_nac, c_tel, c_mail = st.columns(3)
            nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
            
            # Feedback Visual Edad
            edad_calc, tipo_calc = calcular_edad_completa(nacimiento)
            c_nac.caption(f"Edad: {edad_calc} años ({tipo_calc})")
            
            tel = c_tel.text_input("Teléfono (10 dígitos)")
            email = c_mail.text_input("Email")
            
            st.markdown("---")
            # LOGICA FISCAL CONDICIONAL
            requiere_factura = st.checkbox("¿Requiere Factura?")
            
            if requiere_factura:
                st.markdown("**Datos Fiscales**")
                c_f1, c_f2 = st.columns(2)
                rfc = c_f1.text_input("RFC")
                cp = c_f2.text_input("C.P.")
                regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                uso = st.selectbox("Uso CFDI", get_usos_cfdi())
            else:
                rfc = "XAXX010101000"
                cp = "N/A"
                regimen = "616 - Sin obligaciones fiscales"
                uso = "S01 - Sin efectos fiscales"
            
            if st.button("💾 GUARDAR PACIENTE", type="primary"):
                errores = []
                
                # 1. Validación Estricta Teléfono
                tel_limpio = formatear_telefono(tel)
                if len(tel_limpio) != 10:
                    errores.append(f"❌ El teléfono debe tener exactamente 10 dígitos numéricos. Ingresaste {len(tel_limpio)}.")
                
                if not nombre or not paterno:
                    errores.append("❌ Nombre y Apellido Paterno son obligatorios.")
                
                if errores:
                    for e in errores: st.error(e)
                else:
                    # Guardar si todo bien
                    nuevo_id = generar_id_unico(nombre, paterno, nacimiento)
                    fecha_reg = get_fecha_mx()
                    tel_final = f"{tel_limpio[:2]}-{tel_limpio[2:6]}-{tel_limpio[6:]}"
                    
                    row = [
                        nuevo_id, fecha_reg, nombre, paterno, materno, tel_final, email, 
                        rfc, regimen.split(" - ")[0], uso.split(" - ")[0], cp, 
                        f"Nac: {nacimiento}", "", "Activo", ""
                    ]
                    try:
                        sheet_pacientes.append_row(row)
                        st.success(f"✅ Paciente guardado correctamente.")
                        st.balloons()
                        time.sleep(2); st.rerun()
                    except Exception as ex:
                        st.error(f"Error Google Sheets: {ex}")

    # ------------------------------------
    # MÓDULO 3: TRATAMIENTOS (CASCADA Y MATH)
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Cotizador Profesional")
        
        pacientes_raw = sheet_pacientes.get_all_records()
        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
        seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
        
        if seleccion_pac != "Buscar...":
            st.markdown("---")
            
            # Cargar Servicios
            try:
                servicios_data = sheet_servicios.get_all_records()
                df_servicios = pd.DataFrame(servicios_data)
            except: df_servicios = pd.DataFrame()

            # --- SELECTORES (FUERA DE FORM PARA INTERACTIVIDAD) ---
            col_sel1, col_sel2, col_sel3 = st.columns(3)
            
            categoria_sel = "General"
            tratamiento_sel = ""
            precio_lista_val = 0.0
            
            if not df_servicios.empty and 'categoria' in df_servicios.columns:
                cats = df_servicios['categoria'].unique()
                categoria_sel = col_sel1.selectbox("1. Categoría", cats)
                
                # Filtrar Tratamientos basado en Categoria
                df_filt = df_servicios[df_servicios['categoria'] == categoria_sel]
                trats = df_filt['nombre_tratamiento'].unique()
                tratamiento_sel = col_sel2.selectbox("2. Tratamiento", trats)
                
                # Obtener Precio
                item = df_filt[df_filt['nombre_tratamiento'] == tratamiento_sel].iloc[0]
                precio_lista_val = float(item.get('precio_lista', 0))
            else:
                tratamiento_sel = col_sel2.text_input("Tratamiento Manual")
                precio_lista_val = col_sel3.number_input("Precio Lista", 0.0)

            # --- FORMULARIO FINANCIERO (CON MATH) ---
            # Mostramos el precio de lista bloqueado (solo lectura)
            col_sel3.metric("Precio de Lista", f"${precio_lista_val:,.2f}")
            
            st.markdown("#### 💳 Detalles Financieros")
            
            # Usamos columnas para simular tabla profesional
            c_fin1, c_fin2, c_fin3 = st.columns(3)
            
            precio_final = c_fin1.number_input("Precio Final a Cobrar", value=precio_lista_val, step=50.0)
            
            # Cálculo Descuento
            descuento_monto = precio_lista_val - precio_final
            pct_desc = (descuento_monto / precio_lista_val * 100) if precio_lista_val > 0 else 0
            
            c_fin2.metric("Descuento Aplicado", f"${descuento_monto:,.2f}", f"-{pct_desc:.1f}%")
            
            abono = c_fin3.number_input("Abono Inicial", min_value=0.0, max_value=precio_final)
            
            # Cálculo Pendiente
            pendiente = precio_final - abono
            estatus_pago = "Pagado" if pendiente <= 0 else "Pendiente"
            
            st.info(f"💵 **Por Cobrar:** ${pendiente:,.2f} | **Estatus:** {estatus_pago}")
            
            c_doc, c_met = st.columns(2)
            doctor = c_doc.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
            metodo = c_met.selectbox("Método de Pago", ["Efectivo", "Tarjeta Crédito/Débito", "Transferencia", "Pendiente Total"])
            
            diente = st.number_input("Diente (ISO)", 0)
            
            if st.button("💾 REGISTRAR PLAN Y PAGO"):
                id_p = seleccion_pac.split(" - ")[0]
                nom_p = seleccion_pac.split(" - ")[1]
                
                # Guardar
                row = [
                    int(time.time()), str(get_fecha_mx()), get_hora_mx(), id_p, nom_p,
                    categoria_sel, tratamiento_sel, diente, doctor,
                    precio_lista_val, precio_final, pct_desc, "No", 0, (precio_final * 0.4), # Utilidad estim
                    metodo, estatus_pago, "No", f"Saldo Pendiente: ${pendiente}"
                ]
                sheet_citas.append_row(row)
                st.success("Plan registrado exitosamente.")
                time.sleep(1.5); st.rerun()

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
