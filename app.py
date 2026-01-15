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
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')
LOGO_FILE = "logo.png"
DIRECCION_CONSULTORIO = "Calle Ejemplo #123, Col. Centro, Ciudad de México, CP 00000" # <--- ACTUALIZA ESTO

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
        div[data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
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
    conn = get_db_connection()
    c = conn.cursor()
    # Campos Historia Clínica y Legal Completa
    nuevos = ['domicilio', 'tutor', 'contacto_emergencia', 'antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo', 'ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']
    for col in nuevos:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
        except: pass
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT PRIMARY KEY, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT,
        antecedentes_medicos TEXT, ahf TEXT, app TEXT, apnp TEXT,
        domicilio TEXT, tutor TEXT, contacto_emergencia TEXT,
        ocupacion TEXT, estado_civil TEXT, motivo_consulta TEXT, exploracion_fisica TEXT, diagnostico TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (id_evento INTEGER PRIMARY KEY AUTOINCREMENT, fecha_evento TEXT, usuario TEXT, accion TEXT, detalle TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL)''')
    conn.commit()
    conn.close()

def seed_data():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        tratamientos = [("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0),("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0),("Preventiva", "Sellador de Fosetas y Fisuras", 400.0, 0.0),("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0),("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0),("Operatoria", "Reconstrucción de Muñón", 1500.0, 0.0),("Operatoria", "Curación Temporal (Cavit)", 300.0, 0.0),("Cirugía", "Extracción Simple", 900.0, 0.0),("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0),("Cirugía", "Drenaje de Absceso", 800.0, 0.0),("Endodoncia", "Endodoncia Anterior (1 conducto)", 2800.0, 0.0),("Endodoncia", "Endodoncia Premolar (2 conductos)", 3200.0, 0.0),("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0),("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0),("Prótesis Fija", "Corona Metal-Porcelana", 3500.0, 600.0),("Prótesis Fija", "Incrustación Estética", 3800.0, 700.0),("Prótesis Fija", "Carilla de Porcelana", 5500.0, 1100.0),("Prótesis Fija", "Poste de Fibra de Vidrio", 1200.0, 0.0),("Prótesis Removible", "Placa Total (Acrílico) - Una arcada", 6000.0, 1200.0),("Prótesis Removible", "Prótesis Flexible (Valplast) - Unilateral", 4500.0, 900.0),("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0),("Estética", "Blanqueamiento (Guardas en casa)", 2500.0, 500.0),("Ortodoncia", "Pago Inicial (Brackets Metálicos)", 4000.0, 1500.0),("Ortodoncia", "Mensualidad Ortodoncia", 700.0, 0.0),("Ortodoncia", "Recolocación de Bracket (Reposición)", 200.0, 0.0),("Pediatría", "Pulpotomía", 1500.0, 0.0),("Pediatría", "Corona Acero-Cromo", 1800.0, 0.0),("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0)]
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
def limpiar_email(texto): return texto.lower().strip() if texto else ""
def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)", (datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, sanitizar(detalle)))
        conn.commit(); conn.close()
    except: pass
def registrar_movimiento(doctor, tipo):
    conn = get_db_connection(); c = conn.cursor(); hoy = get_fecha_mx(); hora_actual = get_hora_mx()
    try:
        if tipo == "Entrada":
            c.execute("SELECT * FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            if c.fetchone(): return False, "Ya tienes una sesión abierta."
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, hora_salida, horas_totales, estado) VALUES (?,?,?,?,?,?)", (hoy, doctor, hora_actual, "", 0, "Pendiente"))
            conn.commit(); return True, f"Entrada: {hora_actual}"
        elif tipo == "Salida":
            c.execute("SELECT id_registro, hora_entrada FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            row = c.fetchone()
            if not row: return False, "No entrada abierta."
            id_reg, h_ent = row; fmt = "%H:%M:%S"
            try: tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(h_ent, fmt)
            except: tdelta = timedelta(0)
            horas = round(tdelta.total_seconds() / 3600, 2)
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=?, estado=? WHERE id_registro=?", (hora_actual, horas, "Finalizado", id_reg))
            conn.commit(); return True, f"Salida: {hora_actual} ({horas}h)"
    except Exception as e: return False, str(e)
    finally: conn.close()
def format_tel_visual(tel): return f"{tel[:2]}-{tel[2:6]}-{tel[6:]}" if tel and len(tel)==10 else tel
def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    try:
        nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date() if isinstance(nacimiento_input, str) else nacimiento_input
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return edad, "MENOR" if edad < 18 else "ADULTO"
    except: return "N/A", ""
def generar_id_unico(nombre, paterno, nacimiento):
    try:
        nombre = sanitizar(nombre); paterno = sanitizar(paterno)
        part1 = paterno[:3] if len(paterno) >=3 else paterno + "X"; part2 = nombre[0]; part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"
def formatear_telefono_db(numero): return re.sub(r'\D', '', str(numero))
def generar_slots_tiempo():
    slots = []; hora_actual = datetime.strptime("08:00", "%H:%M"); hora_fin = datetime.strptime("20:00", "%H:%M")
    while hora_actual <= hora_fin: slots.append(hora_actual.strftime("%H:%M")); hora_actual += timedelta(minutes=30)
    return slots
def get_regimenes_fiscales(): return ["605 - Sueldos y Salarios", "612 - PFAEP (Actividad Empresarial)", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]
def get_usos_cfdi(): return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]
def verificar_disponibilidad(fecha_str, hora_str):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT count(*) FROM citas WHERE fecha=? AND hora=? AND estado_pago != 'CANCELADO'", (fecha_str, hora_str))
    count = c.fetchone()[0]; conn.close()
    return count > 0
def calcular_rfc_10(nombre, paterno, materno, nacimiento):
    try:
        nombre = sanitizar(nombre); paterno = sanitizar(paterno); materno = sanitizar(materno); fecha = datetime.strptime(str(nacimiento), "%Y-%m-%d")
        letra1 = paterno[0]; vocales = [c for c in paterno[1:] if c in "AEIOU"]; letra2 = vocales[0] if vocales else "X"; letra3 = materno[0] if materno else "X"
        nombres = nombre.split(); letra4 = nombres[1][0] if len(nombres) > 1 and nombres[0] in ["JOSE", "MARIA", "MA.", "MA", "J."] else nombre[0]
        fecha_str = fecha.strftime("%y%m%d"); rfc_base = f"{letra1}{letra2}{letra3}{letra4}{fecha_str}".upper()
        if rfc_base[:4] in ["PUTO", "PITO", "CULO", "MAME"]: rfc_base = f"{rfc_base[:3]}X{rfc_base[4:]}"
        return rfc_base
    except: return ""

# ==========================================
# 4. GENERADOR DE PDF (LEGAL & COMPLIANCE)
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

def crear_pdf_consentimiento(paciente_data, doctor, tipo_doc, tratamiento, riesgos, firma_img_data):
    pdf = PDFGenerator(); pdf.add_page()
    p = paciente_data
    nombre_p = f"{p['nombre']} {p['apellido_paterno']} {p.get('apellido_materno','')}"
    edad, _ = calcular_edad_completa(p.get('fecha_nacimiento', ''))
    
    if "Aviso" in tipo_doc:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "AVISO DE PRIVACIDAD INTEGRAL PARA PACIENTES", 0, 1, 'C'); pdf.ln(5)
        texto = f"""En cumplimiento estricto con lo dispuesto por la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (la "Ley"), ROYAL DENTAL, con domicilio en {DIRECCION_CONSULTORIO}, es el responsable del uso y protección de sus datos personales.

DATOS QUE RECABAMOS: Nombre, edad, sexo, domicilio, teléfono, RFC, ocupación y DATOS SENSIBLES DE SALUD (Historia clínica, radiografías, antecedentes).

FINALIDADES: A) Prestación de servicios odontológicos. B) Creación del expediente clínico (NOM-004-SSA3-2012). C) Facturación. D) Seguimiento post-operatorio.

DERECHOS ARCO: Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse al tratamiento de sus datos presentando solicitud en recepción.

CONSENTIMIENTO: Consiento que mis datos sensibles sean tratados conforme a este aviso. Reconozco que la firma digital plasmada tiene validez legal."""
        pdf.chapter_body(texto)
    else:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "CARTA DE CONSENTIMIENTO INFORMADO", 0, 1, 'C'); pdf.ln(5)
        texto = f"""LUGAR Y FECHA: Ciudad de México, a {get_fecha_mx()}
NOMBRE DEL PACIENTE: {nombre_p}
EDAD: {edad} Años | EXPEDIENTE: {p['id_paciente']}

DECLARACIÓN DEL PACIENTE:
Yo, el paciente arriba mencionado (o mi tutor), declaro que he recibido del {doctor} una explicación clara sobre mi diagnóstico y el plan de tratamiento.

PROCEDIMIENTO A REALIZAR: {tratamiento}

RIESGOS Y COMPLICACIONES ADVERTIDOS:
{riesgos if riesgos else 'Riesgos generales inherentes al procedimiento (dolor, inflamación, infección).'}

DECLARACIONES LEGALES:
1. OBLIGACIÓN DE MEDIOS: Entiendo que la Odontología no es una ciencia exacta y el profesional se compromete a usar todos los medios técnicos, pero no puede garantizar resultados biológicos al 100%.
2. ANESTESIA: Autorizo la administración de anestesia local y asumo sus riesgos inherentes.
3. CUIDADOS: Me comprometo a seguir las instrucciones post-operatorias. Asumo responsabilidad por negligencia en mis cuidados.
4. REVOCACIÓN: Sé que puedo revocar este consentimiento antes de iniciar el procedimiento.

OTORGO MI CONSENTIMIENTO TOTAL PARA SER SOMETIDO AL PROCEDIMIENTO."""
        pdf.chapter_body(texto)

    pdf.ln(15); pdf.cell(0, 10, "FIRMA DE CONFORMIDAD:", 0, 1)
    if firma_img_data:
        try:
            img_data = re.sub('^data:image/.+;base64,', '', firma_img_data); img = Image.open(io.BytesIO(base64.b64decode(img_data)))
            temp_filename = f"temp_sig_{int(time.time())}.png"; img.save(temp_filename); pdf.image(temp_filename, x=10, w=60)
        except: pass
    
    # FIRMA TUTOR SI ES MENOR
    if edad != "N/A" and isinstance(edad, int) and edad < 18:
        pdf.ln(15); pdf.cell(0, 10, "______________________________________", 0, 1)
        pdf.cell(0, 5, f"NOMBRE Y FIRMA DEL TUTOR: {p.get('tutor', '__________________')}", 0, 1)

    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

def crear_pdf_historia(p, historial):
    pdf = PDFGenerator(); pdf.add_page()
    nombre_p = f"{p['nombre']} {p['apellido_paterno']} {p.get('apellido_materno','')}"
    edad, _ = calcular_edad_completa(p.get('fecha_nacimiento', ''))
    
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "HISTORIA CLÍNICA ODONTOLÓGICA (NOM-004-SSA3-2012)", 0, 1, 'C'); pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230); pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "I. FICHA DE IDENTIFICACIÓN", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    info = f"""Nombre: {nombre_p}\nEdad: {edad} | Sexo: {p.get('sexo','N/A')} | Nacimiento: {p.get('fecha_nacimiento','N/A')}\nOcupación: {p.get('ocupacion','N/A')} | Estado Civil: {p.get('estado_civil','N/A')}\nDomicilio: {p.get('domicilio','N/A')}\nTel: {p['telefono']} | Email: {p.get('email','N/A')}\nContacto Emergencia: {p.get('contacto_emergencia','N/A')}"""
    pdf.multi_cell(0, 5, info, 1); pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "II. ANTECEDENTES (ANAMNESIS)", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    ant = f"""HEREDO-FAMILIARES (AHF): {p.get('ahf','Negados')}\n\nPERSONALES PATOLÓGICOS (APP - Alergias/Enf): {p.get('app','Negados')}\n\nNO PATOLÓGICOS (APNP): {p.get('apnp','Negados')}"""
    pdf.multi_cell(0, 5, ant, 1); pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "III. MOTIVO DE CONSULTA Y DIAGNÓSTICO", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    diag = f"""Motivo: {p.get('motivo_consulta','N/A')}\n\nExploración Física: {p.get('exploracion_fisica','N/A')}\n\nDiagnóstico: {p.get('diagnostico','N/A')}"""
    pdf.multi_cell(0, 5, diag, 1); pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "IV. NOTAS DE EVOLUCIÓN", 0, 1, 'L')
    if not historial.empty:
        pdf.set_font('Arial', 'B', 8); pdf.cell(25, 6, "FECHA", 1); pdf.cell(60, 6, "TRATAMIENTO", 1); pdf.cell(105, 6, "NOTAS / EVOLUCIÓN", 1); pdf.ln()
        pdf.set_font('Arial', '', 8)
        for _, row in historial.iterrows():
            pdf.cell(25, 6, str(row['fecha']), 1)
            pdf.cell(60, 6, str(row['tratamiento'])[:35], 1)
            pdf.cell(105, 6, str(row['notas'])[:60], 1); pdf.ln()
            
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, use_container_width=True)
        st.markdown("""<h1 style='text-align: center; color: #002B5B;'>ROYAL DENTAL</h1>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", type="primary", use_container_width=True):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC": st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN": st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("Acceso Denegado")

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_column_width=True)
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Documentos & Firmas", "5. Control Asistencia"])
    
    with st.sidebar.expander("🛠️ Mantenimiento"):
        if st.button("🗑️ RESETEAR BASE DE DATOS", type="primary"):
            c = get_db_connection().cursor()
            c.execute("DELETE FROM pacientes"); c.execute("DELETE FROM citas"); c.execute("DELETE FROM asistencia")
            get_db_connection().commit(); st.cache_data.clear(); st.success("Sistema limpio."); time.sleep(1); st.rerun()

    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    conn = get_db_connection()

    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        with st.expander("🔍 BUSCAR"):
            q = st.text_input("Buscar cita:"); 
            if q: st.dataframe(pd.read_sql(f"SELECT fecha, hora, nombre_paciente, estado_pago FROM citas WHERE nombre_paciente LIKE '%{sanitizar(q)}%' ORDER BY timestamp DESC", conn))

        col_cal1, col_cal2 = st.columns([1, 2.5])
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver = st.date_input("Fecha", datetime.now(TZ_MX)); fecha_str = format_date_latino(fecha_ver)
            with st.expander("➕ Agendar Cita", expanded=False):
                with st.form("cita_reg", clear_on_submit=False):
                    pacientes = pd.read_sql("SELECT * FROM pacientes", conn)
                    lp = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not pacientes.empty else []
                    p_sel = st.selectbox("Paciente", ["..."]+lp); h = st.selectbox("Hora", generar_slots_tiempo()); m = st.text_input("Motivo"); d = st.selectbox("Dr", ["Dr. Emmanuel", "Dra. Mónica"]); urg = st.checkbox("Urgencia/Sobrecupo")
                    if st.form_submit_button("Agendar"):
                        oc = verificar_disponibilidad(fecha_str, h)
                        if oc and not urg: st.error("Horario Ocupado")
                        elif p_sel != "...":
                            c = conn.cursor()
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                      (int(time.time()), fecha_str, h, p_sel.split(" - ")[0], p_sel.split(" - ")[1], "General", sanitizar(m), d, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General"))
                            conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()

            st.markdown("### 🔄 Modificar")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            if not df_c.empty:
                df_d = df_c[df_c['fecha'] == fecha_str]
                if not df_d.empty:
                    lc = [f"{r['hora']} - {r['nombre_paciente']}" for i, r in df_d.iterrows()]
                    sel = st.selectbox("Cita:", ["..."]+lc)
                    if sel != "...":
                        h_t = sel.split(" - ")[0]; n_t = sel.split(" - ")[1]
                        if st.button("❌ Cancelar"):
                            c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_str, h_t, n_t)); conn.commit(); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 {fecha_str}")
            if not df_c.empty:
                df_d = df_c[df_c['fecha'] == fecha_str]
                for s in generar_slots_tiempo():
                    oc = df_d[(df_d['hora'] == s) & (df_d['estado_pago'] != 'CANCELADO')]
                    if oc.empty: st.markdown(f"<div style='color:#ccc; border-bottom:1px solid #eee;'>{s} Disponible</div>", unsafe_allow_html=True)
                    else: 
                        for _, r in oc.iterrows(): st.markdown(f"<div style='background:#e3f2fd; padding:5px; border-left:4px solid #1976d2;'><b>{s} {r['nombre_paciente']}</b><br><small>{r['tratamiento']}</small></div>", unsafe_allow_html=True)

    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico")
        tab_b, tab_n, tab_e = st.tabs(["BUSCAR", "NUEVO", "EDITAR"])
        with tab_b:
            df_p = pd.read_sql("SELECT * FROM pacientes", conn)
            if not df_p.empty:
                sel = st.selectbox("Paciente:", ["..."] + df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
                if sel != "...":
                    p = df_p[df_p['id_paciente'] == sel.split(" - ")[0]].iloc[0]
                    hist = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{p['id_paciente']}' ORDER BY timestamp DESC", conn)
                    st.write(f"👤 {p['nombre']} {p['apellido_paterno']} | Tel: {p['telefono']}")
                    if st.button("🖨️ Imprimir Historia Clínica"):
                        pdf = crear_pdf_historia(p, hist); st.download_button("Descargar PDF", pdf, "Historia.pdf", "application/pdf")
        
        with tab_n:
            st.markdown("#### Alta de Paciente")
            with st.form("alta", clear_on_submit=False):
                c1, c2, c3 = st.columns(3); n = c1.text_input("Nombre"); p = c2.text_input("Paterno"); m = c3.text_input("Materno")
                c4, c5, c6 = st.columns(3); fn = c4.date_input("Nacimiento", datetime(1990,1,1)); tel = c5.text_input("Tel"); mail = c6.text_input("Email")
                c7, c8 = st.columns(2); sx = c7.selectbox("Sexo", ["Mujer", "Hombre"]); ec = c8.selectbox("Estado Civil", ["Soltero", "Casado"])
                col_dom = st.columns(1); dom = col_dom[0].text_input("Domicilio Completo")
                c9, c10 = st.columns(2); emer = c9.text_input("Contacto Emergencia"); tutor = c10.text_input("Tutor (si es menor)")
                st.markdown("**Clínico:**")
                ahf = st.text_area("AHF"); app = st.text_area("APP"); apnp = st.text_area("APNP")
                if st.form_submit_button("Guardar"):
                    if n and p and len(tel)==10:
                        nid = generar_id_unico(sanitizar(n), sanitizar(p), fn)
                        c = conn.cursor()
                        # INSERT CON NUEVOS CAMPOS
                        c.execute("INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, email, sexo, fecha_nacimiento, domicilio, contacto_emergencia, tutor, ahf, app, apnp, estado_civil) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (nid, get_fecha_mx(), sanitizar(n), sanitizar(p), sanitizar(m), tel, mail, sx, format_date_latino(fn), sanitizar(dom), sanitizar(emer), sanitizar(tutor), sanitizar(ahf), sanitizar(app), sanitizar(apnp), ec))
                        conn.commit(); st.success("Guardado"); time.sleep(1); st.rerun()
                    else: st.error("Datos incompletos")

    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes"); df_p = pd.read_sql("SELECT * FROM pacientes", conn); df_s = pd.read_sql("SELECT * FROM servicios", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", df_p['nombre'].tolist())
            c1, c2 = st.columns(2)
            if not df_s.empty:
                cat = c1.selectbox("Categoría", df_s['categoria'].unique()); filt = df_s[df_s['categoria']==cat]
                trat = c2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                row = filt[filt['nombre_tratamiento']==trat].iloc[0]; precio = row['precio_lista']
            
            with st.form("cobro"):
                pf = st.number_input("Precio", value=float(precio)); ab = st.number_input("Abono"); sal = pf - ab
                doc = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"]); met = st.selectbox("Método", ["Efectivo", "Tarjeta"])
                # AGREGADO RIESGOS ESPECIFICOS PARA EL PDF (Solo informativo aqui, se guarda en notas)
                riesgos = st.text_input("Riesgos Específicos (Para Consentimiento)")
                if st.form_submit_button("Registrar"):
                    c = conn.cursor(); c.execute("INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tratamiento, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                                 (int(time.time()), get_fecha_mx(), get_hora_mx(), "ID_PEND", sel, trat, pf, ab, sal, "Pendiente", riesgos))
                    conn.commit(); st.success("Registrado")

    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Legal"); df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", ["..."]+df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']}", axis=1).tolist())
            if sel != "...":
                id_target = sel.split(" - ")[0]; p = df_p[df_p['id_paciente'] == id_target].iloc[0]
                tdoc = st.selectbox("Documento:", ["Consentimiento Informado", "Aviso de Privacidad"])
                doc = st.selectbox("Doctor:", ["Dr. Emmanuel", "Dra. Mónica"])
                trat = st.text_input("Tratamiento (Solo Consentimiento)")
                riesgos = st.text_area("Riesgos Específicos (Solo Consentimiento)")
                
                canvas = st_canvas(stroke_width=2, height=150, key="sig")
                if st.button("Generar PDF"):
                    if canvas.image_data is not None:
                        import numpy as np; from PIL import Image; import io
                        img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG")
                        img_str = base64.b64encode(buf.getvalue()).decode()
                        pdf = crear_pdf_consentimiento(p, doc, tdoc, trat, riesgos, img_str)
                        st.download_button("Descargar PDF", pdf, "Legal.pdf", "application/pdf")

    elif menu == "5. Control Asistencia":
        st.title("⏱️ Checador")
        if st.button("Entrada"): ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada"); st.success(m) if ok else st.warning(m)
        if st.button("Salida"): ok, m = registrar_movimiento("Dr. Emmanuel", "Salida"); st.success(m) if ok else st.warning(m)
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Administracion": st.title("Admin"); st.button("Salir", on_click=lambda: st.session_state.update(perfil=None))
