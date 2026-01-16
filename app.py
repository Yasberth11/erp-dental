import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import re
import time
import random
import string
import base64
import io
import numpy as np
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import os

# ==========================================
# 1. CONFIGURACIÓN Y CATÁLOGOS
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')
LOGO_FILE = "logo.png"
DIRECCION_CONSULTORIO = "Calle Ejemplo #123, Col. Centro, Ciudad de México" 

# CONSTANTES DE PERSONAL
DOCS_INFO = {
    "Dr. Emmanuel": {"nombre": "Dr. Emmanuel Tlacaélel López Bermejo", "cedula": "12345678"},
    "Dra. Mónica": {"nombre": "Dra. Mónica Montserrat Rodríguez Álvarez", "cedula": "87654321"}
}
TESTIGOS_DEFAULT = {"t1": "Dra. Mónica Rodríguez", "t2": "Asistente Clínica"}

# RIESGOS BASE (Diccionario)
CLAUSULA_CIERRE = "Adicionalmente, entiendo que pueden presentarse eventos imprevisibles en cualquier acto médico, tales como: reacciones alérgicas, síncope, trismus o hematomas. Acepto que el éxito depende también de seguir las indicaciones."
RIESGOS_DB = {
    "Profilaxis (Limpieza Ultrasónica)": "Sensibilidad dental transitoria; sangrado leve de encías; desalojo de restauraciones antiguas.",
    "Resina Simple (1 cara)": "Sensibilidad postoperatoria; riesgo de pulpitis si caries profunda; desajuste oclusal.",
    "Extracción Simple": "Hemorragia; dolor e inflamación; alveolitis; hematomas; daño a dientes vecinos.",
    "Cirugía de Tercer Molar": "Parestesia (adormecimiento) temporal/permanente; comunicación oroantral; trismus; infección severa.",
    "Endodoncia": "Fractura de instrumentos (limas); perforación; dolor agudo (flare-up); posible fracaso que lleve a extracción.",
    "Corona Zirconia": "Sensibilidad al tallado; retracción gingival; fractura de porcelana; descementado.",
    "Blanqueamiento": "Hipersensibilidad aguda transitoria; irritación de encías; resultado estético variable.",
    "Ortodoncia": "Reabsorción radicular; descalcificación (manchas); inflamación gingival; recidiva si no usa retenedores.",
    "Pulpotomía": "Fracaso por infección recurrente; reabsorción interna; exfoliación prematura.",
    "Garantía": "Aplica solo por defectos de material. NO cubre nuevas caries, fracturas por trauma o mala higiene."
}

