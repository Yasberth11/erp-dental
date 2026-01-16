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
# 1. CONFIGURACIÓN Y CATÁLOGOS LEGALES
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')
LOGO_FILE = "logo.png"
DIRECCION_CONSULTORIO = "Calle Ejemplo #123, Col. Centro, Ciudad de México" # <--- EDITA ESTO

# CONSTANTES DOCTORES (Nombre y Cédula)
DOCS_INFO = {
    "Dr. Emmanuel": {"nombre": "Dr. Emmanuel Tlacaélel López Bermejo", "cedula": "12345678"},
    "Dra. Mónica": {"nombre": "Dra. Mónica Montserrat Rodríguez Álvarez", "cedula": "87654321"}
}

# BASE DE DATOS DE RIESGOS (TEXTOS JURÍDICOS)
CLAUSULA_CIERRE = "Adicionalmente, entiendo que pueden presentarse eventos imprevisibles en cualquier acto médico, tales como: reacciones alérgicas a los anestésicos o materiales (incluso si no tengo antecedentes conocidos), síncope (desmayo), trismus (dificultad para abrir la boca), hematomas, o infecciones secundarias. Acepto que el éxito del tratamiento depende también de mi biología y de seguir estrictamente las indicaciones post-operatorias."

RIESGOS_DB = {
    "Profilaxis (Limpieza Ultrasónica)": "Sensibilidad dental transitoria (frio/calor); sangrado leve de encías debido a la inflamación previa; desalojo de restauraciones antiguas que estuvieran desajustadas; molestia en cuellos dentales expuestos.",
    "Aplicación de Flúor (Niños)": "Náuseas leves o malestar estomacal en caso de ingestión accidental; sabor desagradable momentáneo.",
    "Sellador de Fosetas y Fisuras": "Sensación de mordida alta que requiere ajuste; desalojo parcial o total del sellador si se consumen alimentos pegajosos/chiclosis inmediatamente; necesidad de reemplazo futuro por desgaste natural.",
    "Resina Simple (1 cara)": "Sensibilidad postoperatoria (dolor al morder o con el frío) que puede durar días o semanas; riesgo de pulpitis (inflamación del nervio) que requiera endodoncia si la caries era profunda; desajuste oclusal; fractura de la restauración o de la pared dental remanente.",
    "Resina Compuesta (2 o más caras)": "Sensibilidad postoperatoria (dolor al morder o con el frío) que puede durar días o semanas; riesgo de pulpitis (inflamación del nervio) que requiera endodoncia si la caries era profunda; desajuste oclusal; fractura de la restauración o de la pared dental remanente.",
    "Reconstrucción de Muñón": "Riesgo de perforación del piso de la cámara pulpar; fractura de la estructura dental remanente debido a la debilidad del diente; pronóstico reservado sujeto a la colocación de la corona definitiva.",
    "Curación Temporal (Cavit)": "Desgaste o caída del material provisional si no se acude a la cita definitiva; filtración bacteriana y dolor si se deja más tiempo del indicado; sabor medicamentoso.",
    "Extracción Simple": "Hemorragia o sangrado postoperatorio; dolor e inflamación (edema); infección del alveolo (alveolitis seca); hematomas faciales; daño accidental a dientes vecinos o restauraciones adyacentes; fractura de raíces que requiera odontosección.",
    "Cirugía de Tercer Molar (Muela del Juicio)": "Parestesia (adormecimiento temporal o permanente de labio, lengua o mentón por cercanía con el nervio dentario); comunicación oroantral (en superiores); trismus severo; infección; inflamación extendida a cuello; equimosis (moretones).",
    "Drenaje de Absceso": "Dolor durante la incisión; necesidad de mantener un drenaje (penrose); cicatriz en mucosa; posible reincidencia de la infección si no se trata el diente causal (extracción o endodoncia) inmediatamente.",
    "Endodoncia Anterior (1 conducto)": "Fractura de instrumentos (limas) dentro de los conductos debido a anatomía compleja; perforación radicular; sobre-obturación o falta de sellado apical; dolor agudo post-tratamiento (flare-up); oscurecimiento del diente con el tiempo; fractura vertical de la raíz; posible fracaso del tratamiento que conlleve a la extracción.",
    "Endodoncia Premolar (2 conductos)": "Fractura de instrumentos (limas) dentro de los conductos debido a anatomía compleja; perforación radicular; sobre-obturación o falta de sellado apical; dolor agudo post-tratamiento (flare-up); oscurecimiento del diente con el tiempo; fractura vertical de la raíz; posible fracaso del tratamiento que conlleve a la extracción.",
    "Endodoncia Molar (3+ conductos)": "Fractura de instrumentos (limas) dentro de los conductos debido a anatomía compleja; perforación radicular; sobre-obturación o falta de sellado apical; dolor agudo post-tratamiento (flare-up); oscurecimiento del diente con el tiempo; fractura vertical de la raíz; posible fracaso del tratamiento que conlleve a la extracción.",
    "Corona Zirconia": "Sensibilidad dental tras el tallado que puede requerir endodoncia; retracción gingival con el tiempo exponiendo el margen; fractura de la porcelana (chipping) por fuerzas masticatorias excesivas; descementado (caída) de la corona.",
    "Corona Metal-Porcelana": "Sensibilidad dental tras el tallado que puede requerir endodoncia; retracción gingival con el tiempo exponiendo el margen; fractura de la porcelana (chipping) por fuerzas masticatorias excesivas; descementado (caída) de la corona.",
    "Incrustación Estética": "Sensibilidad postoperatoria; fractura de la restauración; despegamiento; diferencia de color con el diente natural por pigmentaciones futuras; necesidad de mayor desgaste dental si se detecta caries oculta.",
    "Carilla de Porcelana": "Sensibilidad postoperatoria; fractura de la restauración; despegamiento; diferencia de color con el diente natural por pigmentaciones futuras; necesidad de mayor desgaste dental si se detecta caries oculta.",
    "Poste de Fibra de Vidrio": "Riesgo de perforación de la raíz durante la desobturación; fractura radicular por efecto de cuña; desalojo del poste junto con la corona.",
    "Placa Total (Acrílico) - Una arcada": "Rozaduras, úlceras o llagas por presión en las encías; dificultad fonética y masticatoria durante el periodo de adaptación (hasta 30 días); reabsorción ósea continua; necesidad de rebase o ajuste periódico; posible reacción alérgica al acrílico (poco común).",
    "Prótesis Flexible (Valplast) - Unilateral": "Rozaduras, úlceras o llagas por presión en las encías; dificultad fonética y masticatoria durante el periodo de adaptación (hasta 30 días); reabsorción ósea continua; necesidad de rebase o ajuste periódico.",
    "Blanqueamiento (Consultorio 2 sesiones)": "Hipersensibilidad dentinaria aguda (shocks eléctricos) transitoria; irritación química de encías y mucosas (quemadura blanca reversible); resultado estético variable (no se garantiza un tono blanco específico); regresión del color si no se modifican hábitos (café, tabaco).",
    "Blanqueamiento (Guardas en casa)": "Hipersensibilidad dentinaria aguda (shocks eléctricos) transitoria; irritación química de encías y mucosas (quemadura blanca reversible); resultado estético variable (no se garantiza un tono blanco específico); regresión del color si no se modifican hábitos (café, tabaco).",
    "Pago Inicial (Brackets Metálicos)": "Reabsorción radicular (acortamiento de raíces); descalcificación (manchas blancas) y caries por mala higiene alrededor de los brackets; inflamación gingival; dolor y movilidad dental; recidiva (movimiento de dientes) si no se usan retenedores al finalizar.",
    "Mensualidad Ortodoncia": "Reabsorción radicular (acortamiento de raíces); descalcificación (manchas blancas) y caries por mala higiene alrededor de los brackets; inflamación gingival; dolor y movilidad dental; recidiva (movimiento de dientes) si no se usan retenedores al finalizar.",
    "Pulpotomía": "Fracaso del tratamiento por infección recurrente (fístula) que requiera extracción; reabsorción interna; exfoliación prematura o retardada del diente.",
    "Corona Acero-Cromo": "Molestia gingival por presión de la corona; estética metálica; riesgo de ingestión si se descementa; dolor a la masticación los primeros días.",
    "Garantía (Retoque/Reparación)": "La garantía aplica exclusivamente sobre defectos de laboratorio o fractura de material por vicio oculto. NO cubre: nuevas caries, fracturas por traumatismos (golpes, caídas), ni fracasos derivados de mala higiene o inasistencia a citas de revisión."
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
        div[data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. MOTOR DE BASE DE DATOS
# ==========================================
DB_FILE = "royal_dental_db.sqlite"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def migrar_tablas():
    conn = get_db_connection()
    c = conn.cursor()
    for col in ['antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo', 'domicilio', 'tutor', 'contacto_emergencia', 'ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']:
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
# 3. HELPERS Y FUNCIONES
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
            conn.commit(); return True, f"Entrada registrada: {hora_actual}"
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
        if isinstance(nacimiento_input, str): nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date()
        else: nacimiento = nacimiento_input
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
        fecha_str = fecha.strftime("%y%m%d"); rfc_base = f"{letra1}{letra2}{letra3}{letra4}{fecha_str}".upper()
        if rfc_base[:4] in ["PUTO", "PITO", "CULO", "MAME"]: rfc_base = f"{rfc_base[:3]}X{rfc_base[4:]}"
        return rfc_base
    except: return ""

# ==========================================
# 4. GENERADOR DE PDF PROFESIONALES (LEGAL SUITE)
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

def procesar_firma_digital(firma_img_data):
    """Convierte base64 de canvas a archivo temporal para FPDF"""
    try:
        img_data = re.sub('^data:image/.+;base64,', '', firma_img_data)
        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
        temp_filename = f"temp_sig_{int(time.time())}_{random.randint(1,1000)}.png"
        img.save(temp_filename)
        return temp_filename
    except: return None

def crear_pdf_consentimiento(paciente_full, nombre_doctor, cedula_doctor, tipo_doc, tratamiento, riesgo_legal, firma_pac, firma_doc, testigos):
    pdf = PDFGenerator(); pdf.add_page()
    fecha_hoy = get_fecha_mx()
    
    if "Aviso" in tipo_doc:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "AVISO DE PRIVACIDAD INTEGRAL PARA PACIENTES", 0, 1, 'C'); pdf.ln(5)
        texto = f"""En cumplimiento estricto con lo dispuesto por la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (la "Ley"), su Reglamento y los Lineamientos del Aviso de Privacidad, se emite el presente documento:

IDENTIDAD Y DOMICILIO DEL RESPONSABLE
La clínica dental denominada comercialmente ROYAL DENTAL (en adelante "El Responsable"), con domicilio en {DIRECCION_CONSULTORIO}, es la entidad responsable del uso, manejo, almacenamiento y confidencialidad de sus datos personales.

DATOS PERSONALES QUE SE RECABAN Y DATOS SENSIBLES
Para llevar a cabo las finalidades descritas, utilizaremos: nombre completo, edad, sexo, domicilio, teléfono, correo electrónico, RFC y ocupación.
Además, para cumplir con la normatividad sanitaria vigente (NOM-004-SSA3-2012), es necesario recabar DATOS PERSONALES SENSIBLES referentes a: Estado de salud, Antecedentes, Información genética, Imágenes diagnósticas.

FINALIDADES DEL TRATAMIENTO
A) Prestación de servicios odontológicos. B) Creación y conservación del expediente clínico. C) Facturación y cobranza. D) Contacto para seguimiento.
Finalidades Secundarias: Envío de promociones y encuestas de calidad.

TRANSFERENCIA DE DATOS
Sus datos pueden ser compartidos con: Laboratorios dentales y gabinetes radiológicos (para prótesis/estudios), Especialistas interconsultantes, Compañías Aseguradoras y Autoridades sanitarias.

DERECHOS ARCO
Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse al tratamiento de sus datos presentando solicitud en recepción.

CONSENTIMIENTO
Consiento que mis datos personales sensibles sean tratados conforme a este aviso. Reconozco que la firma digital tiene validez legal."""
        try: pdf.chapter_body(texto.encode('latin-1', 'replace').decode('latin-1'))
        except: pdf.chapter_body(texto)

    else:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "CARTA DE CONSENTIMIENTO INFORMADO", 0, 1, 'C'); pdf.ln(5)
        cuerpo = f"""LUGAR Y FECHA: Ciudad de México, a {fecha_hoy}
NOMBRE DEL PACIENTE: {paciente_full}
ODONTÓLOGO TRATANTE: {nombre_doctor} (Céd. Prof. {cedula_doctor})

DECLARACIÓN DEL PACIENTE:
Yo, el paciente arriba mencionado, declaro en pleno uso de mis facultades que he recibido una explicación clara sobre mi diagnóstico y el plan de tratamiento.

PROCEDIMIENTO A REALIZAR: {tratamiento}

RIESGOS Y COMPLICACIONES ADVERTIDOS:
{riesgo_legal}

{CLAUSULA_CIERRE}

OBLIGACIÓN DE MEDIOS Y NO DE RESULTADOS: Entiendo que la Odontología no es una ciencia exacta y el profesional se compromete a usar todos los medios técnicos, pero no puede garantizar resultados biológicos al 100%.

AUTORIZACIÓN: Autorizo la anestesia local y procedimientos necesarios, asumiendo los riesgos inherentes."""
        try: pdf.chapter_body(cuerpo.encode('latin-1', 'replace').decode('latin-1'))
        except: pdf.chapter_body(cuerpo)

    # SECCIÓN DE FIRMAS (PACIENTE Y DOCTOR)
    pdf.ln(10)
    y_firmas = pdf.get_y()
    
    # Firma Paciente
    pdf.set_font('Arial', 'B', 9)
    pdf.text(20, y_firmas + 40, "FIRMA DEL PACIENTE")
    if firma_pac:
        f_path = procesar_firma_digital(firma_pac)
        if f_path: pdf.image(f_path, x=20, y=y_firmas, w=50); os.remove(f_path)
    else: pdf.line(20, y_firmas + 35, 80, y_firmas + 35)

    # Firma Doctor
    pdf.text(120, y_firmas + 40, f"FIRMA DR. {nombre_doctor.split()[2]}") # Apellido
    if firma_doc:
        f_path_d = procesar_firma_digital(firma_doc)
        if f_path_d: pdf.image(f_path_d, x=120, y=y_firmas, w=50); os.remove(f_path_d)
    else: pdf.line(120, y_firmas + 35, 180, y_firmas + 35)

    # TESTIGOS (Si se llenaron)
    pdf.ln(50)
    pdf.set_font('Arial', '', 8)
    if testigos['t1']:
        pdf.cell(90, 10, f"Testigo 1: {testigos['t1']}", 0, 0, 'L')
    if testigos['t2']:
        pdf.cell(90, 10, f"Testigo 2: {testigos['t2']}", 0, 1, 'L')
        
    # Salida segura
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

