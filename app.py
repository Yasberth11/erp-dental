import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import time
import re
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
        
        /* Ocultar elementos por defecto de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. MOTOR DE BASE DE DATOS (SQLITE)
# ==========================================
DB_NAME = 'royal_dental.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla Pacientes
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT PRIMARY KEY,
        fecha_registro TEXT,
        nombre TEXT,
        apellido_paterno TEXT,
        apellido_materno TEXT,
        telefono TEXT,
        email TEXT,
        rfc TEXT,
        regimen TEXT,
        uso_cfdi TEXT,
        cp TEXT,
        fecha_nacimiento TEXT
    )''')
    
    # Tabla Citas
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        id_paciente TEXT,
        nombre_paciente TEXT,
        tipo TEXT,
        motivo TEXT,
        doctor_asignado TEXT,
        estado TEXT
    )''')
    
    # Tabla Pagos y Finanzas (CON LOGICA DE LABORATORIO)
    c.execute('''CREATE TABLE IF NOT EXISTS pagos (
        id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_pago TEXT,
        hora_pago TEXT,
        id_paciente TEXT,
        nombre_paciente TEXT,
        concepto_tratamiento TEXT,
        precio_cobrado REAL,
        costo_laboratorio REAL,
        utilidad_real REAL,
        metodo_pago TEXT,
        doctor_realizo TEXT,
        comision_doctor REAL,
        nota TEXT
    )''')
    
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        doctor TEXT,
        hora_entrada TEXT,
        hora_salida TEXT,
        horas_totales REAL,
        estado TEXT
    )''')

    # Tabla Auditoría
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (
        id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_evento TEXT,
        usuario TEXT,
        accion TEXT,
        detalle TEXT
    )''')

    # Tabla Tratamientos (Catálogo)
    c.execute('''CREATE TABLE IF NOT EXISTS tratamientos (
        nombre_tratamiento TEXT PRIMARY KEY,
        categoria TEXT,
        precio_lista REAL,
        costo_laboratorio REAL
    )''')

    conn.commit()
    conn.close()

def seed_tratamientos():
    """Carga inicial del catálogo de tratamientos proporcionado"""
    conn = get_db_connection()
    c = conn.cursor()
    # Verificamos si está vacía
    c.execute("SELECT count(*) FROM tratamientos")
    if c.fetchone()[0] == 0:
        data = [
            ("Profilaxis (Limpieza Ultrasónica)", "Preventiva", 600.0, 0.0),
            ("Aplicación de Flúor (Niños)", "Preventiva", 350.0, 0.0),
            ("Sellador de Fosetas y Fisuras", "Preventiva", 400.0, 0.0),
            ("Resina Simple (1 cara)", "Operatoria", 800.0, 0.0),
            ("Resina Compuesta (2 o más caras)", "Operatoria", 1200.0, 0.0),
            ("Reconstrucción de Muñón", "Operatoria", 1500.0, 0.0),
            ("Curación Temporal (Cavit)", "Operatoria", 300.0, 0.0),
            ("Extracción Simple", "Cirugía", 900.0, 0.0),
            ("Cirugía de Tercer Molar", "Cirugía", 3500.0, 0.0),
            ("Drenaje de Absceso", "Cirugía", 800.0, 0.0),
            ("Endodoncia Anterior (1 conducto)", "Endodoncia", 2800.0, 0.0),
            ("Endodoncia Premolar (2 conductos)", "Endodoncia", 3200.0, 0.0),
            ("Endodoncia Molar (3+ conductos)", "Endodoncia", 4200.0, 0.0),
            ("Corona Zirconia", "Prótesis Fija", 4800.0, 900.0),
            ("Corona Metal-Porcelana", "Prótesis Fija", 3500.0, 600.0),
            ("Incrustación Estética", "Prótesis Fija", 3800.0, 700.0),
            ("Carilla de Porcelana", "Prótesis Fija", 5500.0, 1100.0),
            ("Poste de Fibra de Vidrio", "Prótesis Fija", 1200.0, 0.0),
            ("Placa Total (Acrílico)", "Prótesis Removible", 6000.0, 1200.0),
            ("Prótesis Flexible (Valplast)", "Prótesis Removible", 4500.0, 900.0),
            ("Blanqueamiento (Consultorio)", "Estética", 3500.0, 300.0),
            ("Blanqueamiento (Casa)", "Estética", 2500.0, 500.0),
            ("Ortodoncia Pago Inicial", "Ortodoncia", 4000.0, 1500.0),
            ("Ortodoncia Mensualidad", "Ortodoncia", 700.0, 0.0),
            ("Recolocación de Bracket", "Ortodoncia", 200.0, 0.0),
            ("Pulpotomía", "Pediatría", 1500.0, 0.0),
            ("Corona Acero-Cromo", "Pediatría", 1800.0, 0.0),
            ("Garantía", "Garantía", 0.0, 0.0)
        ]
        c.executemany("INSERT OR IGNORE INTO tratamientos VALUES (?,?,?,?)", data)
        conn.commit()
    conn.close()

# Inicialización
init_db()
seed_tratamientos()

# ==========================================
# 3. HELPERS
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def limpiar_texto_mayus(texto):
    return texto.upper().strip() if texto else ""

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, detalle))
        conn.commit()
        conn.close()
    except: pass

def generar_id_unico(nombre, paterno, nacimiento):
    part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"
    part2 = nombre[0].upper()
    part3 = str(nacimiento.year)
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{part1}{part2}-{part3}-{random_chars}"

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("20:00", "%H:%M")
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

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
            # Verificar si ya tiene entrada sin salida
            c.execute("SELECT * FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida IS NULL", (doctor, hoy))
            if c.fetchone(): return False, "Ya tienes una sesión abierta."
            
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, estado) VALUES (?,?,?,?)",
                      (hoy, doctor, hora_actual, "Activo"))
            conn.commit()
            return True, f"Entrada registrada: {hora_actual}"
            
        elif tipo == "Salida":
            c.execute("SELECT id_registro, hora_entrada FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida IS NULL", (doctor, hoy))
            registro = c.fetchone()
            if not registro: return False, "No tienes entrada registrada hoy."
            
            id_reg, h_ent = registro
            # Calcular horas
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(h_ent, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=?, estado=? WHERE id_registro=?",
                      (hora_actual, horas, "Finalizado", id_reg))
            conn.commit()
            return True, f"Salida registrada: {hora_actual} ({horas} hrs)"
            
    except Exception as e: return False, str(e)
    finally: conn.close()

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col1, col_centro, col3 = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 30px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div><br>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC":
                st.session_state.perfil = "Consultorio"
                st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN":
                st.session_state.perfil = "Administracion"
                st.rerun()
            else: st.error("Acceso Denegado")

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    
    # Menú Lateral Original
    menu = st.sidebar.radio("Menú", 
        ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes & Cobranza", "4. Control Asistencia"])
    
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
                df = pd.read_sql(f"SELECT * FROM citas WHERE nombre_paciente LIKE '%{q_cita}%'", conn)
                st.dataframe(df)

        st.markdown("---")
        col_cal1, col_cal2 = st.columns([1, 2])
        
        with col_cal1:
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            fecha_str = format_date_latino(fecha_ver)
            
            st.markdown("#### ➕ Agendar Cita")
            with st.form("nueva_cita"):
                # Cargar pacientes para dropdown
                pacientes = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                lista_pac = ["Nuevo / Prospecto"] + pacientes.apply(lambda x: f"{x['id_paciente']} | {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                
                p_sel = st.selectbox("Paciente", lista_pac)
                h_sel = st.selectbox("Hora", generar_slots_tiempo())
                motivo = st.text_input("Motivo", "Revisión")
                doc = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                
                if st.form_submit_button("Agendar"):
                    if p_sel == "Nuevo / Prospecto":
                        nom_temp = st.text_input("Nombre Prospecto (Si seleccionó Nuevo)") # Este flujo es mejorable pero funcional
                        id_final = "PROSPECTO"
                        nom_final = "PROSPECTO - Pendiente Registro"
                    else:
                        id_final = p_sel.split(" | ")[0]
                        nom_final = p_sel.split(" | ")[1]
                    
                    c = conn.cursor()
                    c.execute("INSERT INTO citas (fecha, hora, id_paciente, nombre_paciente, tipo, motivo, doctor_asignado, estado) VALUES (?,?,?,?,?,?,?,?)",
                              (fecha_str, h_sel, id_final, nom_final, "General", motivo, doc, "Pendiente"))
                    conn.commit()
                    st.success("Cita Agendada")
                    time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 Citas del {fecha_str}")
            df_dia = pd.read_sql(f"SELECT * FROM citas WHERE fecha='{fecha_str}' ORDER BY hora", conn)
            
            slots = generar_slots_tiempo()
            for slot in slots:
                cita = df_dia[df_dia['hora'] == slot]
                if not cita.empty:
                    row = cita.iloc[0]
                    st.info(f"🕒 {slot} - {row['nombre_paciente']} ({row['doctor_asignado']}) - {row['motivo']}")
                    if st.button("🗑️ Cancelar", key=f"del_{slot}"):
                        c = conn.cursor()
                        c.execute(f"DELETE FROM citas WHERE id_cita={row['id_cita']}")
                        conn.commit()
                        st.rerun()
                else:
                    st.markdown(f"<div style='color:#ccc; padding:5px; border-bottom:1px solid #eee;'>{slot} - Disponible</div>", unsafe_allow_html=True)

    # ------------------------------------
    # MÓDULO 2: PACIENTES (MEJORADO)
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico")
        
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)", "✏️ EDITAR"])
        
        with tab_b:
            q = st.text_input("Buscar Paciente (Nombre/Apellido):")
            if q:
                df = pd.read_sql(f"SELECT * FROM pacientes WHERE nombre LIKE '%{q}%' OR apellido_paterno LIKE '%{q}%'", conn)
                st.dataframe(df, use_container_width=True)

        with tab_n:
            st.markdown("#### Datos Generales")
            with st.form("alta_paciente"):
                c1, c2 = st.columns(2)
                nombre = c1.text_input("Nombre(s)")
                paterno = c2.text_input("Apellido Paterno")
                materno = c1.text_input("Apellido Materno")
                nacimiento = c2.date_input("Fecha Nacimiento", min_value=datetime(1930,1,1))
                
                c3, c4 = st.columns(2)
                tel = c3.text_input("Teléfono (10 dígitos)", max_chars=10)
                email = c4.text_input("Email")
                
                st.markdown("**Datos Fiscales (Opcional)**")
                rfc = st.text_input("RFC")
                regimen = st.selectbox("Régimen", ["616 - Sin obligaciones", "605 - Sueldos y Salarios", "612 - Empresarial"])
                
                if st.form_submit_button("💾 GUARDAR"):
                    if nombre and paterno and len(tel) == 10:
                        id_p = generar_id_unico(nombre, paterno, nacimiento)
                        c = conn.cursor()
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (id_p, get_fecha_mx(), limpiar_texto_mayus(nombre), limpiar_texto_mayus(paterno), 
                                   limpiar_texto_mayus(materno), tel, email, rfc, regimen, "", "", format_date_latino(nacimiento)))
                        conn.commit()
                        registrar_auditoria("Consultorio", "ALTA PACIENTE", f"Nuevo: {nombre} {paterno}")
                        st.success(f"Paciente registrado con ID: {id_p}")
                    else:
                        st.error("Nombre, Apellido y Teléfono (10 dígitos) son obligatorios.")

        with tab_e:
            st.warning("⚠️ Edición de datos (Se generará registro de auditoría)")
            df_p = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
            if not df_p.empty:
                opciones = df_p.apply(lambda x: f"{x['id_paciente']} | {x['nombre']} {x['apellido_paterno']}", axis=1)
                sel_edit = st.selectbox("Seleccionar Paciente a Editar:", opciones)
                id_target = sel_edit.split(" | ")[0]
                
                current = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{id_target}'", conn).iloc[0]
                
                with st.form("form_edit"):
                    ne_tel = st.text_input("Teléfono", value=current['telefono'])
                    ne_email = st.text_input("Email", value=current['email'])
                    ne_rfc = st.text_input("RFC", value=current['rfc'])
                    
                    if st.form_submit_button("Actualizar Datos"):
                        c = conn.cursor()
                        c.execute("UPDATE pacientes SET telefono=?, email=?, rfc=? WHERE id_paciente=?", 
                                  (ne_tel, ne_email, ne_rfc, id_target))
                        conn.commit()
                        registrar_auditoria("Consultorio", "EDICION", f"Modificación datos paciente {id_target}")
                        st.success("Datos actualizados correctamente.")
                        time.sleep(1); st.rerun()

    # ------------------------------------
    # MÓDULO 3: PLANES Y COBRANZA (NUEVA LÓGICA)
    # ------------------------------------
    elif menu == "3. Planes & Cobranza":
        st.title("💰 Caja y Cobro de Tratamientos")
        
        # 1. Selección de Paciente
        df_pac = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
        opc_pac = df_pac.apply(lambda x: f"{x['id_paciente']} | {x['nombre']} {x['apellido_paterno']}", axis=1)
        sel_pac = st.selectbox("Seleccionar Paciente:", opc_pac)
        id_pac_cobro = sel_pac.split(" | ")[0]
        nom_pac_cobro = sel_pac.split(" | ")[1]

        st.markdown("---")
        
        # 2. Selección de Tratamiento (Catálogo)
        df_trat = pd.read_sql("SELECT * FROM tratamientos ORDER BY categoria, nombre_tratamiento", conn)
        lista_trat = ["Otro / Manual"] + df_trat.apply(lambda x: f"{x['nombre_tratamiento']} (Lista: ${x['precio_lista']})", axis=1).tolist()
        
        sel_trat = st.selectbox("Seleccionar Tratamiento a Cobrar:", lista_trat)
        
        # Valores por defecto
        def_precio = 0.0
        def_lab = 0.0
        txt_concepto = ""
        
        if sel_trat != "Otro / Manual":
            nombre_puro = sel_trat.split(" (Lista")[0]
            row_t = df_trat[df_trat['nombre_tratamiento'] == nombre_puro].iloc[0]
            def_precio = float(row_t['precio_lista'])
            def_lab = float(row_t['costo_laboratorio'])
            txt_concepto = nombre_puro
        
        # 3. Formulario de Pago
        with st.form("form_cobro"):
            st.subheader("Detalle Financiero")
            c1, c2, c3 = st.columns(3)
            
            concepto = c1.text_input("Concepto", value=txt_concepto)
            monto_final = c2.number_input("Precio Final a Cobrar ($)", value=def_precio, step=50.0)
            costo_lab_real = c3.number_input("Costo Laboratorio ($)", value=def_lab, step=50.0, help="Costo del técnico dental")
            
            c4, c5 = st.columns(2)
            doc_realizo = c4.selectbox("Doctor que realizó el trabajo", ["Dr. Emmanuel", "Dra. Mónica", "Asistente"])
            metodo = c5.radio("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"], horizontal=True)
            
            # Cálculo de Utilidad y Comisión
            utilidad = monto_final - costo_lab_real
            comision = utilidad * 0.25 if utilidad > 0 else 0
            
            st.info(f"📊 **Cálculo:** Cobrado ${monto_final} - Lab ${costo_lab_real} = **Utilidad ${utilidad}**")
            st.success(f"💼 **Comisión para {doc_realizo}:** ${comision:,.2f} (25% de Utilidad)")
            
            nota = st.text_area("Nota adicional (Opcional)")
            
            if st.form_submit_button("💳 REGISTRAR COBRO"):
                if monto_final > 0:
                    c = conn.cursor()
                    fecha_hoy = get_fecha_mx()
                    c.execute('''INSERT INTO pagos (fecha_pago, hora_pago, id_paciente, nombre_paciente, concepto_tratamiento, 
                                 precio_cobrado, costo_laboratorio, utilidad_real, metodo_pago, doctor_realizo, comision_doctor, nota)
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (fecha_hoy, get_hora_mx(), id_pac_cobro, nom_pac_cobro, concepto, 
                               monto_final, costo_lab_real, utilidad, metodo, doc_realizo, comision, nota))
                    conn.commit()
                    
                    # Auditoría si hubo descuento manual
                    if sel_trat != "Otro / Manual" and monto_final < def_precio:
                        registrar_auditoria("Consultorio", "DESCUENTO", f"Descuento de ${def_precio - monto_final} en {concepto} autorizado por {doc_realizo}")
                    
                    st.balloons()
                    st.success("Pago registrado exitosamente")
                    time.sleep(2); st.rerun()

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 👨‍⚕️ Dr. Emmanuel")
            if st.button("🟢 ENTRADA Dr. Emmanuel"):
                ok, msg = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(msg)
                else: st.warning(msg)
            if st.button("🔴 SALIDA Dr. Emmanuel"):
                ok, msg = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(msg)
                else: st.warning(msg)

    conn.close()

# ==========================================
# 7. VISTA ADMINISTRACIÓN (BÁSICA POR AHORA)
# ==========================================
def vista_admin():
    st.title("💼 Panel Administrativo")
    st.info("Bienvenido Yasberth. Aquí verás los reportes financieros.")
    
    conn = get_db_connection()
    
    # Resumen Rápido
    df_pagos = pd.read_sql("SELECT * FROM pagos", conn)
    if not df_pagos.empty:
        total_ingreso = df_pagos['precio_cobrado'].sum()
        total_utilidad = df_pagos['utilidad_real'].sum()
        total_comisiones = df_pagos['comision_doctor'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Totales", f"${total_ingreso:,.2f}")
        c2.metric("Utilidad Neta Clínica", f"${total_utilidad:,.2f}")
        c3.metric("Comisiones Pagadas", f"${total_comisiones:,.2f}")
        
        st.markdown("### 🛡️ Bitácora de Auditoría")
        df_audit = pd.read_sql("SELECT * FROM auditoria ORDER BY id_evento DESC", conn)
        st.dataframe(df_audit, use_container_width=True)
    else:
        st.warning("No hay datos financieros aún.")
    
    if st.button("Cerrar Sesión Admin"):
        st.session_state.perfil = None; st.rerun()
    conn.close()

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        vista_admin()
