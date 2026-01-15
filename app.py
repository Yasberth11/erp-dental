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
# 0. CONFIGURACIÓN GLOBAL Y CONSTANTES
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')
LOGO_FILE = "logo.png" # Asegúrate de que este archivo exista en la misma carpeta
DOC_EMMANUEL = "Dr. Emmanuel Tlacaélel López Bermejo"
DOC_MONICA = "Dra. Mónica Montserrat Rodríguez Álvarez"
LISTA_DOCTORES = [DOC_EMMANUEL, DOC_MONICA]

# ==========================================
# 1. ESTILO Y HELPERS VISUALES
# ==========================================
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
    """Actualiza la DB con nuevos campos si no existen"""
    conn = get_db_connection()
    c = conn.cursor()
    # Nuevos campos para Historia Clínica Completa
    nuevos_campos_pacientes = ['ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']
    for col in nuevos_campos_pacientes:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass

    # Campos previamente añadidos (doble verificación)
    for col in ['antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo']:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    
    # Campos Citas
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
        except: pass
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla Pacientes Expandida
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT PRIMARY KEY, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT,
        antecedentes_medicos TEXT, ahf TEXT, app TEXT, apnp TEXT,
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
# 3. HELPERS Y FUNCIONES DE SOPORTE
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def sanitizar(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    for old, new in {'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U'}.items(): 
        texto = texto.replace(old, new)
    return " ".join(texto.split())

def limpiar_email(texto): 
    if not texto: return ""
    texto = str(texto).lower().strip()
    for old, new in {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ü':'u','ñ':'n'}.items():
        texto = texto.replace(old, new)
    return texto

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)", (datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, sanitizar(detalle)))
        conn.commit(); conn.close()
    except: pass

def registrar_movimiento(doctor, tipo):
    conn = get_db_connection(); c = conn.cursor()
    hoy = get_fecha_mx(); hora_actual = get_hora_mx()
    try:
        if tipo == "Entrada":
            c.execute("SELECT * FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            if c.fetchone(): return False, "Ya tienes una sesión abierta."
            c.execute("INSERT INTO asistencia (fecha, doctor, hora_entrada, hora_salida, horas_totales, estado) VALUES (?,?,?,?,?,?)", (hoy, doctor, hora_actual, "", 0, "Pendiente"))
            conn.commit(); return True, f"Entrada registrada: {hora_actual}"
        elif tipo == "Salida":
            c.execute("SELECT id_registro, hora_entrada FROM asistencia WHERE doctor=? AND fecha=? AND hora_salida = ''", (doctor, hoy))
            row = c.fetchone()
            if not row: return False, "No tienes una entrada abierta hoy."
            id_reg, h_ent = row
            fmt = "%H:%M:%S"
            try: tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(h_ent, fmt)
            except: tdelta = timedelta(0)
            horas = round(tdelta.total_seconds() / 3600, 2)
            c.execute("UPDATE asistencia SET hora_salida=?, horas_totales=?, estado=? WHERE id_registro=?", (hora_actual, horas, "Finalizado", id_reg))
            conn.commit(); return True, f"Salida registrada: {hora_actual} ({horas} horas)"
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
        nombre = sanitizar(nombre); paterno = sanitizar(paterno); materno = sanitizar(materno)
        fecha = datetime.strptime(str(nacimiento), "%Y-%m-%d")
        letra1 = paterno[0]; vocales = [c for c in paterno[1:] if c in "AEIOU"]; letra2 = vocales[0] if vocales else "X"
        letra3 = materno[0] if materno else "X"
        nombres = nombre.split(); letra4 = nombres[1][0] if len(nombres) > 1 and nombres[0] in ["JOSE", "MARIA", "MA.", "MA", "J."] else nombre[0]
        fecha_str = fecha.strftime("%y%m%d")
        rfc_base = f"{letra1}{letra2}{letra3}{letra4}{fecha_str}".upper()
        if rfc_base[:4] in ["PUTO", "PITO", "CULO", "MAME", "CACA", "PENE"]: rfc_base = f"{rfc_base[:3]}X{rfc_base[4:]}"
        return rfc_base
    except: return ""

# ==========================================
# 4. GENERADOR DE PDF PROFESIONALES
# ==========================================
class PDFGenerator(FPDF):
    def __init__(self): super().__init__()
    def header(self):
        # LOGO PROFESIONAL
        if os.path.exists(LOGO_FILE):
            try: self.image(LOGO_FILE, 10, 8, 33)
            except: pass
        self.set_font('Arial', 'B', 16); self.set_text_color(0, 43, 91)
        self.cell(0, 10, 'ROYAL DENTAL', 0, 1, 'R'); self.ln(1)
        self.set_font('Arial', 'I', 10); self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'Odontología Integral y Especializada', 0, 1, 'R')
        self.line(10, 30, 200, 30); self.ln(15)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()} - Documento Confidencial - Royal Dental', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12); self.set_text_color(0, 43, 91)
        self.cell(0, 10, title.upper(), 0, 1, 'L'); self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10); self.set_text_color(0, 0, 0); self.multi_cell(0, 6, body); self.ln()

    def safe_cell(self, w, h, txt, border=0, ln=0, align='', fill=False):
        try: txt = txt.encode('latin-1', 'replace').decode('latin-1')
        except: pass
        self.cell(w, h, txt, border, ln, align, fill)

