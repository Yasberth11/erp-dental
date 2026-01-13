import streamlit as st
import pandas as pd
import sqlite3 # CAMBIO: Motor de base de datos local
from datetime import datetime, timedelta
import pytz
import re
import time
import random
import string

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO ROYAL (INTACTO)
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
        
        /* Ocultar elementos default de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB (CAMBIO: SQLITE EN LUGAR DE GSPREAD)
# ==========================================
DB_FILE = "royal_dental_db.sqlite"

def get_db_connection():
    # Conecta al archivo local. Si no existe, lo crea.
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    # Esto permite acceder a las columnas por nombre (como dict)
    conn.row_factory = sqlite3.Row 
    return conn

# Función para inicializar tablas (Sustituye a crear las hojas en Drive)
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla Pacientes
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, extra1 TEXT, estado TEXT, fecha_nacimiento TEXT
    )''')
    
    # Tabla Citas
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT
    )''')
    
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, 
        hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT
    )''')
    
    # Tabla Servicios (Catálogo) - Le cargaremos tus precios por defecto
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (
        categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL
    )''')
    
    conn.commit()
    conn.close()

# Ejecutamos la creación de tablas al inicio
init_db()

# ==========================================
# 3. HELPERS & SANITIZACIÓN (INTACTO)
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
# 4. LOGICA ASISTENCIA (MIGRADO A SQL)
# ==========================================
def registrar_movimiento(doctor, tipo):
    try:
        conn = get_db_connection()
        # Leemos en dataframe igual que antes
        df = pd.read_sql("SELECT * FROM asistencia", conn)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        if tipo == "Entrada":
            if not df.empty:
                # Lógica idéntica: buscamos si ya entró
                check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
                if not check.empty: 
                    conn.close()
                    return False, "Ya tienes una sesión abierta."
            
            # INSERT SQL (Reemplaza append_row)
            c = conn.cursor()
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, hora_salida, horas_totales, estado) VALUES (?,?,?,?,?,?)",
                      (hoy, doctor, hora_actual, "", "", "Pendiente"))
            conn.commit()
            conn.close()
            return True, f"Entrada: {hora_actual}"
            
        elif tipo == "Salida":
            if df.empty: 
                conn.close(); return False, "No hay registros."
            
            check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
            if check.empty: 
                conn.close(); return False, "No encontré entrada abierta hoy."
            
            # Obtener ID para actualizar
            id_reg = check.iloc[-1]['id_registro']
            entrada = check.iloc[-1]['hora_entrada']
            
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(entrada, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            # UPDATE SQL (Reemplaza update_cell)
            c = conn.cursor()
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=? WHERE id_registro=?", (hora_actual, horas, int(id_reg)))
            conn.commit()
            conn.close()
            return True, f"Salida: {hora_actual} ({horas}h)"
            
    except Exception as e: return False, str(e)

# ==========================================
# 5. SISTEMA DE LOGIN (INTACTO)
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
# 6. VISTA CONSULTORIO (MIGRADO A SQL)
# ==========================================
def vista_consultorio():
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    
    menu = st.sidebar.radio("Menú", 
        ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Control Asistencia"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()
    
    # Creamos conexión para usar en las pestañas
    conn = get_db_connection()

    # ------------------------------------
    # MÓDULO 1: AGENDA 
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        
        # --- BUSCADOR GLOBAL DE CITAS ---
        with st.expander("🔍 BUSCADOR DE CITAS (¿Cuándo le toca a...?)", expanded=False):
            st.info("Escribe el nombre del paciente para ver su historial completo de citas.")
            q_cita = st.text_input("Nombre del Paciente:")
            if q_cita:
                try:
                    # SQL LIKE para búsqueda
                    df_res = pd.read_sql(f"SELECT fecha, hora, nombre_paciente, tratamiento, doctor_atendio, estado_pago FROM citas WHERE nombre_paciente LIKE '%{q_cita}%'", conn)
                    if not df_res.empty:
                        st.write(f"Encontradas {len(df_res)} citas:")
                        st.dataframe(df_res)
                    else:
                        st.warning("No se encontraron citas con ese nombre.")
                except Exception as e:
                    st.error(f"Error en búsqueda: {e}")

        st.markdown("---")
        
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            # --- AGENDAR ---
            with st.expander("➕ Agendar Cita Nueva", expanded=False):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                
                with tab_reg:
                    with st.form("cita_registrada"):
                        # Cargar pacientes de SQL
                        pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                        if not pacientes_raw.empty:
                            lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                        else:
                            lista_pac = []
                        
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        h_sel = st.selectbox("Hora", generar_slots_tiempo())
                        m_sel = st.text_input("Motivo", "Revisión / Continuación")
                        d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        if st.form_submit_button("Agendar"):
                            if p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]
                                nom_p = p_sel.split(" - ")[1]
                                # INSERT SQL
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
                        precio_pros = st.number_input("Costo", value=100.0, min_value=0.0)
                        doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        if st.form_submit_button("Agendar Prospecto"):
                            if nombre_pros and len(tel_pros) == 10:
                                id_temp = f"PROSPECTO-{int(time.time())}"
                                nom_final = limpiar_texto_mayus(nombre_pros)
                                # INSERT SQL
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", motivo_pros, doc_pros, precio_pros, 0, precio_pros, "Pendiente", f"Tel: {tel_pros}"))
                                conn.commit()
                                st.success("Agendado")
                                time.sleep(1); st.rerun()
                            else: st.error("Datos incorrectos")
            
            # --- MODIFICAR CITAS ---
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
                        
                        tab_del, tab_res = st.tabs(["❌ Cancelar", "🗓️ Reagendar"])
                        
                        with tab_del:
                            if st.button("Eliminar Cita Definitivamente"):
                                c = conn.cursor()
                                # DELETE SQL
                                c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nombre_target))
                                conn.commit()
                                st.success("Cita eliminada y horario liberado.")
                                time.sleep(1); st.rerun()
                        
                        with tab_res:
                            st.info(f"Cita Actual: {hora_target} del {fecha_ver_str}")
                            with st.form("form_reagendar"):
                                nueva_fecha_obj = st.date_input("Nueva Fecha", format="DD/MM/YYYY")
                                nueva_hora = st.selectbox("Nueva Hora", generar_slots_tiempo())
                                
                                if st.form_submit_button("Confirmar Cambio"):
                                    nueva_fecha_str = format_date_latino(nueva_fecha_obj)
                                    # UPDATE SQL
                                    c = conn.cursor()
                                    c.execute("UPDATE citas SET fecha=?, hora=? WHERE fecha=? AND hora=? AND nombre_paciente=?", 
                                              (nueva_fecha_str, nueva_hora, fecha_ver_str, hora_target, nombre_target))
                                    conn.commit()
                                    st.success(f"✅ Horario actualizado.")
                                    time.sleep(2); st.rerun()
                else:
                    st.info("No hay citas este día.")

        with col_