def crear_pdf_historia(p, historial):
    pdf = PDFGenerator(); pdf.add_page()
    nombre_p = f"{p['nombre']} {p['apellido_paterno']} {p.get('apellido_materno','')}"
    edad, _ = calcular_edad_completa(p.get('fecha_nacimiento', ''))
    
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "HISTORIA CLÍNICA ODONTOLÓGICA (NOM-004-SSA3-2012)", 0, 1, 'C'); pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230); pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "I. FICHA DE IDENTIFICACIÓN", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    info = f"""Nombre: {nombre_p}\nEdad: {edad} | Sexo: {p.get('sexo','N/A')} | Nacimiento: {p.get('fecha_nacimiento','N/A')}\nOcupación: {p.get('ocupacion','N/A')} | Estado Civil: {p.get('estado_civil','N/A')}\nDomicilio: {p.get('domicilio','N/A')}\nTel: {p['telefono']} | Email: {p.get('email','N/A')}\nContacto Emergencia: {p.get('contacto_emergencia','N/A')}\nTutor: {p.get('tutor','N/A')}"""
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
    
    # ===================== MANTENIMIENTO FIX (PRIORIDAD 0) =====================
    with st.sidebar.expander("🛠️ Mantenimiento"):
        if st.button("🗑️ RESETEAR BASE DE DATOS (CUIDADO)", type="primary"):
            try:
                # PASO 1: Conexión explícita
                conn_temp = get_db_connection()
                c_temp = conn_temp.cursor()
                # PASO 2: Borrado
                c_temp.execute("DELETE FROM pacientes")
                c_temp.execute("DELETE FROM citas")
                c_temp.execute("DELETE FROM asistencia")
                # PASO 3: Commit real y cierre
                conn_temp.commit()
                conn_temp.close()
                # PASO 4: Limpiar Cache
                st.cache_data.clear()
                if 'perfil' in st.session_state: del st.session_state['perfil']
                st.success("✅ Sistema y memoria limpiados.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error crítico: {e}")
    # ===========================================================================

    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    conn = get_db_connection()

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
                    with st.form("cita_registrada", clear_on_submit=True):
                        pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                        lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not pacientes_raw.empty else []
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        h_sel = st.selectbox("Hora", generar_slots_tiempo())
                        m_sel = st.text_input("Motivo", "Revisión / Continuación")
                        d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        urgencia = st.checkbox("🚨 Es Urgencia / Sobrecupo")
                        if st.form_submit_button("Agendar"):
                            ocupado = verificar_disponibilidad(fecha_ver_str, h_sel)
                            if ocupado and not urgencia: st.error(f"⚠️ Horario {h_sel} OCUPADO.")
                            elif p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]; nom_p = p_sel.split(" - ")[1]
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria) 
                                                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                         (int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", sanitizar(m_sel), d_sel, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General"))
                                conn.commit(); st.success(f"Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Seleccione paciente")

                with tab_new:
                    with st.form("cita_prospecto", clear_on_submit=True):
                        nombre_pros = st.text_input("Nombre"); tel_pros = st.text_input("Tel (10)", max_chars=10)
                        hora_pros = st.selectbox("Hora", generar_slots_tiempo()); motivo_pros = st.text_input("Motivo", "Revisión 1ra Vez")
                        doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"]); urgencia_p = st.checkbox("🚨 Es Urgencia")
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
                        # LAYOUT FIX: Vertical buttons for elegance and better spacing
                        col_inputs, col_actions = st.columns([2.5, 1])
                        with col_inputs:
                            new_date_res = st.date_input("Nueva Fecha", datetime.now(TZ_MX))
                            new_h_res = st.selectbox("Nueva Hora", generar_slots_tiempo(), key="reag_time")
                        with col_actions:
                            st.write("") # Spacer
                            st.write("") # Spacer
                            if st.button("🗓️ Mover", use_container_width=True):
                                c = conn.cursor(); c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", (format_date_latino(new_date_res), new_h_res, fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.success(f"Reagendada"); time.sleep(1); st.rerun()
                            
                            if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                                 c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                 conn.commit(); st.warning("Cancelada"); time.sleep(1); st.rerun()
                            
                            if st.button("🗑️ Eliminar", type="primary", use_container_width=True):
                                 c = conn.cursor(); c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                 conn.commit(); registrar_auditoria("Consultorio", "ELIMINACION CITA", f"Se eliminó cita de {nom_target}"); st.error("Eliminado."); time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 {fecha_ver_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                slots = generar_slots_tiempo()
                for slot in slots:
                    ocupado = df_dia[(df_dia['hora'] == slot) & (df_dia['estado_pago'] != 'CANCELADO')]
                    if ocupado.empty: st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)
                    else:
                        for _, r in ocupado.iterrows():
                            color = "#FF5722" if "PROS" in str(r['id_paciente']) else "#002B5B"
                            st.markdown(f"""<div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;"><b>{slot} | {r['nombre_paciente']}</b><br><span style="color:#666; font-size:0.9em;">{r['tratamiento']} - {r['doctor_atendio']}</span></div>""", unsafe_allow_html=True)

    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico")
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR/IMPRIMIR", "➕ NUEVO (ALTA)", "✏️ EDITAR"])
        with tab_b:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_busqueda = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                seleccion = st.selectbox("Seleccionar:", ["..."] + lista_busqueda)
                if seleccion != "...":
                    id_sel_str = seleccion.split(" - ")[0]; p_data = pacientes_raw[pacientes_raw['id_paciente'] == id_sel_str].iloc[0]
                    edad, tipo_pac = calcular_edad_completa(p_data.get('fecha_nacimiento', ''))
                    antecedentes = p_data.get('app', '') 
                    if antecedentes: st.markdown(f"<div class='alerta-medica'>⚠️ ALERTA: {antecedentes}</div><br>", unsafe_allow_html=True)
                    c_info, c_hist = st.columns([1, 2])
                    with c_info:
                        st.markdown(f"""<div class="royal-card"><h3>👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3><b>Edad:</b> {edad} Años<br><b>Tel:</b> {format_tel_visual(p_data['telefono'])}<br><b>RFC:</b> {p_data.get('rfc', 'N/A')}</div>""", unsafe_allow_html=True)
                        hist_notas = pd.read_sql(f"SELECT fecha, tratamiento, doctor_atendio, notas FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn)
                        if st.button("🖨️ Descargar Historia (PDF)"):
                            pdf_bytes = crear_pdf_historia(p_data, hist_notas)
                            # NOMBRE ARCHIVO FIX
                            clean_name = f"{p_data['id_paciente']}_HISTORIAL_{sanitizar(p_data['nombre'])}_{sanitizar(p_data['apellido_paterno'])}.pdf".replace(" ", "_")
                            st.download_button("📥 Bajar PDF", pdf_bytes, clean_name, "application/pdf")
                    with c_hist:
                        st.markdown("#### 📜 Notas"); st.dataframe(hist_notas[['fecha', 'tratamiento', 'notas']], use_container_width=True)
        with tab_n:
            st.markdown("#### Formulario Alta (NOM-004)")
            with st.form("alta_paciente", clear_on_submit=True): # FIX: Clear Form
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)"); paterno = c2.text_input("A. Paterno"); materno = c3.text_input("A. Materno")
                c4, c5, c6 = st.columns(3)
                nacimiento = c4.date_input("Nacimiento", min_value=datetime(1920,1,1)); tel = c5.text_input("Tel (10 dígitos)", max_chars=10); email = c6.text_input("Email")
                c7, c8_a, c8_b = st.columns([1,1,1])
                sexo = c7.selectbox("Sexo", ["Mujer", "Hombre"])
                rfc_base = c8_a.text_input("RFC (Opcional)", max_chars=10, help="Dejar vacío para calcular automático")
                homoclave = c8_b.text_input("Homoclave", max_chars=3)
                
                # CAMPOS ADICIONALES LEGALES
                st.markdown("**Datos Adicionales**")
                col_extra = st.columns(3)
                ocupacion = col_extra[0].text_input("Ocupación")
                estado_civil = col_extra[1].selectbox("Estado Civil", ["Soltero", "Casado", "Divorciado", "Viudo", "Unión Libre"])
                domicilio = col_extra[2].text_input("Domicilio Completo")
                col_extra2 = st.columns(2)
                tutor = col_extra2[0].text_input("Nombre Tutor (Si es menor)")
                contacto_emer = col_extra2[1].text_input("Contacto Emergencia (Nombre y Tel)")
                motivo_consulta = st.text_area("Motivo de Consulta*")

                st.markdown("**Historia Médica**")
                ahf = st.text_area("AHF", placeholder="Diabetes, Hipertensión..."); app = st.text_area("APP", placeholder="Alergias, Cirugías..."); apnp = st.text_area("APNP", placeholder="Tabaquismo, Alcoholismo...")
                
                # EXPLORACIÓN
                st.markdown("**Exploración y Diagnóstico (Dr)**")
                exploracion = st.text_area("Exploración Física"); diagnostico = st.text_area("Diagnóstico Presuntivo")

                st.markdown("**Fiscal**")
                c9, c10, c11 = st.columns(3)
                regimen = c9.selectbox("Régimen", get_regimenes_fiscales()); uso_cfdi = c10.selectbox("Uso CFDI", get_usos_cfdi()); cp = c11.text_input("C.P.", max_chars=5)
                aviso = st.checkbox("Acepto Aviso de Privacidad")
                
                if st.form_submit_button("💾 GUARDAR EXPEDIENTE"):
                    if not aviso: st.error("Acepte Aviso Privacidad"); st.stop()
                    if not tel.isdigit() or len(tel) != 10: st.error("Teléfono incorrecto"); st.stop()
                    if not nombre or not paterno: st.error("Nombre incompleto"); st.stop()
                    
                    if not rfc_base: rfc_final = calcular_rfc_10(nombre, paterno, materno, nacimiento) + sanitizar(homoclave)
                    else: rfc_final = sanitizar(rfc_base) + sanitizar(homoclave)
                    
                    nuevo_id = generar_id_unico(sanitizar(nombre), sanitizar(paterno), nacimiento)
                    c = conn.cursor()
                    c.execute("INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, email, rfc, regimen, uso_cfdi, cp, nota_fiscal, sexo, estado, fecha_nacimiento, antecedentes_medicos, ahf, app, apnp, ocupacion, estado_civil, domicilio, tutor, contacto_emergencia, motivo_consulta, exploracion_fisica, diagnostico) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (nuevo_id, get_fecha_mx(), sanitizar(nombre), sanitizar(paterno), sanitizar(materno), tel, limpiar_email(email), rfc_final, regimen, uso_cfdi, cp, "", sexo, "Activo", format_date_latino(nacimiento), "", sanitizar(ahf), sanitizar(app), sanitizar(apnp), sanitizar(ocupacion), estado_civil, sanitizar(domicilio), sanitizar(tutor), sanitizar(contacto_emer), sanitizar(motivo_consulta), sanitizar(exploracion), sanitizar(diagnostico)))
                    conn.commit(); st.success(f"✅ Paciente {nombre} guardado."); time.sleep(1.5); st.rerun()
        with tab_e:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                sel_edit = st.selectbox("Buscar Paciente:", ["Select..."] + lista_edit)
                if sel_edit != "Select...":
                    id_target = sel_edit.split(" - ")[0]
                    p = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    with st.form("form_editar_full"):
                        st.info("Editando a: " + p['nombre'])
                        ec1, ec2, ec3 = st.columns(3)
                        e_nom = ec1.text_input("Nombre", p['nombre']); e_pat = ec2.text_input("A. Paterno", p['apellido_paterno']); e_mat = ec3.text_input("A. Materno", p['apellido_materno'])
                        ec4, ec5 = st.columns(2)
                        e_tel = ec4.text_input("Teléfono", p['telefono']); e_email = ec5.text_input("Email", p['email'])
                        
                        st.markdown("**Médico & Contacto**")
                        e_app = st.text_area("APP (Alergias)", p['app'] if p['app'] else ""); e_ahf = st.text_area("AHF", p['ahf'] if p['ahf'] else ""); e_apnp = st.text_area("APNP", p['apnp'] if p['apnp'] else "")
                        # FIX: Missing field
                        e_cont = st.text_input("Contacto Emergencia", p.get('contacto_emergencia', ''))
                        
                        st.markdown("**Fiscal**")
                        ec6, ec7, ec8 = st.columns(3)
                        e_rfc = ec6.text_input("RFC Completo", p['rfc']); e_cp = ec7.text_input("C.P.", p['cp'])
                        
                        idx_reg = 0
                        reg_list = get_regimenes_fiscales()
                        if p['regimen'] in reg_list: idx_reg = reg_list.index(p['regimen'])
                        e_reg = ec8.selectbox("Régimen", reg_list, index=idx_reg)

                        if st.form_submit_button("💾 ACTUALIZAR TODO"):
                            c = conn.cursor()
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, app=?, ahf=?, apnp=?, rfc=?, cp=?, regimen=?, contacto_emergencia=? WHERE id_paciente=?", 
                                     (sanitizar(e_nom), sanitizar(e_pat), sanitizar(e_mat), formatear_telefono_db(e_tel), limpiar_email(e_email), sanitizar(e_app), sanitizar(e_ahf), sanitizar(e_apnp), sanitizar(e_rfc), e_cp, e_reg, sanitizar(e_cont), id_target))
                            conn.commit(); st.success("Datos actualizados."); time.sleep(1.5); st.rerun()

    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Finanzas")
        pacientes = pd.read_sql("SELECT * FROM pacientes", conn); servicios = pd.read_sql("SELECT * FROM servicios", conn)
        if not pacientes.empty:
            sel = st.selectbox("Paciente:", pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']}", axis=1).tolist())
            id_p = sel.split(" - ")[0]; nom_p = sel.split(" - ")[1]
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            df_f = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_p}' AND estado_pago != 'CANCELADO'", conn)
            if not df_f.empty:
                deuda = pd.to_numeric(df_f['saldo_pendiente'], errors='coerce').fillna(0).sum()
                c1, c2 = st.columns(2); c1.metric("Deuda", f"${deuda:,.2f}")
                # CRASH FIX: Unrolled conditional for Streamlit compatibility
                if deuda > 0: c2.error("PENDIENTE") 
                else: c2.success("AL CORRIENTE")
                
                st.dataframe(df_f[['fecha', 'tratamiento', 'precio_final', 'monto_pagado', 'saldo_pendiente']])
            st.markdown("---"); st.subheader("Nuevo Plan")
            c1, c2 = st.columns(2)
            if not servicios.empty:
                cat_sel = c1.selectbox("Categoría", servicios['categoria'].unique()); filt = servicios[servicios['categoria'] == cat_sel]
                trat_sel = c2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]; precio_sug = float(item['precio_lista']); costo_lab = float(item['costo_laboratorio_base'])
                # RIESGO AUTOMATICO DEL DICCIONARIO
                riesgo_auto = RIESGOS_DB.get(trat_sel, "Riesgos generales inherentes al procedimiento.")
            else:
                cat_sel = "Manual"; trat_sel = c2.text_input("Tratamiento"); precio_sug = 0.0; costo_lab = 0.0; riesgo_auto = ""
            
            with st.form("cobro", clear_on_submit=True): # FIX: Clear Form
                c1, c2, c3 = st.columns(3)
                precio = c1.number_input("Precio", value=precio_sug, step=50.0); abono = c2.number_input("Abono", step=50.0); saldo = precio - abono
                c3.metric("Saldo", f"${saldo:,.2f}")
                
                num_sessions = st.number_input("Sesiones Estimadas", min_value=1, value=1)
                
                # FIX: Payment methods updated
                doc_name = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"]); metodo = st.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia", "Garantía", "Pendiente de Pago"])
                notas = st.text_area("Notas Evolución"); agendar = st.checkbox("¿Agendar Cita?"); f_cita = st.date_input("Fecha"); h_cita = st.selectbox("Hora", generar_slots_tiempo())
                
                if st.form_submit_button("Registrar"):
                    ocupado = verificar_disponibilidad(format_date_latino(f_cita), h_cita) if agendar else False
                    if ocupado: st.error("Horario Ocupado.")
                    else:
                        estatus = "Pagado" if saldo <= 0 else "Pendiente"
                        c = conn.cursor()
                        # GUARDAR RIESGO AUTOMATICO EN NOTAS OCULTAS O VISIBLES
                        nota_final = f"{sanitizar(notas)} | RIESGO: {riesgo_auto}"
                        c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                 (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, cat_sel, trat_sel, doc_name, precio_sug, precio, 0, metodo, estatus, nota_final, abono, saldo, get_fecha_mx(), costo_lab))
                        if agendar:
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago, categoria) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                                     (int(time.time())+1, format_date_latino(f_cita), h_cita, id_p, nom_p, "Tratamiento", trat_sel, doc_name, "Pendiente", cat_sel))
                        conn.commit(); st.success("Registrado"); time.sleep(1); st.rerun()

    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Centro Legal"); df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", ["..."]+df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']}", axis=1).tolist())
            if sel != "...":
                id_target = sel.split(" - ")[0]; p_obj = df_p[df_p['id_paciente'] == id_target].iloc[0]
                
                tipo_doc = st.selectbox("Documento", ["Consentimiento Informado", "Aviso de Privacidad"])
                
                # SELECCION DE TRATAMIENTO PARA EL CONTRATO (AUTOMATIZADO)
                servicios = pd.read_sql("SELECT * FROM servicios", conn)
                tratamiento_legal = ""
                riesgo_legal = ""
                
                if "Consentimiento" in tipo_doc:
                    if not servicios.empty:
                        cat_l = st.selectbox("Categoría Tratamiento:", servicios['categoria'].unique())
                        trat_l = st.selectbox("Tratamiento a Realizar:", servicios[servicios['categoria']==cat_l]['nombre_tratamiento'].unique())
                        tratamiento_legal = trat_l
                        riesgo_legal = RIESGOS_DB.get(trat_l, "Riesgos generales inherentes.")
                        st.info(f"Riesgos detectados: {riesgo_legal}")
                
                col_doc_sel = st.columns(2)
                doc_name_sel = col_doc_sel[0].selectbox("Odontólogo Tratante:", list(DOCS_INFO.keys()))
                
                # TESTIGOS (OPCIONALES)
                with st.expander("Testigos (Opcional)"):
                    t1 = st.text_input("Nombre Testigo 1")
                    t2 = st.text_input("Nombre Testigo 2")
                
                st.markdown("### Firmas Digitales")
                # FIX: Firmas múltiples y corrección de keys
                col_firmas_1, col_firmas_2 = st.columns(2)
                
                with col_firmas_1:
                    st.caption("Firma del Paciente")
                    canvas_pac = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_paciente")
                    st.caption("Firma Testigo 1")
                    canvas_t1 = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_testigo1")

                with col_firmas_2:
                    st.caption(f"Firma Dr. {doc_name_sel.split()[1]}")
                    canvas_doc = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_doctor")
                    st.caption("Firma Testigo 2")
                    canvas_t2 = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_testigo2")
                
                if st.button("Generar PDF Legal"):
                    img_pac = None; img_doc = None
                    if canvas_pac.image_data is not None:
                        import numpy as np; from PIL import Image; import io
                        if not np.all(canvas_pac.image_data[:,:,3] == 0):
                            img = Image.fromarray(canvas_pac.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_pac = base64.b64encode(buf.getvalue()).decode()
                    
                    if canvas_doc.image_data is not None:
                        if not np.all(canvas_doc.image_data[:,:,3] == 0):
                            img = Image.fromarray(canvas_doc.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_doc = base64.b64encode(buf.getvalue()).decode()
                    
                    # OBTENER DATOS COMPLETOS DOCTOR Y PACIENTE
                    doc_full = DOCS_INFO[doc_name_sel]['nombre']
                    cedula_full = DOCS_INFO[doc_name_sel]['cedula']
                    nombre_paciente_full = f"{p_obj['nombre']} {p_obj['apellido_paterno']} {p_obj.get('apellido_materno','')}"
                    
                    pdf_bytes = crear_pdf_consentimiento(nombre_paciente_full, doc_full, cedula_full, tipo_doc, tratamiento_legal, riesgo_legal, img_pac, img_doc, {'t1':t1, 't2':t2})
                    st.download_button("Descargar PDF Firmado", pdf_bytes, "Legal.pdf", "application/pdf")

    elif menu == "5. Control Asistencia":
        st.title("⏱️ Checador")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Entrada Dr. Emmanuel"): 
                ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada"); 
                if ok: st.success(m) 
                else: st.warning(m)
        with col_b:
            if st.button("Salida Dr. Emmanuel"): 
                ok, m = registrar_movimiento("Dr. Emmanuel", "Salida"); 
                if ok: st.success(m)
                else: st.warning(m)
            
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Administracion": st.title("Admin"); st.button("Salir", on_click=lambda: st.session_state.update(perfil=None))