def crear_pdf_consentimiento(paciente_full_name, doctor, tipo_doc, tratamiento, firma_img_data):
    pdf = PDFGenerator(); pdf.add_page()
    fecha_hoy = get_fecha_mx()
    
    if "Aviso" in tipo_doc:
        pdf.chapter_title("Aviso de Privacidad Simplificado")
        cuerpo = f"""FECHA: {fecha_hoy}\n\nESTIMADO(A) PACIENTE: {paciente_full_name}\n\nEn cumplimiento con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP), Royal Dental, con domicilio en [Domicilio del Consultorio], le informa que sus datos personales, incluyendo los sensibles relacionados con su salud, serán tratados con la finalidad de prestarle servicios odontológicos integrales, integrar su expediente clínico, y para fines administrativos y de facturación relacionados con dichos servicios.\n\nSus datos serán resguardados bajo estrictas medidas de seguridad. Usted cuenta con los derechos de Acceso, Rectificación, Cancelación y Oposición (ARCO), los cuales podrá ejercer presentando su solicitud por escrito en nuestra recepción.\n\nAl firmar el presente, otorga su consentimiento expreso para el tratamiento de sus datos personales sensibles para los fines descritos."""
    else:
        pdf.chapter_title(f"Consentimiento Informado - {tratamiento}")
        cuerpo = f"""FECHA: {fecha_hoy}\n\nYO, {paciente_full_name}, en pleno uso de mis facultades, otorgo mi consentimiento al {doctor} y al personal de Royal Dental para realizar el procedimiento de: {tratamiento}.\n\nDECLARO QUE:\n1. He recibido una explicación clara y comprensible sobre la naturaleza, propósito, beneficios esperados y posibles riesgos y complicaciones del procedimiento propuesto.\n2. He tenido la oportunidad de hacer preguntas y todas han sido respondidas a mi satisfacción.\n3. Entiendo que la odontología no es una ciencia exacta y, por lo tanto, no se me han dado garantías absolutas sobre los resultados.\n4. Autorizo la administración de la anestesia local necesaria, comprendiendo sus riesgos inherentes.\n5. Me comprometo a seguir fielmente las instrucciones y cuidados post-operatorios indicados por el profesional para favorecer mi recuperación.\n\nEste consentimiento es revocable por mí en cualquier momento antes del inicio del procedimiento."""
        
    pdf.chapter_body(cuerpo)
    pdf.ln(20)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, "FIRMA DE CONFORMIDAD DEL PACIENTE:", 0, 1, 'L')
    
    if firma_img_data:
        try:
            img_data = re.sub('^data:image/.+;base64,', '', firma_img_data); img = Image.open(io.BytesIO(base64.b64decode(img_data)))
            temp_filename = f"temp_sig_{int(time.time())}.png"; img.save(temp_filename); pdf.image(temp_filename, x=10, w=60)
            pdf.ln(5)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, f"Firma digital capturada el {fecha_hoy}", 0, 1, 'L')
        except: pdf.cell(0, 10, "[Error al procesar la imagen de la firma]", 0, 1)
    else:
        pdf.ln(15); pdf.line(10, pdf.get_y(), 80, pdf.get_y()); pdf.ln(2); pdf.cell(0, 10, "Nombre y Firma", 0, 1)
        
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

