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
# 1. CONFIGURACIÓN Y ESTILO
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
        
        /* Inputs numéricos alineados a la derecha */
        input[type=number] { text-align: right; }
        
        /* Alerta Médica */
        .alerta-medica { background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; border: 1px solid #ef9a9a; font-weight: bold; }
        
        div[data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end; }
        
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

def migrar_tablas():
    """Función de seguridad para actualizar la DB si faltan columnas nuevas"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Intentar agregar columna antecedentes si no existe
        c.execute("ALTER TABLE pacientes ADD COLUMN antecedentes_medicos TEXT")
    except: pass # Ya existe
    
    try:
        # Asegurar columnas en citas
        c.execute("ALTER TABLE citas ADD COLUMN costo_laboratorio REAL")
    except: pass
    
    try:
        c.execute("ALTER TABLE citas ADD COLUMN categoria TEXT")
    except: pass
    
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla Pacientes
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT,
        antecedentes_medicos TEXT
    )''')
    
    # Tabla Citas
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, 
        hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (
        categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL
    )''')
    
    conn.commit()
    conn.close()

def seed_data():
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

init_db()
migrar_tablas() # Ejecutar migración por si faltan columnas
seed_data()

# ==========================================
# 3. HELPERS
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")
def limpiar_texto_mayus(texto): return texto.upper().strip() if texto else ""
def limpiar_email(texto): return texto.lower().strip() if texto else ""

def format_tel_visual(tel):
    if not tel or len(tel) != 10: return tel
    return f"{tel[:2]}-{tel[2:6]}-{tel[6:]}"

def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    try:
        if isinstance(nacimiento_input, str):
            nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date()
        else:
            nacimiento = nacimiento_input
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        tipo = "MENOR DE EDAD" if edad < 18 else "ADULTO"
        return edad, tipo
    except: return "N/A", ""

def generar_id_unico(nombre, paterno, nacimiento):
    try:
        part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"
        part2 = nombre[0].upper()
        part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"

def formatear_telefono_db(numero): return re.sub(r'\D', '', str(numero))

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("20:00", "%H:%M")
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales():
    return ["605 - Sueldos y Salarios", "612 - PFAEP (Actividad Empresarial)", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]

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
            conn.commit(); return True, f"Entrada: {hora_actual}"
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
            conn.commit(); return True, f"Salida: {hora_actual} ({horas}h)"
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
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Control Asistencia"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    
    conn = get_db_connection()

    # --- MÓDULO 1: AGENDA ---
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        
        with st.expander("🔍 BUSCADOR DE CITAS", expanded=False):
            q_cita = st.text_input("Buscar cita por nombre:")
            if q_cita:
                # Modificado para mostrar el estado
                df = pd.read_sql(f"SELECT fecha, hora, nombre_paciente, tratamiento, doctor_atendio, estado_pago FROM citas WHERE nombre_paciente LIKE '%{q_cita}%' ORDER BY timestamp DESC", conn)
                st.dataframe(df)

        col_cal1, col_cal2 = st.columns([1, 2.5])
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            with st.expander("➕ Agendar Cita Nueva", expanded=False):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                # AGENDAR REGISTRADO
                with tab_reg:
                    with st.form("cita_registrada", clear_on_submit=True):
                        pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                        lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not pacientes_raw.empty else []
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        h_sel = st.selectbox("Hora", generar_slots_tiempo())
                        m_sel = st.text_input("Motivo", "Revisión / Continuación")
                        d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        if st.form_submit_button("Agendar"):
                            if p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]
                                nom_p = p_sel.split(" - ")[1]
                                c = conn.cursor()
                                # Se corrigió el INSERT para incluir todas las columnas necesarias
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", m_sel, d_sel, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General"))
                                conn.commit()
                                st.success(f"Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Seleccione paciente")

                # AGENDAR PROSPECTO
                with tab_new:
                    with st.form("cita_prospecto", clear_on_submit=True):
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
                                # CORRECCIÓN DE ERROR SQLITE OPERATIONAL ERROR AQUÍ
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", motivo_pros, doc_pros, 0, 0, 0, "Pendiente", f"Tel: {tel_pros}", 0, 0, "No", 0, 0, "", "No", "", 0, "Primera Vez"))
                                conn.commit()
                                st.success("Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Datos incorrectos")
            
            st.markdown("### 🔄 Modificar Agenda")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                if not df_dia.empty:
                    # Incluimos el estado en el selector para ver si está cancelada
                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['estado_pago']})" for i, r in df_dia.iterrows()]
                    cita_sel = st.selectbox("Seleccionar Cita:", ["Seleccionar..."] + lista_citas_dia)
                    
                    if cita_sel != "Seleccionar...":
                        hora_target = cita_sel.split(" - ")[0]
                        # Extraer nombre con cuidado del paréntesis
                        nom_target = cita_sel.split(" - ")[1].split(" (")[0]
                        
                        st.info(f"Gestionando cita de: {nom_target}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.markdown("**Reagendar Cita:**")
                            new_date_res = st.date_input("Nueva Fecha", datetime.now(TZ_MX))
                            new_h_res = st.selectbox("Nueva Hora", generar_slots_tiempo(), key="reag_time")
                            if st.button("🗓️ Mover y Activar"):
                                new_date_str = format_date_latino(new_date_res)
                                c = conn.cursor()
                                # SOLUCIÓN ERROR LULÚ: Al reagendar, forzamos estado a 'Pendiente' para quitar el Cancelado
                                c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", 
                                          (new_date_str, new_h_res, fecha_ver_str, hora_target, nom_target))
                                conn.commit()
                                st.success(f"✅ Reagendada al {new_date_str} {new_h_res}"); time.sleep(1); st.rerun()
                        
                        with col_btn2:
                             st.markdown("**Cancelar:**")
                             st.write("") 
                             st.write("") 
                             if st.button("❌ Cancelar Cita", type="primary"):
                                c = conn.cursor()
                                c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", 
                                          (fecha_ver_str, hora_target, nom_target))
                                conn.commit()
                                st.warning("Cita cancelada."); time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                slots = generar_slots_tiempo()
                for slot in slots:
                    # Solo mostramos ocupado si NO está cancelado
                    ocupado = df_dia[(df_dia['hora'] == slot) & (df_dia['estado_pago'] != 'CANCELADO')]
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

    # --- MÓDULO 2: PACIENTES ---
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico")
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)", "✏️ EDITAR COMPLETO"])
        
        with tab_b:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if pacientes_raw.empty: st.warning("Sin pacientes")
            else:
                lista_busqueda = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                if seleccion != "Buscar...":
                    id_sel_str = seleccion.split(" - ")[0]
                    p_data = pacientes_raw[pacientes_raw['id_paciente'] == id_sel_str].iloc[0]
                    edad, tipo_pac = calcular_edad_completa(p_data.get('fecha_nacimiento', ''))
                    tel_fmt = format_tel_visual(p_data['telefono'])
                    
                    # ALERTA MÉDICA (SOLUCIÓN NOTAS PERMANENTES)
                    antecedentes = p_data.get('antecedentes_medicos', '')
                    if antecedentes:
                        st.markdown(f"<div class='alerta-medica'>⚠️ ALERTA MÉDICA: {antecedentes}</div><br>", unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="royal-card">
                        <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data['apellido_materno']}</h3>
                        <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac} - {p_data.get('sexo', '')}</span>
                        <br><br><b>Tel:</b> {tel_fmt} | <b>Email:</b> {p_data['email']}
                        <br><b>RFC:</b> {p_data.get('rfc', 'N/A')} | <b>Régimen:</b> {p_data.get('regimen', 'N/A')}
                    </div>""", unsafe_allow_html=True)
                    
                    # HISTORIAL DE NOTAS (SOLUCIÓN HISTORIAL RECURRENTE)
                    st.markdown("#### 📜 Historial Clínico y Notas de Evolución")
                    hist_notas = pd.read_sql(f"SELECT fecha, tratamiento, doctor_atendio, notas FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn)
                    st.dataframe(hist_notas, use_container_width=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            with st.form("alta_paciente"):
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)")
                paterno = c2.text_input("Apellido Paterno")
                materno = c3.text_input("Apellido Materno")
                
                c4, c5, c6 = st.columns(3)
                nacimiento = c4.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1))
                tel = c5.text_input("Teléfono (10 dígitos)", max_chars=10)
                email = c6.text_input("Email")
                
                c7, c8 = st.columns(2)
                sexo = c7.selectbox("Sexo/Género", ["Mujer", "Hombre", "Prefiero no decir"])
                rfc = c8.text_input("RFC (Opcional)")
                
                # NUEVO CAMPO: ANTECEDENTES
                st.markdown("**Información Médica Importante**")
                antecedentes = st.text_area("Alergias / Padecimientos Crónicos (Aparecerá en Rojo en el expediente)", placeholder="Ej. Alérgico a Penicilina, Hipertenso...")
                
                st.markdown("**Datos Fiscales**")
                c9, c10, c11 = st.columns(3)
                regimen = c9.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                uso_cfdi = c10.selectbox("Uso CFDI", get_usos_cfdi())
                cp = c11.text_input("Código Postal (5 dígitos)", max_chars=5)
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    errores = []
                    if not tel.isdigit() or len(tel) != 10: errores.append("❌ Teléfono debe ser 10 dígitos numéricos.")
                    if cp and (not cp.isdigit() or len(cp) != 5): errores.append("❌ C.P. debe ser 5 dígitos numéricos.")
                    if not nombre or not paterno: errores.append("❌ Nombre y Apellido Paterno obligatorios.")
                    
                    if errores:
                        for e in errores: st.error(e)
                    else:
                        nom_f = limpiar_texto_mayus(nombre)
                        pat_f = limpiar_texto_mayus(paterno)
                        mat_f = limpiar_texto_mayus(materno)
                        nuevo_id = generar_id_unico(nom_f, pat_f, nacimiento)
                        f_nac_str = format_date_latino(nacimiento)
                        
                        c = conn.cursor()
                        # Incluye el nuevo campo antecedentes
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (nuevo_id, get_fecha_mx(), nom_f, pat_f, mat_f, tel, limpiar_email(email), rfc.upper(), regimen, uso_cfdi, cp, "", sexo, "Activo", f_nac_str, antecedentes))
                        conn.commit()
                        st.success(f"✅ Paciente {nom_f} guardado."); time.sleep(1.5); st.rerun()

        with tab_e:
            st.markdown("#### ✏️ Edición Completa")
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                sel_edit = st.selectbox("Buscar Paciente:", ["Seleccionar..."] + lista_edit)
                
                if sel_edit != "Seleccionar...":
                    id_target = sel_edit.split(" - ")[0]
                    p = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    
                    with st.form("form_editar_full"):
                        ec1, ec2, ec3 = st.columns(3)
                        e_nom = ec1.text_input("Nombre", p['nombre'])
                        e_pat = ec2.text_input("A. Paterno", p['apellido_paterno'])
                        e_mat = ec3.text_input("A. Materno", p['apellido_materno'])
                        ec4, ec5 = st.columns(2)
                        e_tel = ec4.text_input("Teléfono", p['telefono'])
                        e_email = ec5.text_input("Email", p['email'])
                        
                        st.markdown("**Médico**")
                        # Recuperar antecedente de forma segura (por si es base vieja)
                        ant_old = p['antecedentes_medicos'] if 'antecedentes_medicos' in p else ""
                        e_ant = st.text_area("Alertas Médicas (Alergias)", value=ant_old)

                        st.markdown("**Fiscal**")
                        ec6, ec7, ec8 = st.columns(3)
                        e_rfc = ec6.text_input("RFC", p['rfc'])
                        e_cp = ec7.text_input("C.P.", p['cp'])
                        idx_reg = 0
                        reg_list = get_regimenes_fiscales()
                        if p['regimen'] in reg_list: idx_reg = reg_list.index(p['regimen'])
                        e_reg = ec8.selectbox("Régimen", reg_list, index=idx_reg)

                        if st.form_submit_button("💾 ACTUALIZAR TODO"):
                            c = conn.cursor()
                            # Actualizamos también antecedentes
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, rfc=?, cp=?, regimen=?, antecedentes_medicos=? WHERE id_paciente=?", 
                                      (limpiar_texto_mayus(e_nom), limpiar_texto_mayus(e_pat), limpiar_texto_mayus(e_mat), formatear_telefono_db(e_tel), e_email, e_rfc.upper(), e_cp, e_reg, e_ant, id_target))
                            conn.commit()
                            st.success("Datos actualizados."); time.sleep(1.5); st.rerun()

    # --- MÓDULO 3: PLANES DE TRATAMIENTO ---
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes y Finanzas")
        try:
            pacientes = pd.read_sql("SELECT * FROM pacientes", conn)
            servicios = pd.read_sql("SELECT * FROM servicios", conn)
            df_finanzas = pd.read_sql("SELECT * FROM citas", conn)
        except Exception as e: st.error(f"Error DB: {e}"); st.stop()
            
        if pacientes.empty:
            st.warning("Registra pacientes primero.")
        else:
            lista_pac = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
            seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
            
            if seleccion_pac != "Buscar...":
                id_p = seleccion_pac.split(" - ")[0]
                nom_p = seleccion_pac.split(" - ")[1]
                
                # ESTADO DE CUENTA
                st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
                if not df_finanzas.empty:
                    historial = df_finanzas[df_finanzas['id_paciente'] == id_p]
                    if not historial.empty:
                        # Filtramos solo lo que no está cancelado para la deuda
                        hist_valid = historial[historial['estado_pago'] != 'CANCELADO']
                        deuda_total = pd.to_numeric(hist_valid['saldo_pendiente'], errors='coerce').fillna(0).sum()
                        col_sem1, col_sem2 = st.columns(2)
                        col_sem1.metric("Deuda Total", f"${deuda_total:,.2f}")
                        
                        if deuda_total > 0: 
                            col_sem2.error(f"🚨 TIENE UN SALDO PENDIENTE DE: ${deuda_total:,.2f}")
                        else: 
                            col_sem2.success("✅ SIN ADEUDOS (Cuenta al corriente)")
                        
                        with st.expander("📜 Ver Historial Clínico y Financiero Completo", expanded=True):
                            st.dataframe(historial[['fecha', 'tratamiento', 'doctor_atendio', 'precio_final', 'monto_pagado', 'saldo_pendiente', 'estado_pago', 'notas']])
                
                st.markdown("---")
                st.subheader("Nuevo Plan / Procedimiento")
                
                c1, c2, c3 = st.columns(3)
                
                if not servicios.empty:
                    cats = servicios['categoria'].unique()
                    cat_sel = c1.selectbox("1. Categoría", cats)
                    filt = servicios[servicios['categoria'] == cat_sel]
                    trat_sel = c2.selectbox("2. Tratamiento", filt['nombre_tratamiento'].unique())
                    item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]
                    precio_lista_sug = float(item['precio_lista'])
                    costo_lab_sug = float(item['costo_laboratorio_base'])
                else:
                    cat_sel = "Manual"
                    trat_sel = c2.text_input("Tratamiento")
                    precio_lista_sug = 0.0
                    costo_lab_sug = 0.0
                    
                c3.metric("Precio Lista", f"${precio_lista_sug:,.2f}")
                
                with st.form("form_plan_final"):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    precio_final = col_f1.number_input("Precio Final a Cobrar", value=precio_lista_sug, min_value=0.0, format="%.2f")
                    abono = col_f2.number_input("Abono Inicial", min_value=0.0, format="%.2f")
                    
                    if precio_final < precio_lista_sug:
                        st.info(f"🎁 Descuento aplicado: ${precio_lista_sug - precio_final:,.2f}")
                    elif precio_final > precio_lista_sug:
                        pct_extra = ((precio_final - precio_lista_sug) / precio_lista_sug) * 100 if precio_lista_sug > 0 else 0
                        st.warning(f"📈 Sobrecosto: +{pct_extra:.1f}% (${precio_final - precio_lista_sug:,.2f})")
                    
                    saldo_real = precio_final - abono
                    col_f3.metric("Saldo Pendiente", f"${saldo_real:,.2f}")
                    
                    st.markdown("---")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    doctor = col_d1.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    diente = col_d2.number_input("Diente (ISO)", min_value=0, max_value=85, step=1)
                    metodo = col_d3.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia", "Pendiente de Pago"])
                    
                    # CAMPO DE NOTAS DE EVOLUCIÓN (Aquí se registra lo del día)
                    notas_evolucion = st.text_area("Notas del Procedimiento (Evolución)", placeholder="Detalles clínicos de la sesión de hoy...")
                    
                    agendar = st.checkbox("¿Agendar Cita para Realizar el Tratamiento?")
                    st.caption("Si marcas la casilla anterior, selecciona fecha y hora:")
                    c_date1, c_date2 = st.columns(2)
                    f_cita_plan = c_date1.date_input("Fecha Cita Tratamiento", datetime.now(TZ_MX))
                    h_cita_plan = c_date2.selectbox("Hora Cita", generar_slots_tiempo())

                    if st.form_submit_button("💾 REGISTRAR PLAN Y COBRO"):
                        if metodo == "Pendiente de Pago" and abono > 0:
                            st.warning("Seleccionaste 'Pendiente de Pago' pero ingresaste un abono. Se registrará el abono.")
                        
                        nota_final = f"{notas_evolucion} | Desc: ${precio_lista_sug-precio_final}" if precio_final < precio_lista_sug else notas_evolucion
                        estatus = "Pagado" if saldo_real <= 0 else "Pendiente"
                        
                        c = conn.cursor()
                        # SOLUCIÓN ERROR INSERT: Se revisaron y contaron todas las columnas para que coincidan
                        c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, 
                                     categoria, tratamiento, diente, doctor_atendio, precio_lista, precio_final, 
                                     porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) 
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                  (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, 
                                   cat_sel, trat_sel, str(diente), doctor, precio_lista_sug, precio_final, 0, 
                                   metodo, estatus, nota_final, abono, saldo_real, get_fecha_mx(), costo_lab_sug))
                        
                        if agendar:
                            f_str = format_date_latino(f_cita_plan)
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, diente, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria) 
                                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                      (int(time.time())+1, f_str, h_cita_plan, id_p, nom_p, "Tratamiento", f"{trat_sel}", str(diente), doctor, 0, 0, 0, "Pendiente", "Cita de Tratamiento", 0, 0, "No", 0, 0, "", "No", "", 0, cat_sel))
                        
                        conn.commit()
                        st.success(f"✅ Tratamiento registrado correctamente."); time.sleep(2); st.rerun()

    # --- MÓDULO 4: ASISTENCIA ---
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
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
