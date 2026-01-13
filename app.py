import streamlit as st
import pandas as pd
import sqlite3
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
        
        /* Ocultar elementos default */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. MOTOR DE BASE DE DATOS (SQLITE)
# ==========================================
DB_FILE = "royal_dental_db.sqlite"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla Pacientes
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, extra1 TEXT, estado TEXT, fecha_nacimiento TEXT
    )''')
    
    # Tabla Citas (Finanzas y Agenda)
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL
    )''')
    
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, 
        hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT
    )''')
    
    # Tabla Servicios (Catálogo)
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (
        categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL
    )''')
    
    conn.commit()
    conn.close()

def seed_data():
    """Carga los tratamientos dentales por defecto si la tabla está vacía"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        tratamientos = [
            ("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0),
            ("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0),
            ("Preventiva", "Sellador de Fosetas y Fisuras", 400.0, 0.0),
            ("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0),
            ("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0),
            ("Operatoria", "Reconstrucción de Muñón", 1500.0, 0.0),
            ("Operatoria", "Curación Temporal (Cavit)", 300.0, 0.0),
            ("Cirugía", "Extracción Simple", 900.0, 0.0),
            ("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0),
            ("Cirugía", "Drenaje de Absceso", 800.0, 0.0),
            ("Endodoncia", "Endodoncia Anterior (1 conducto)", 2800.0, 0.0),
            ("Endodoncia", "Endodoncia Premolar (2 conductos)", 3200.0, 0.0),
            ("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0),
            ("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0),
            ("Prótesis Fija", "Corona Metal-Porcelana", 3500.0, 600.0),
            ("Prótesis Fija", "Incrustación Estética", 3800.0, 700.0),
            ("Prótesis Fija", "Carilla de Porcelana", 5500.0, 1100.0),
            ("Prótesis Fija", "Poste de Fibra de Vidrio", 1200.0, 0.0),
            ("Prótesis Removible", "Placa Total (Acrílico) - Una arcada", 6000.0, 1200.0),
            ("Prótesis Removible", "Prótesis Flexible (Valplast) - Unilateral", 4500.0, 900.0),
            ("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0),
            ("Estética", "Blanqueamiento (Guardas en casa)", 2500.0, 500.0),
            ("Ortodoncia", "Pago Inicial (Brackets Metálicos)", 4000.0, 1500.0),
            ("Ortodoncia", "Mensualidad Ortodoncia", 700.0, 0.0),
            ("Ortodoncia", "Recolocación de Bracket (Reposición)", 200.0, 0.0),
            ("Pediatría", "Pulpotomía", 1500.0, 0.0),
            ("Pediatría", "Corona Acero-Cromo", 1800.0, 0.0),
            ("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0)
        ]
        c.executemany("INSERT INTO servicios VALUES (?,?,?,?)", tratamientos)
        conn.commit()
    conn.close()

# Inicialización
init_db()
seed_data()

# ==========================================
# 3. HELPERS
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def limpiar_texto_mayus(texto):
    if not texto: return ""
    remplaces = {'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U', 'á':'A', 'é':'E', 'í':'I', 'ó':'O', 'ú':'U'}
    texto = texto.upper()
    for k, v in remplaces.items(): texto = texto.replace(k, v)
    return texto

def limpiar_email(texto): return texto.lower().strip() if texto else ""

def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    # Intenta parsear la fecha, si falla devuelve N/A
    try:
        nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date()
    except:
        return "N/A", ""
        
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
    except: return f"P-{int(time.time())}"

def formatear_telefono(numero): return re.sub(r'\D', '', str(numero))

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("20:00", "%H:%M")
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
    conn = get_db_connection()
    c = conn.cursor()
    hoy = get_fecha_mx()
    hora_actual = get_hora_mx()
    
    try:
        if tipo == "Entrada":
            c.execute("SELECT * FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            if c.fetchone(): return False, "Ya tienes una sesión abierta."
            
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, hora_salida, horas_totales, estado) VALUES (?,?,?,?,?,?)",
                      (hoy, doctor, hora_actual, "", 0, "Pendiente"))
            conn.commit()
            return True, f"Entrada: {hora_actual}"
            
        elif tipo == "Salida":
            c.execute("SELECT id_registro, hora_entrada FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            row = c.fetchone()
            if not row: return False, "No tienes entrada abierta hoy."
            
            id_reg, h_ent = row
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(h_ent, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=?, estado=? WHERE id_registro=?",
                      (hora_actual, horas, "Finalizado", id_reg))
            conn.commit()
            return True, f"Salida: {hora_actual} ({horas}h)"
            
    except Exception as e: return False, str(e)
    finally: conn.close()

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
    
    conn = get_db_connection()

    # ------------------------------------
    # MÓDULO 1: AGENDA 
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        with st.expander("🔍 BUSCADOR DE CITAS", expanded=False):
            q_cita = st.text_input("Buscar cita por nombre:")
            if q_cita:
                df = pd.read_sql(f"SELECT fecha, hora, nombre_paciente, tratamiento, doctor_atendio FROM citas WHERE nombre_paciente LIKE '%{q_cita}%'", conn)
                st.dataframe(df)

        st.markdown("---")
        
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            with st.expander("➕ Agendar Cita Nueva", expanded=False):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                
                with tab_reg:
                    with st.form("cita_registrada"):
                        pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                        lista_pac = []
                        if not pacientes_raw.empty:
                            lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                        
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        h_sel = st.selectbox("Hora", generar_slots_tiempo())
                        m_sel = st.text_input("Motivo", "Revisión / Continuación")
                        d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        if st.form_submit_button("Agendar"):
                            if p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]
                                nom_p = p_sel.split(" - ")[1]
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", m_sel, d_sel, 0, 0, "Pendiente"))
                                conn.commit()
                                st.success(f"Agendado el {fecha_ver_str}")
                                time.sleep(1); st.rerun()
                            else: st.error("Seleccione paciente")

                with tab_new:
                    with st.form("cita_prospecto"):
                        nombre_pros = st.text_input("Nombre")
                        tel_pros = st.text_input("Tel (10)", max_chars=10)
                        hora_pros = st.selectbox("Hora", generar_slots_tiempo())
                        motivo_pros = st.text_input("Motivo", "Revisión 1ra Vez")
                        doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        if st.form_submit_button("Agendar Prospecto"):
                            if nombre_pros and len(tel_pros) == 10:
                                id_temp = f"PROSPECTO-{int(time.time())}"
                                nom_final = limpiar_texto_mayus(nombre_pros)
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", motivo_pros, doc_pros, 0, 0, 0, "Pendiente", f"Tel: {tel_pros}"))
                                conn.commit()
                                st.success("Agendado")
                                time.sleep(1); st.rerun()
                            else: st.error("Datos incorrectos")
            
            st.markdown("### 🔄 Modificar Agenda")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                if not df_dia.empty:
                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['tratamiento']})" for i, r in df_dia.iterrows()]
                    cita_sel = st.selectbox("Seleccionar Cita:", ["Seleccionar..."] + lista_citas_dia)
                    
                    if cita_sel != "Seleccionar...":
                        hora_target = cita_sel.split(" - ")[0]
                        nombre_target = cita_sel.split(" - ")[1].split(" (")[0]
                        
                        if st.button("Eliminar Cita Seleccionada"):
                            c = conn.cursor()
                            c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nombre_target))
                            conn.commit()
                            st.success("Cita eliminada.")
                            time.sleep(1); st.rerun()
                else:
                    st.info("No hay citas este día.")

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                slots = generar_slots_tiempo()
                for slot in slots:
                    ocupado = df_dia[df_dia['hora'] == slot]
                    if ocupado.empty:
                        st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)
                    else:
                        for _, r in ocupado.iterrows():
                            color = "#FF5722" if "PROSPECTO" in str(r['id_paciente']) else "#002B5B"
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
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if pacientes_raw.empty: st.warning("Sin pacientes")
            else:
                lista_busqueda = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    id_sel_str = seleccion.split(" - ")[0]
                    p_data = pacientes_raw[pacientes_raw['id_paciente'] == id_sel_str].iloc[0]
                    
                    f_nac_raw = p_data['fecha_nacimiento'] if p_data['fecha_nacimiento'] else ""
                    edad, tipo_pac = calcular_edad_completa(f_nac_raw)
                    rfc_show = p_data['rfc'] if p_data['rfc'] else 'N/A'
                    
                    st.markdown(f"""
                    <div class="royal-card">
                        <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>
                        <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span>
                        <br><br><b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}
                        <br><b>RFC:</b> {rfc_show}
                    </div>""", unsafe_allow_html=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            requiere_factura = st.checkbox("¿Requiere Factura?", key="chk_alta")
            
            with st.form("alta_paciente"):
                c_nom, c_pat, c_mat = st.columns(3)
                nombre = c_nom.text_input("Nombre(s)")
                paterno = c_pat.text_input("Apellido Paterno")
                materno = c_mat.text_input("Apellido Materno")
                
                c_nac, c_tel, c_mail = st.columns(3)
                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1))
                tel = c_tel.text_input("Teléfono (10 dígitos)", max_chars=10)
                email = c_mail.text_input("Email")
                
                if requiere_factura:
                    st.markdown("**Datos Fiscales (SAT)**")
                    c_f1, c_f2 = st.columns(2)
                    rfc = c_f1.text_input("RFC", max_chars=13)
                    cp = c_f2.text_input("C.P.", max_chars=5)
                    regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                    uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                else:
                    rfc, cp, regimen, uso = "", "", "", ""
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    if not tel.isdigit() or len(tel) != 10: st.error("❌ Teléfono incorrecto.")
                    elif not nombre or not paterno: st.error("❌ Nombre/Apellido obligatorios.")
                    else:
                        nom_f = limpiar_texto_mayus(nombre)
                        pat_f = limpiar_texto_mayus(paterno)
                        mat_f = limpiar_texto_mayus(materno)
                        mail_f = limpiar_email(email)
                        nuevo_id = generar_id_unico(nom_f, pat_f, nacimiento)
                        f_nac_str = format_date_latino(nacimiento)
                        
                        c = conn.cursor()
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (nuevo_id, get_fecha_mx(), nom_f, pat_f, mat_f, tel, mail_f, rfc.upper(), regimen, uso, cp, "", "", "Activo", f_nac_str))
                        conn.commit()
                        st.success(f"✅ Paciente {nom_f} guardado.")
                        time.sleep(1.5); st.rerun()

        with tab_e:
            st.markdown("#### ✏️ Modificar Paciente")
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                sel_edit = st.selectbox("Buscar Paciente:", ["Seleccionar..."] + lista_edit)
                
                if sel_edit != "Seleccionar...":
                    id_target = sel_edit.split(" - ")[0]
                    p_edit = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    
                    with st.form("form_editar"):
                        e_nom = st.text_input("Nombre", p_edit['nombre'])
                        e_pat = st.text_input("Apellido Paterno", p_edit['apellido_paterno'])
                        e_tel = st.text_input("Teléfono", p_edit['telefono'])
                        e_email = st.text_input("Email", p_edit['email'])
                        
                        if st.form_submit_button("💾 ACTUALIZAR"):
                            c = conn.cursor()
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, telefono=?, email=? WHERE id_paciente=?", 
                                      (limpiar_texto_mayus(e_nom), limpiar_texto_mayus(e_pat), formatear_telefono(e_tel), e_email, id_target))
                            conn.commit()
                            st.success("Datos actualizados.")
                            time.sleep(1.5); st.rerun()

    # ------------------------------------
    # MÓDULO 3: PLANES (CON HISTORIAL)
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes de Tratamiento")
        
        try:
            pacientes = pd.read_sql("SELECT * FROM pacientes", conn)
            servicios = pd.read_sql("SELECT * FROM servicios", conn)
            df_finanzas = pd.read_sql("SELECT * FROM citas", conn)
        except Exception as e: 
            st.error(f"Error cargando base de datos: {e}")
            st.stop()
            
        if pacientes.empty:
            st.warning("No hay pacientes registrados.")
        else:
            lista_pac = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
            seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
            
            if seleccion_pac != "Buscar...":
                id_p = seleccion_pac.split(" - ")[0]
                nom_p = seleccion_pac.split(" - ")[1]
                
                st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
                if not df_finanzas.empty:
                    historial = df_finanzas[df_finanzas['id_paciente'] == id_p]
                    if not historial.empty:
                        # Corregir error de tipo de dato
                        if 'saldo_pendiente' in historial.columns:
                            deuda_total = pd.to_numeric(historial['saldo_pendiente'], errors='coerce').fillna(0).sum()
                        else:
                            deuda_total = 0
                        
                        col_sem1, col_sem2 = st.columns(2)
                        col_sem1.metric("Deuda Total", f"${deuda_total:,.2f}")
                        if deuda_total > 0: col_sem2.error("🚨 SALDO PENDIENTE")
                        else: col_sem2.success("✅ AL CORRIENTE")
                        
                        with st.expander("📜 Historial Detallado", expanded=False):
                            cols = [c for c in ['fecha', 'tratamiento', 'precio_final', 'monto_pagado', 'saldo_pendiente', 'estado_pago'] if c in historial.columns]
                            st.dataframe(historial[cols])
                
                st.markdown("---")
                st.subheader("Nuevo Plan Integral")
                
                c1, c2, c3 = st.columns(3)
                
                # Carga dinámica de servicios desde SQL
                if not servicios.empty:
                    cats = servicios['categoria'].unique()
                    cat_sel = c1.selectbox("1. Categoría", cats)
                    filt = servicios[servicios['categoria'] == cat_sel]
                    trat_sel = c2.selectbox("2. Tratamiento", filt['nombre_tratamiento'].unique())
                    item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]
                    precio_lista_sug = float(item['precio_lista'])
                    costo_lab_sug = float(item['costo_laboratorio_base'])
                else:
                    cat_sel = "General"
                    trat_sel = c2.text_input("Tratamiento Manual")
                    precio_lista_sug = c3.number_input("Precio Lista", 0.0)
                    costo_lab_sug = 0.0
                    
                c3.metric("Precio de Lista Sugerido", f"${precio_lista_sug:,.2f}")
                
                st.markdown("#### 💳 Definición de Cobro")
                col_f1, col_f2, col_f3 = st.columns(3)
                precio_final = col_f1.number_input("Precio Final a Cobrar", value=precio_lista_sug, min_value=0.0, format="%.2f")
                abono = col_f2.number_input("Abono Inicial", min_value=0.0, format="%.2f")
                saldo_real = precio_final - abono
                col_f3.metric("Saldo Pendiente (Deuda)", f"${saldo_real:,.2f}", delta_color="inverse")

                agendar_ahora = st.checkbox("📅 ¿Agendar Primera Sesión/Cita Ahora?")

                with st.form("form_plan_final"):
                    col_d1, col_d2, col_d3 = st.columns(3)
                    doctor = col_d1.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    diente = col_d2.number_input("Diente (ISO)", min_value=0, max_value=85)
                    metodo = col_d3.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                    num_citas = st.number_input("Sesiones Estimadas", min_value=1, value=1)
                    
                    if st.form_submit_button("💾 REGISTRAR"):
                        pct = 0; nota = ""
                        if precio_final > precio_lista_sug: nota = f"Sobrecosto: ${precio_final - precio_lista_sug}"
                        
                        estatus = "Pagado" if saldo_real <= 0 else "Pendiente"
                        
                        c = conn.cursor()
                        # Insertar Cita/Cobro con campo costo_laboratorio
                        c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, 
                                     categoria, tratamiento, diente, doctor_atendio, precio_lista, precio_final, 
                                     porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) 
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                  (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, 
                                   cat_sel, trat_sel, diente, doctor, precio_lista_sug, precio_final, pct, 
                                   metodo, estatus, nota, abono, saldo_real, get_fecha_mx(), costo_lab_sug))
                        
                        if agendar_ahora:
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, diente, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas) 
                                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                      (int(time.time())+1, get_fecha_mx(), "09:00", id_p, nom_p, "Seguimiento", f"{trat_sel} (Sesión 1)", diente, doctor, 0, 0, 0, "N/A", "Cita generada desde Plan"))
                        
                        conn.commit()
                        st.success(f"✅ Plan Registrado")
                        time.sleep(2); st.rerun()

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        # CORRECCIÓN DE ERROR SINTÁCTICO DE LÍNEA 370
        col_asist1, col_asist2 = st.columns([1,3])
        
        with col_asist1:
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
    
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