def crear_pdf_historia(paciente_data, historial_citas):
    pdf = PDFGenerator(); pdf.add_page()
    p = paciente_data
    nombre_completo = f"{p['nombre']} {p['apellido_paterno']} {p.get('apellido_materno', '')}".strip()
    edad_str, tipo_edad = calcular_edad_completa(p.get('fecha_nacimiento', ''))
    fecha_hoy = get_fecha_mx()

    pdf.chapter_title("EXPEDIENTE CLÍNICO ODONTOLÓGICO (NOM-004-SSA3-2012)")
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, f"Fecha de Impresión: {fecha_hoy} | ID: {p['id_paciente']}", 0, 1, 'R'); pdf.ln(5)

    # SECCIÓN 1: FICHA DE IDENTIFICACIÓN
    pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "1. FICHA DE IDENTIFICACIÓN", 0, 1, 'L', True); pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    pdf.safe_cell(95, 7, f"Nombre: {nombre_completo}", 1); pdf.safe_cell(95, 7, f"Sexo: {p.get('sexo', 'N/A')}", 1, 1)
    pdf.safe_cell(95, 7, f"Edad: {edad_str} Años ({tipo_edad})", 1); pdf.safe_cell(95, 7, f"F. Nacimiento: {format_date_latino(datetime.strptime(p['fecha_nacimiento'], '%Y-%m-%d')) if p.get('fecha_nacimiento') else 'N/A'}", 1, 1)
    pdf.safe_cell(95, 7, f"Teléfono: {format_tel_visual(p.get('telefono', ''))}", 1); pdf.safe_cell(95, 7, f"Email: {p.get('email', 'N/A')}", 1, 1)
    pdf.safe_cell(95, 7, f"Ocupación: {p.get('ocupacion', 'N/A')}", 1); pdf.safe_cell(95, 7, f"Estado Civil: {p.get('estado_civil', 'N/A')}", 1, 1)
    pdf.ln(5)

    # SECCIÓN 2: MOTIVO DE CONSULTA
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "2. MOTIVO DE CONSULTA", 0, 1, 'L', True); pdf.ln(2)
    pdf.chapter_body(p.get('motivo_consulta', 'Sin registro.'))
    pdf.ln(3)

    # SECCIÓN 3: ANTECEDENTES HEREDO-FAMILIARES Y PERSONALES
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "3. HISTORIA MÉDICA (ANAMNESIS)", 0, 1, 'L', True); pdf.ln(2)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, "Antecedentes Heredo-Familiares (AHF):", 0, 1)
    pdf.chapter_body(p.get('ahf', 'Negados.')); pdf.ln(2)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, "Antecedentes Personales Patológicos (APP - Alergias, Enf. Sistémicas):", 0, 1)
    pdf.chapter_body(p.get('app', 'Negados.')); pdf.ln(2)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, "Antecedentes Personales No Patológicos (APNP - Hábitos):", 0, 1)
    pdf.chapter_body(p.get('apnp', 'Sin datos relevantes.')); pdf.ln(5)

    # SECCIÓN 4: EXPLORACIÓN FÍSICA Y DIAGNÓSTICO
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "4. EXPLORACIÓN FÍSICA Y DIAGNÓSTICO INICIAL", 0, 1, 'L', True); pdf.ln(2)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, "Hallazgos de Exploración:", 0, 1)
    pdf.chapter_body(p.get('exploracion_fisica', 'Sin registro.')); pdf.ln(2)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, "Diagnóstico Presuntivo:", 0, 1)
    pdf.chapter_body(p.get('diagnostico', 'Pendiente.')); pdf.ln(5)

    # SECCIÓN 5: NOTAS DE EVOLUCIÓN (HISTORIAL DE CITAS)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "5. NOTAS DE EVOLUCIÓN Y TRATAMIENTOS", 0, 1, 'L', True); pdf.ln(2)
    if not historial_citas.empty:
        pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(220, 220, 220)
        pdf.cell(25, 8, 'FECHA', 1, 0, 'C', True); pdf.cell(60, 8, 'TRATAMIENTO', 1, 0, 'C', True); pdf.cell(35, 8, 'DOCTOR', 1, 0, 'C', True); pdf.cell(70, 8, 'NOTAS DE EVOLUCIÓN', 1, 1, 'C', True)
        pdf.set_font('Arial', '', 9)
        for _, row in historial_citas.iterrows():
            pdf.safe_cell(25, 8, str(row['fecha']), 1, 0, 'C')
            pdf.safe_cell(60, 8, str(row['tratamiento'])[:35], 1)
            pdf.safe_cell(35, 8, str(row['doctor_atendio']).replace("Dr. Emmanuel Tlacaélel López Bermejo", "Dr. Emmanuel").replace("Dra. Mónica Montserrat Rodríguez Álvarez", "Dra. Mónica"), 1, 0, 'C')
            pdf.safe_cell(70, 8, str(row['notas'])[:50], 1, 1)
    else:
        pdf.chapter_body("No hay registros de evolución.")
            
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=200)
        st.markdown("""<div style="background-color: #002B5B; padding: 30px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div><br>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC": st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN": st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("Acceso Denegado")

# ==========================================
# 6. VISTA CONSULTORIO (MAIN)
# ==========================================
def vista_consultorio():
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_column_width=True)
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()} (CDMX)")
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Documentos & Firmas", "5. Control Asistencia"])
    
    with st.sidebar.expander("🛠️ Mantenimiento"):
        if st.button("🗑️ RESETEAR BASE DE DATOS (CUIDADO)", type="primary"):
            c = get_db_connection().cursor()
            c.execute("DELETE FROM pacientes"); c.execute("DELETE FROM citas"); c.execute("DELETE FROM asistencia")
            get_db_connection().commit(); st.cache_data.clear(); st.error("BASE DE DATOS LIMPIA. Reiniciando..."); time.sleep(1); st.rerun()

    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    conn = get_db_connection()

    # --- MÓDULO 1: AGENDA ---
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        with st.expander("🔍 BUSCAR CITAS", expanded=False):
            q_cita = st.text_input("Buscar cita por nombre:")
            if q_cita:
                df = pd.read_sql(f"SELECT fecha, hora, nombre_paciente, tratamiento, doctor_atendio, estado_pago FROM citas WHERE nombre_paciente LIKE '%{sanitizar(q_cita)}%' ORDER BY timestamp DESC", conn)
                st.dataframe(df)

        col_cal1, col_cal2 = st.columns([1, 2.5])
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            with st.expander("➕ Agendar Cita Nueva", expanded=False):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                with tab_reg:
                    with st.form("cita_registrada", clear_on_submit=False):
                        pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno, apellido_materno FROM pacientes", conn)
                        lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']} {x.get('apellido_materno','')}".strip(), axis=1).tolist() if not pacientes_raw.empty else []
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        h_sel = st.selectbox("Hora", generar_slots_tiempo()); m_sel = st.text_input("Motivo", "Revisión / Continuación")
                        d_sel = st.selectbox("Doctor", LISTA_DOCTORES); urgencia = st.checkbox("🚨 Es Urgencia / Sobrecupo")
                        if st.form_submit_button("Agendar"):
                            ocupado = verificar_disponibilidad(fecha_ver_str, h_sel)
                            if ocupado and not urgencia: st.error(f"⚠️ Horario {h_sel} OCUPADO.")
                            elif p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]; nom_p = p_sel.split(" - ")[1]
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", sanitizar(m_sel), d_sel, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General"))
                                conn.commit(); st.success(f"Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Seleccione paciente")
                with tab_new:
                    with st.form("cita_prospecto", clear_on_submit=False):
                        nombre_pros = st.text_input("Nombre Completo"); tel_pros = st.text_input("Tel (10)", max_chars=10)
                        hora_pros = st.selectbox("Hora", generar_slots_tiempo()); motivo_pros = st.text_input("Motivo", "Revisión 1ra Vez")
                        doc_pros = st.selectbox("Doctor", LISTA_DOCTORES); urgencia_p = st.checkbox("🚨 Es Urgencia")
                        if st.form_submit_button("Agendar Prospecto"):
                            ocupado = verificar_disponibilidad(fecha_ver_str, hora_pros)
                            if ocupado and not urgencia_p: st.error(f"⚠️ Horario {hora_pros} OCUPADO.")
                            elif nombre_pros and len(tel_pros) == 10:
                                id_temp = f"PROS-{int(time.time())}"; nom_final = sanitizar(nombre_pros)
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", sanitizar(motivo_pros), doc_pros, 0, 0, 0, "Pendiente", f"Tel: {tel_pros}", 0, 0, "No", 0, 0, "", "No", "", 0, "Primera Vez"))
                                conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Datos incorrectos")
            
            st.markdown("### 🔄 Modificar Agenda")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                if not df_dia.empty:
                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['estado_pago']})" for i, r in df_dia.iterrows()]
                    cita_sel = st.selectbox("Seleccionar Cita:", ["Seleccionar..."] + lista_citas_dia)
                    if cita_sel != "Seleccionar...":
                        hora_target = cita_sel.split(" - ")[0]; nom_target = cita_sel.split(" - ")[1].split(" (")[0]
                        c_move, c_cancel, c_delete = st.columns(3)
                        with c_move:
                            new_date_res = st.date_input("Nueva Fecha", datetime.now(TZ_MX)); new_h_res = st.selectbox("Nueva Hora", generar_slots_tiempo(), key="reag_time")
                            if st.button("🗓️ Mover"):
                                c = conn.cursor(); c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", (format_date_latino(new_date_res), new_h_res, fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.success(f"Reagendada para: {new_date_str}"); time.sleep(1); st.rerun()
                        with c_cancel:
                             st.write(""); st.write(""); 
                             if st.button("❌ Cancelar", type="secondary"):
                                c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.warning("Cancelada"); time.sleep(1); st.rerun()
                        with c_delete:
                             st.write(""); st.write(""); 
                             if st.button("🗑️ Eliminar Def.", type="primary"):
                                c = conn.cursor(); c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                conn.commit(); registrar_auditoria("Consultorio", "ELIMINACION CITA", f"Se eliminó cita de {nom_target}"); st.error("Eliminado."); time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                slots = generar_slots_tiempo()
                for slot in slots:
                    ocupado = df_dia[(df_dia['hora'] == slot) & (df_dia['estado_pago'] != 'CANCELADO')]
                    if ocupado.empty: st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)
                    else:
                        for _, r in ocupado.iterrows():
                            color = "#FF5722" if "PROS" in str(r['id_paciente']) else "#002B5B"
                            doc_corto = "Dr. Emmanuel" if "Emmanuel" in r['doctor_atendio'] else "Dra. Mónica"
                            st.markdown(f"""<div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;"><b>{slot} | {r['nombre_paciente']}</b><br><span style="color:#666; font-size:0.9em;">{r['tratamiento']} - {doc_corto}</span></div>""", unsafe_allow_html=True)

    # --- MÓDULO 2: PACIENTES (EXPANDIDO) ---
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico Completo")
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR/IMPRIMIR", "➕ NUEVO (ALTA)", "✏️ EDITAR COMPLETO"])
        with tab_b:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_busqueda = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']} {x.get('apellido_materno','')}".strip(), axis=1).tolist()
                seleccion = st.selectbox("Seleccionar:", ["..."] + lista_busqueda)
                if seleccion != "...":
                    id_sel_str = seleccion.split(" - ")[0]; p_data = pacientes_raw[pacientes_raw['id_paciente'] == id_sel_str].iloc[0]
                    edad, tipo_pac = calcular_edad_completa(p_data.get('fecha_nacimiento', ''))
                    antecedentes = p_data.get('app', '') 
                    if antecedentes: st.markdown(f"<div class='alerta-medica'>⚠️ ALERTA: {antecedentes}</div><br>", unsafe_allow_html=True)
                    c_info, c_hist = st.columns([1, 2])
                    with c_info:
                        st.markdown(f"""<div class="royal-card"><h3>👤 {p_data['nombre']} {p_data['apellido_paterno']} {p_data.get('apellido_materno','')}</h3><b>Edad:</b> {edad} Años ({tipo_pac})<br><b>Tel:</b> {format_tel_visual(p_data['telefono'])}<br><b>RFC:</b> {p_data.get('rfc', 'N/A')}</div>""", unsafe_allow_html=True)
                        hist_notas = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn)
                        if st.button("🖨️ Descargar Historia Clínica Profesional (PDF)"):
                            pdf_bytes = crear_pdf_historia(p_data, hist_notas)
                            st.download_button("📥 Bajar PDF", pdf_bytes, f"Historia_{p_data['id_paciente']}.pdf", "application/pdf")
                    with c_hist:
                        st.markdown("#### 📜 Notas de Evolución"); st.dataframe(hist_notas[['fecha', 'tratamiento', 'notas']], use_container_width=True)
        with tab_n:
            st.markdown("#### Formulario de Alta (NOM-004)")
            with st.form("alta_paciente", clear_on_submit=False):
                st.subheader("1. Ficha de Identificación")
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)*"); paterno = c2.text_input("Primer Apellido*"); materno = c3.text_input("Segundo Apellido")
                c4, c5, c6, c7 = st.columns(4)
                nacimiento = c4.date_input("Fecha Nacimiento*", min_value=datetime(1920,1,1)); sexo = c5.selectbox("Sexo*", ["Mujer", "Hombre"]); estado_civil = c6.selectbox("Estado Civil", ["Soltero/a", "Casado/a", "Unión Libre", "Divorciado/a", "Viudo/a"]); ocupacion = c7.text_input("Ocupación")
                c8, c9 = st.columns(2); tel = c8.text_input("Teléfono (10 dígitos)*", max_chars=10); email = c9.text_input("Email")
                
                st.subheader("2. Motivo de Consulta y Antecedentes")
                motivo = st.text_area("Motivo Principal de la Consulta*")
                ahf = st.text_area("AHF (Heredo-Familiares)", placeholder="Diabetes, Hipertensión, Cardiopatías en familia directa..."); app = st.text_area("APP (Personales Patológicos)", placeholder="Alergias, Cirugías, Enfermedades Crónicas, Medicamentos actuales..."); apnp = st.text_area("APNP (No Patológicos)", placeholder="Tabaquismo, Alcoholismo, Higiene bucal...")
                
                st.subheader("3. Exploración y Diagnóstico Inicial (Llenado por el Doctor)")
                exploracion = st.text_area("Hallazgos de Exploración Física (TA, Temp, Tejidos blandos/duros)"); diagnostico = st.text_area("Diagnóstico Presuntivo")

                st.subheader("4. Datos Fiscales (Opcional)")
                cf1, cf2, cf3 = st.columns([2,1,2])
                rfc_base = cf1.text_input("RFC (10 Caracteres)", max_chars=10, help="Si se deja vacío, se calcula automáticamente."); homoclave = cf2.text_input("Homoclave (3)", max_chars=3); cp = cf3.text_input("C.P.", max_chars=5)
                cf4, cf5 = st.columns(2); regimen = cf4.selectbox("Régimen Fiscal", get_regimenes_fiscales()); uso_cfdi = cf5.selectbox("Uso CFDI", get_usos_cfdi())
                aviso = st.checkbox("✅ He leído y acepto el Aviso de Privacidad.", value=True)
                
                if st.form_submit_button("💾 GUARDAR EXPEDIENTE COMPLETO"):
                    if not aviso: st.error("Debe aceptar el Aviso de Privacidad."); st.stop()
                    if not tel.isdigit() or len(tel) != 10: st.error("Teléfono incorrecto (10 dígitos)."); st.stop()
                    if not nombre or not paterno: st.error("Nombre y Primer Apellido son obligatorios."); st.stop()
                    if not motivo: st.error("El Motivo de Consulta es obligatorio."); st.stop()
                    
                    rfc_final = (sanitizar(rfc_base) + sanitizar(homoclave)) if rfc_base else calcular_rfc_10(nombre, paterno, materno, nacimiento) + sanitizar(homoclave)
                    nuevo_id = generar_id_unico(sanitizar(nombre), sanitizar(paterno), nacimiento)
                    c = conn.cursor()
                    c.execute('''INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, email, rfc, regimen, uso_cfdi, cp, sexo, estado, fecha_nacimiento, antecedentes_medicos, ahf, app, apnp, ocupacion, estado_civil, motivo_consulta, exploracion_fisica, diagnostico) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (nuevo_id, get_fecha_mx(), sanitizar(nombre), sanitizar(paterno), sanitizar(materno), tel, limpiar_email(email), rfc_final, regimen, uso_cfdi, cp, sexo, "Activo", format_date_latino(nacimiento), "", sanitizar(ahf), sanitizar(app), sanitizar(apnp), sanitizar(ocupacion), estado_civil, sanitizar(motivo), sanitizar(exploracion), sanitizar(diagnostico)))
                    conn.commit(); st.success(f"✅ Expediente {nuevo_id} creado exitosamente."); time.sleep(1.5); st.rerun()
        with tab_e:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']} {x.get('apellido_materno','')}".strip(), axis=1).tolist()
                sel_edit = st.selectbox("Buscar Paciente para Editar:", ["Select..."] + lista_edit)
                if sel_edit != "Select...":
                    id_target = sel_edit.split(" - ")[0]
                    p = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    with st.form("form_editar_full"):
                        st.info(f"Editando Expediente: {p['id_paciente']}")
                        col_e1, col_e2 = st.tabs(["Datos Personales y Médicos", "Datos Fiscales"])
                        with col_e1:
                            ec1, ec2, ec3 = st.columns(3)
                            e_nom = ec1.text_input("Nombre", p['nombre']); e_pat = ec2.text_input("A. Paterno", p['apellido_paterno']); e_mat = ec3.text_input("A. Materno", p.get('apellido_materno',''))
                            ec4, ec5, ec6 = st.columns(3); e_tel = ec4.text_input("Teléfono", p['telefono']); e_email = ec5.text_input("Email", p.get('email','')); e_ocup = ec6.text_input("Ocupación", p.get('ocupacion',''))
                            e_motivo = st.text_area("Motivo Consulta", p.get('motivo_consulta','')); e_app = st.text_area("APP", p.get('app','')); e_ahf = st.text_area("AHF", p.get('ahf',''))
                        with col_e2:
                            ef1, ef2 = st.columns(2); e_rfc = ef1.text_input("RFC", p.get('rfc','')); e_cp = ef2.text_input("C.P.", p.get('cp',''))
                            
                        if st.form_submit_button("💾 ACTUALIZAR INFORMACIÓN"):
                            c = conn.cursor()
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, ocupacion=?, motivo_consulta=?, app=?, ahf=?, rfc=?, cp=? WHERE id_paciente=?", 
                                      (sanitizar(e_nom), sanitizar(e_pat), sanitizar(e_mat), formatear_telefono_db(e_tel), limpiar_email(e_email), sanitizar(e_ocup), sanitizar(e_motivo), sanitizar(e_app), sanitizar(e_ahf), sanitizar(e_rfc), e_cp, id_target))
                            conn.commit(); st.success("Expediente actualizado."); time.sleep(1.5); st.rerun()

    # --- MÓDULO 3: FINANZAS ---
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes y Finanzas")
        pacientes = pd.read_sql("SELECT * FROM pacientes", conn); servicios = pd.read_sql("SELECT * FROM servicios", conn)
        if not pacientes.empty:
            lista_pac_fin = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']} {x.get('apellido_materno','')}".strip(), axis=1).tolist()
            sel = st.selectbox("Paciente:", lista_pac_fin)
            id_p = sel.split(" - ")[0]; nom_p = sel.split(" - ")[1]
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            df_f = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_p}' AND estado_pago != 'CANCELADO' ORDER BY timestamp DESC", conn)
            if not df_f.empty:
                deuda = pd.to_numeric(df_f['saldo_pendiente'], errors='coerce').fillna(0).sum()
                c1, c2 = st.columns(2); c1.metric("Deuda Total", f"${deuda:,.2f}")
                if deuda > 0.01: c2.error("⚠️ CUENTA CON SALDO PENDIENTE") 
                else: c2.success("✅ CUENTA AL CORRIENTE")
                st.dataframe(df_f[['fecha', 'tratamiento', 'precio_final', 'monto_pagado', 'saldo_pendiente', 'estado_pago']])
            st.markdown("---"); st.subheader("Nuevo Plan / Cobro")
            c1, c2 = st.columns(2)
            if not servicios.empty:
                cat_sel = c1.selectbox("Categoría", servicios['categoria'].unique()); filt = servicios[servicios['categoria'] == cat_sel]
                trat_sel = c2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]; precio_sug = float(item['precio_lista']); costo_lab = float(item['costo_laboratorio_base'])
            else:
                cat_sel = "Manual"; trat_sel = c2.text_input("Tratamiento"); precio_sug = 0.0; costo_lab = 0.0
            
            with st.form("cobro", clear_on_submit=False):
                c1, c2, c3 = st.columns(3)
                precio = c1.number_input("Precio Final", value=precio_sug, step=50.0); abono = c2.number_input("Abono Hoy", step=50.0); saldo = precio - abono
                c3.metric("Saldo Restante", f"${saldo:,.2f}")
                doc = st.selectbox("Doctor Tratante", LISTA_DOCTORES); metodo = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta de Crédito/Débito", "Transferencia", "Pendiente de Pago"])
                notas = st.text_area("Notas del Procedimiento"); agendar = st.checkbox("¿Agendar próxima cita?"); f_cita = st.date_input("Fecha Próxima"); h_cita = st.selectbox("Hora Próxima", generar_slots_tiempo())
                if st.form_submit_button("💾 REGISTRAR PLAN/COBRO"):
                    ocupado = verificar_disponibilidad(format_date_latino(f_cita), h_cita) if agendar else False
                    if ocupado: st.error("Horario de próxima cita ocupado.")
                    else:
                        estatus = "Pagado" if saldo <= 0.01 else "Pendiente"
                        c = conn.cursor()
                        c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                  (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, cat_sel, trat_sel, doc, precio_sug, precio, 0, metodo, estatus, sanitizar(notas), abono, saldo, get_fecha_mx(), costo_lab))
                        if agendar:
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago, categoria) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                                      (int(time.time())+1, format_date_latino(f_cita), h_cita, id_p, nom_p, "Tratamiento", trat_sel, doc, "Pendiente", cat_sel))
                        conn.commit(); st.success("Registrado exitosamente."); time.sleep(1); st.rerun()

    # --- MÓDULO 4: LEGAL (DOCUMENTOS PROFESIONALES) ---
    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Centro Legal y Documentación")
        df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            lista_pac_legal = df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']} {x.get('apellido_materno','')}".strip(), axis=1).tolist()
            sel = st.selectbox("Seleccionar Paciente:", lista_pac_legal)
            nom_completo_paciente = sel.split(" - ")[1]
            tipo_doc = st.selectbox("Tipo de Documento:", ["Consentimiento Informado (General)", "Aviso de Privacidad (Datos Personales)"])
            doc_sel = st.selectbox("Doctor Responsable:", LISTA_DOCTORES)
            tratamiento_esp = st.text_input("Especificar Tratamiento (si aplica):", "Tratamiento Odontológico Integral") if "Consentimiento" in tipo_doc else ""
            
            st.markdown("### ✍️ Firma del Paciente")
            st.caption("Por favor, solicite al paciente que firme en el recuadro blanco.")
            canvas_result = st_canvas(stroke_width=2, height=150, width=500, background_color="#ffffff", key="canvas_legal")
            
            if st.button("🖨️ Generar y Descargar Documento PDF"):
                if canvas_result.image_data is not None and not np.all(canvas_result.image_data[:,:,3] == 0): # Verifica si hay trazos
                    import numpy as np; from PIL import Image; import io
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG")
                    img_str = base64.b64encode(buf.getvalue()).decode()
                    pdf_bytes = crear_pdf_consentimiento(nom_completo_paciente, doc_sel, tipo_doc, tratamiento_esp, img_str)
                    st.download_button("📥 Descargar PDF Firmado", pdf_bytes, f"{tipo_doc.split()[0]}_{sel.split()[0]}.pdf", "application/pdf")
                else: st.warning("⚠️ El paciente debe firmar en el recuadro antes de generar el documento.")

    # --- MÓDULO 5: ASISTENCIA ---
    elif menu == "5. Control Asistencia":
        st.title("⏱️ Registro de Jornada Laboral")
        st.markdown(f"### 👨‍⚕️ {DOC_EMMANUEL}")
        c_in, c_out = st.columns(2)
        with c_in:
            if st.button("🟢 REGISTRAR ENTRADA"): 
                ok, m = registrar_movimiento(DOC_EMMANUEL, "Entrada")
                if ok: st.success(m); time.sleep(2); st.rerun()
                else: st.warning(m)
        with c_out:
            if st.button("🔴 REGISTRAR SALIDA"): 
                ok, m = registrar_movimiento(DOC_EMMANUEL, "Salida")
                if ok: st.success(m); time.sleep(2); st.rerun()
                else: st.warning(m)
        
        # Ver historial de hoy
        st.markdown("---")
        st.subheader("Tu Actividad de Hoy")
        df_asist = pd.read_sql(f"SELECT hora_entrada, hora_salida, horas_totales, estado FROM asistencia WHERE doctor='{DOC_EMMANUEL}' AND fecha='{get_fecha_mx()}'", conn)
        st.dataframe(df_asist)
            
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Administracion": st.title("Portal Administrativo"); st.info("Módulo en desarrollo."); st.button("Cerrar Sesión", on_click=lambda: st.session_state.update(perfil=None))