def cargar_estilo_royal():
    st.markdown("""
        <style>
        .stApp { background-color: #F4F6F6; }
        .royal-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-bottom: 20px; }
        h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; transition: all 0.3s; }
        .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        input[type=number] { text-align: right; }
        .alerta-medica { background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; border: 1px solid #ef9a9a; font-weight: bold; }
        .success-box { background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; border: 1px solid #c3e6cb; }
        div[data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. BASE DE DATOS
# ==========================================
DB_FILE = "royal_dental_db.sqlite"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def migrar_tablas():
    conn = get_db_connection()
    c = conn.cursor()
    campos = ['antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo', 'domicilio', 'tutor', 'contacto_emergencia', 'ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']
    for col in campos:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
        except: pass
    conn.commit(); conn.close()

def init_db():
    conn = get_db_connection(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (id_paciente TEXT PRIMARY KEY, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT, antecedentes_medicos TEXT, ahf TEXT, app TEXT, apnp TEXT, domicilio TEXT, tutor TEXT, contacto_emergencia TEXT, ocupacion TEXT, estado_civil TEXT, motivo_consulta TEXT, exploracion_fisica TEXT, diagnostico TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas (timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (id_evento INTEGER PRIMARY KEY AUTOINCREMENT, fecha_evento TEXT, usuario TEXT, accion TEXT, detalle TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL)''')
    conn.commit(); conn.close()

def seed_data():
    conn = get_db_connection(); c = conn.cursor(); c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        tratamientos = [("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0),("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0),("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0),("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0),("Cirugía", "Extracción Simple", 900.0, 0.0),("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0),("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0),("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0),("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0),("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0)]
        c.executemany("INSERT INTO servicios VALUES (?,?,?,?)", tratamientos)
        conn.commit()
    conn.close()

init_db(); migrar_tablas(); seed_data()

# ==========================================
# 3. HELPERS
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def sanitizar(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    for old, new in {'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U'}.items(): texto = texto.replace(old, new)
    return " ".join(texto.split())

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)", (datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, sanitizar(detalle)))
        conn.commit(); conn.close()
    except: pass

def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    try:
        nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date() if isinstance(nacimiento_input, str) else nacimiento_input
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return edad, "MENOR" if edad < 18 else "ADULTO"
    except: return 0, "ERROR"

def registrar_movimiento(doctor, tipo):
    conn = get_db_connection(); c = conn.cursor(); hoy = get_fecha_mx(); hora_actual = get_hora_mx()
    try:
        if tipo == "Entrada":
            c.execute("SELECT * FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            if c.fetchone(): return False, "Ya tiene sesión abierta."
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, hora_salida, horas_totales, estado) VALUES (?,?,?,?,?,?)", (hoy, doctor, hora_actual, "", 0, "Pendiente"))
            conn.commit(); return True, f"Entrada: {hora_actual}"
        elif tipo == "Salida":
            c.execute("SELECT id_registro, hora_entrada FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            row = c.fetchone()
            if not row: return False, "No hay entrada."
            id_reg, h_ent = row; fmt = "%H:%M:%S"
            try: tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(h_ent, fmt)
            except: tdelta = timedelta(0)
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=?, estado=? WHERE id_registro=?", (hora_actual, round(tdelta.total_seconds()/3600, 2), "Finalizado", id_reg))
            conn.commit(); return True, f"Salida: {hora_actual}"
    except Exception as e: return False, str(e)
    finally: conn.close()

def generar_slots_tiempo():
    slots = []; hora_actual = datetime.strptime("08:00", "%H:%M"); hora_fin = datetime.strptime("20:00", "%H:%M")
    while hora_actual <= hora_fin: slots.append(hora_actual.strftime("%H:%M")); hora_actual += timedelta(minutes=30)
    return slots

def generar_id_unico(nombre, paterno, nacimiento):
    try:
        nombre = sanitizar(nombre); paterno = sanitizar(paterno)
        part1 = paterno[:3] if len(paterno) >=3 else paterno + "X"; part2 = nombre[0]; part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"

def verificar_disponibilidad(fecha_str, hora_str):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT count(*) FROM citas WHERE fecha=? AND hora=? AND estado_pago != 'CANCELADO'", (fecha_str, hora_str))
    count = c.fetchone()[0]; conn.close()
    return count > 0

# ==========================================
# 4. GENERADOR PDF (LÓGICA MEJORADA)
# ==========================================
class PDFGenerator(FPDF):
    def __init__(self): super().__init__()
    def header(self):
        if os.path.exists(LOGO_FILE):
            try: self.image(LOGO_FILE, 10, 8, 33)
            except: pass
        self.set_font('Arial', 'B', 14); self.set_text_color(0, 43, 91)
        self.cell(0, 10, 'ROYAL DENTAL', 0, 1, 'R'); self.ln(1)
        self.set_font('Arial', 'I', 9); self.set_text_color(100, 100, 100)
        self.cell(0, 5, DIRECCION_CONSULTORIO, 0, 1, 'R'); self.ln(10)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()} - Documento Confidencial', 0, 0, 'C')
    def chapter_body(self, body, style=''):
        self.set_font('Arial', style, 10); self.set_text_color(0, 0, 0); self.multi_cell(0, 5, body); self.ln(2)

def procesar_firma(firma_data):
    if not firma_data: return None
    try:
        img_data = re.sub('^data:image/.+;base64,', '', firma_data)
        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
        fname = f"temp_sig_{int(time.time())}_{random.randint(1,100)}.png"
        img.save(fname); return fname
    except: return None

def crear_pdf_consentimiento(paciente, doctor, cedula, tipo, tratamiento, riesgos, f_pac, f_doc, testigos, edad):
    pdf = PDFGenerator(); pdf.add_page()
    hoy = get_fecha_mx()
    
    if "Aviso" in tipo:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "AVISO DE PRIVACIDAD INTEGRAL", 0, 1, 'C'); pdf.ln(5)
        pdf.chapter_body(f"FECHA: {hoy}\nPACIENTE: {paciente}\n\nEn cumplimiento con la LFPDPPP, ROYAL DENTAL le informa que sus datos personales y sensibles serán tratados para fines clínicos y administrativos.\n\nDERECHOS ARCO: Puede ejercer sus derechos de Acceso, Rectificación, Cancelación y Oposición en la recepción.\n\nCONSENTIMIENTO: Al firmar, acepta el tratamiento de sus datos.")
    else:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "CONSENTIMIENTO INFORMADO", 0, 1, 'C'); pdf.ln(5)
        pdf.chapter_body(f"FECHA: {hoy}\nPACIENTE: {paciente} (Edad: {edad})\nDOCTOR: {doctor} (Céd: {cedula})\nPROCEDIMIENTO: {tratamiento}")
        pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, "RIESGOS Y COMPLICACIONES ADVERTIDOS:", 0, 1)
        pdf.chapter_body(riesgos)
        pdf.chapter_body(CLAUSULA_CIERRE)
        pdf.chapter_body("DECLARACIONES: Entiendo que la medicina no es exacta y no se garantizan resultados. Autorizo anestesia y me comprometo a cuidados post-operatorios.")

    pdf.ln(10); y = pdf.get_y()
    # Firma Paciente
    pdf.set_font('Arial', 'B', 8); pdf.text(20, y+35, "FIRMA PACIENTE")
    fp = procesar_firma(f_pac)
    if fp: pdf.image(fp, x=20, y=y, w=40); os.remove(fp)
    else: pdf.line(20, y+30, 80, y+30)
    
    # Firma Doctor
    pdf.text(120, y+35, "FIRMA DOCTOR")
    fd = procesar_firma(f_doc)
    if fd: pdf.image(fd, x=120, y=y, w=40); os.remove(fd)
    else: pdf.line(120, y+30, 180, y+30)
    
    # Tutor y Testigos
    pdf.ln(45)
    if edad < 18:
        pdf.cell(0, 10, "_______________________________", 0, 1); pdf.cell(0, 5, "FIRMA DEL TUTOR LEGAL", 0, 1)
    
    pdf.ln(5)
    pdf.cell(90, 10, f"Testigo 1: {testigos['t1']}", 0, 0)
    pdf.cell(90, 10, f"Testigo 2: {testigos['t2']}", 0, 1)

    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

def crear_pdf_historia(p, historial):
    pdf = PDFGenerator(); pdf.add_page()
    # Validar None con 'or'
    nombre = f"{p['nombre']} {p['apellido_paterno']} {p['apellido_materno'] or ''}"
    edad, _ = calcular_edad_completa(p['fecha_nacimiento'])
    
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "HISTORIA CLÍNICA (NOM-004)", 0, 1, 'C'); pdf.ln(5)
    pdf.set_fill_color(230, 230, 230); pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "DATOS GENERALES", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, f"Nombre: {nombre}\nEdad: {edad} | Sexo: {p['sexo'] or '-'} | Tel: {p['telefono']}\nTutor: {p['tutor'] or 'N/A'}", 1); pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "ANTECEDENTES CLÍNICOS", 1, 1, 'L', True)
    # ALERTAS EN NEGRITAS
    pdf.set_font('Arial', 'B', 9); pdf.write(5, "APP (Alergias/Enf): "); pdf.set_font('Arial', '', 9); pdf.write(5, f"{p['app'] or 'Negados'}\n")
    pdf.set_font('Arial', 'B', 9); pdf.write(5, "AHF (Hereditarios): "); pdf.set_font('Arial', '', 9); pdf.write(5, f"{p['ahf'] or 'Negados'}\n")
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "NOTAS DE EVOLUCIÓN", 0, 1, 'L')
    if not historial.empty:
        pdf.set_font('Arial', 'B', 8); pdf.cell(25, 6, "FECHA", 1); pdf.cell(60, 6, "TRATAMIENTO", 1); pdf.cell(105, 6, "NOTAS", 1); pdf.ln()
        pdf.set_font('Arial', '', 8)
        for _, row in historial.iterrows():
            pdf.cell(25, 6, str(row['fecha']), 1)
            pdf.cell(60, 6, str(row['tratamiento'])[:35], 1)
            pdf.cell(105, 6, str(row['notas'])[:60], 1); pdf.ln()
            
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

# ==========================================
# 5. MAIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, use_container_width=True)
        st.markdown("<h2 style='text-align:center; color:#002B5B'>ROYAL DENTAL ERP</h2>", unsafe_allow_html=True)
        u = st.selectbox("Usuario", ["Consultorio", "Administración"])
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if u=="Consultorio" and p=="ROYALCLINIC": st.session_state.perfil="Consultorio"; st.rerun()
            elif u=="Administración" and p=="ROYALADMIN": st.session_state.perfil="Admin"; st.rerun()
            else: st.error("Acceso Denegado")

def vista_consultorio():
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_column_width=True)
    menu = st.sidebar.radio("Menú", ["Agenda", "Pacientes", "Finanzas", "Legal", "Asistencia"])
    
    with st.sidebar.expander("Opciones"):
        if st.button("Cerrar Sesión"): st.session_state.perfil=None; st.rerun()
        if st.button("⚠️ Borrar Todo (Reset)"):
            c = get_db_connection().cursor()
            c.execute("DELETE FROM pacientes"); c.execute("DELETE FROM citas"); c.execute("DELETE FROM asistencia")
            get_db_connection().commit(); st.cache_data.clear(); st.success("Sistema Nuevo"); time.sleep(1); st.rerun()
            
    conn = get_db_connection()

    if menu == "Agenda":
        st.title("📅 Agenda")
        c1, c2 = st.columns([1, 2])
        with c1:
            fecha = st.date_input("Fecha", datetime.now(TZ_MX)); f_str = format_date_latino(fecha)
            with st.expander("Nueva Cita", expanded=True):
                with st.form("cita", clear_on_submit=False):
                    p_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                    lp = p_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not p_raw.empty else []
                    p_sel = st.selectbox("Paciente", ["..."]+lp); h = st.selectbox("Hora", generar_slots_tiempo())
                    m = st.text_input("Motivo"); d = st.selectbox("Dr", list(DOCS_INFO.keys()))
                    urg = st.checkbox("Sobrecupo")
                    if st.form_submit_button("Agendar"):
                        oc = verificar_disponibilidad(f_str, h)
                        if oc and not urg: st.error("Horario Ocupado")
                        elif p_sel != "...":
                            c = conn.cursor()
                            c.execute("INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago) VALUES (?,?,?,?,?,?,?,?,?)",
                                      (int(time.time()), f_str, h, p_sel.split(" - ")[0], p_sel.split(" - ")[1], "General", sanitizar(m), d, "Pendiente"))
                            conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()
        with c2:
            st.markdown(f"#### Citas: {f_str}")
            df = pd.read_sql(f"SELECT * FROM citas WHERE fecha='{f_str}'", conn)
            if not df.empty:
                for _, r in df.iterrows():
                    st.info(f"{r['hora']} - {r['nombre_paciente']} ({r['tratamiento']}) - {r['doctor_atendio']}")

    elif menu == "Pacientes":
        st.title("📂 Pacientes"); tab1, tab2 = st.tabs(["Nuevo", "Buscar"])
        with tab1:
            with st.form("alta", clear_on_submit=False): # FORMULARIO BLINDADO
                with st.expander("Datos Personales", expanded=True):
                    c1, c2 = st.columns(2); n = c1.text_input("Nombre"); p = c2.text_input("Apellidos")
                    c3, c4 = st.columns(2); fn = c3.date_input("Nacimiento", datetime(1990,1,1)); sex = c4.selectbox("Sexo", ["Masculino", "Femenino"])
                    tel = st.text_input("Teléfono (10 dígitos)")
                    
                    # LOGICA MENORES
                    edad, tipo_edad = calcular_edad_completa(fn)
                    tutor = st.text_input("Nombre Tutor (Obligatorio)", help="Requerido por ser menor de edad") if edad < 18 else "N/A"
                
                with st.expander("Antecedentes Médicos"):
                    app = st.text_area("Alergias / Enfermedades (APP)", "Negados")
                    ahf = st.text_area("Hereditarios (AHF)", "Negados")
                
                if st.form_submit_button("Guardar"):
                    if not n or not p: st.error("Nombre incompleto")
                    elif edad < 18 and not tutor: st.error("Falta Tutor para menor de edad")
                    else:
                        nid = generar_id_unico(sanitizar(n), sanitizar(p), fn)
                        c = conn.cursor()
                        c.execute("INSERT INTO pacientes (id_paciente, nombre, apellido_paterno, fecha_nacimiento, sexo, telefono, app, ahf, tutor) VALUES (?,?,?,?,?,?,?,?,?)",
                                  (nid, sanitizar(n), sanitizar(p), format_date_latino(fn), sex, tel, sanitizar(app), sanitizar(ahf), sanitizar(tutor)))
                        conn.commit(); st.success("Guardado"); time.sleep(1); st.rerun()
                        
        with tab2:
            p_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not p_raw.empty:
                sel = st.selectbox("Paciente:", ["..."] + p_raw['nombre'].tolist())
                if sel != "...":
                    row = p_raw[p_raw['nombre'] == sel].iloc[0]
                    st.write(f"Edad: {calcular_edad_completa(row['fecha_nacimiento'])[0]} | Tel: {row['telefono']}")
                    hist = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{row['id_paciente']}'", conn)
                    if st.button("📄 PDF Historia Clínica"):
                        pdf = crear_pdf_historia(row, hist)
                        st.download_button("Descargar", pdf, f"Historia_{sel}.pdf", "application/pdf")

    elif menu == "Finanzas":
        st.title("💰 Planes de Tratamiento")
        p_raw = pd.read_sql("SELECT * FROM pacientes", conn)
        s_raw = pd.read_sql("SELECT * FROM servicios", conn)
        
        if not p_raw.empty:
            sel_p = st.selectbox("Paciente:", p_raw['nombre'].tolist())
            id_p = p_raw[p_raw['nombre']==sel_p].iloc[0]['id_paciente']
            
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Categoría", s_raw['categoria'].unique() if not s_raw.empty else ["Manual"])
            trat = c2.selectbox("Tratamiento", s_raw[s_raw['categoria']==cat]['nombre_tratamiento'].unique() if not s_raw.empty else [])
            
            # PRE-LLENADO DE RIESGOS PARA EDICIÓN
            riesgo_auto = RIESGOS_DB.get(trat, "Riesgos generales.")
            riesgo_edit = st.text_area("Riesgos (Editable para Contrato)", value=riesgo_auto)
            
            costo = float(s_raw[s_raw['nombre_tratamiento']==trat].iloc[0]['precio_lista']) if not s_raw.empty else 0.0
            
            with st.form("caja"):
                pf = st.number_input("Precio Final", value=costo); ab = st.number_input("Abono"); sal = pf - ab
                st.metric("Saldo", f"${sal:,.2f}")
                doc = st.selectbox("Doctor", list(DOCS_INFO.keys()))
                
                # VALIDACIÓN DE BOTÓN
                bloqueado = False
                if pf <= 0: st.caption("⚠️ Ingresa un precio válido."); bloqueado = True
                
                if st.form_submit_button("Registrar Cobro", disabled=bloqueado):
                    c = conn.cursor()
                    # Guardamos el riesgo editado en NOTAS para usarlo en el PDF después
                    nota_int = f"Riesgo Legal: {sanitizar(riesgo_edit)}"
                    c.execute("INSERT INTO citas (id_paciente, nombre_paciente, tratamiento, precio_final, monto_pagado, saldo_pendiente, doctor_atendio, notas, fecha, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (id_p, sel_p, trat, pf, ab, sal, doc, nota_int, get_fecha_mx(), int(time.time())))
                    conn.commit(); st.success("Cobrado"); time.sleep(1); st.rerun()

    elif menu == "Legal":
        st.title("⚖️ Documentos")
        p_raw = pd.read_sql("SELECT * FROM pacientes", conn)
        if not p_raw.empty:
            sel_p = st.selectbox("Paciente:", p_raw['nombre'].tolist())
            row_p = p_raw[p_raw['nombre']==sel_p].iloc[0]
            
            tipo = st.selectbox("Documento", ["Consentimiento Informado", "Aviso Privacidad"])
            doc = st.selectbox("Doctor", list(DOCS_INFO.keys()))
            
            # DATOS DINÁMICOS
            trat_pdf = st.selectbox("Tratamiento:", pd.read_sql("SELECT nombre_tratamiento FROM servicios", conn)['nombre_tratamiento'].tolist())
            riesgo_pdf = st.text_area("Riesgos", value=RIESGOS_DB.get(trat_pdf, ""))
            
            # TESTIGOS
            usar_staff = st.checkbox("Usar testigos del personal", value=True)
            if usar_staff: t1, t2 = TESTIGOS_DEFAULT['t1'], TESTIGOS_DEFAULT['t2']
            else: c1, c2 = st.columns(2); t1 = c1.text_input("Testigo 1"); t2 = c2.text_input("Testigo 2")
            
            st.write("Firma Paciente:")
            canvas = st_canvas(stroke_width=2, height=150, key="sig")
            
            # VALIDACIÓN BOTÓN
            if canvas.image_data is not None:
                # Verificamos si dibujó algo (suma de pixeles no blancos)
                if np.sum(canvas.image_data) > 0: 
                    if st.button("Generar PDF"):
                        import io; from PIL import Image
                        img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG")
                        firma_b64 = base64.b64encode(buf.getvalue()).decode()
                        
                        full_doc_name = DOCS_INFO[doc]['nombre']; cedula = DOCS_INFO[doc]['cedula']
                        p_full = f"{row_p['nombre']} {row_p['apellido_paterno']}"
                        edad, _ = calcular_edad_completa(row_p['fecha_nacimiento'])
                        
                        pdf_bytes = crear_pdf_consentimiento(p_full, full_doc_name, cedula, tipo, trat_pdf, riesgo_pdf, firma_b64, None, {'t1':t1, 't2':t2}, edad)
                        
                        # NOMENCLATURA ARCHIVO
                        fname = f"{datetime.now().strftime('%Y%m%d')}_{sanitizar(row_p['apellido_paterno'])}_{tipo.split()[0]}.pdf"
                        st.download_button("📥 Bajar Archivo", pdf_bytes, fname, "application/pdf")
                        
                        # LOG AUDITORÍA
                        registrar_auditoria("Consultorio", "PDF GENERADO", f"{tipo} para {sel_p}")
                else:
                    st.info("Firma en el recuadro para habilitar descarga.")

    elif menu == "Asistencia":
        st.title("⏱️ Checador"); c1, c2 = st.columns(2)
        if c1.button("Entrada"): 
            ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada"); st.success(m) if ok else st.warning(m)
        if c2.button("Salida"): 
            ok, m = registrar_movimiento("Dr. Emmanuel", "Salida"); st.success(m) if ok else st.warning(m)

    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Admin": st.title("Admin"); st.button("Salir", on_click=lambda: st.session_state.perfil=None)
