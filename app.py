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
DIRECCION_CONSULTORIO = "CALLE EL CHILAR S/N, SAN MATEO XOLOC, TEPOTZOTLÁN, ESTADO DE MÉXICO"

# CONSTANTES DOCTORES
DOCS_INFO = {
    "Dr. Emmanuel": {"nombre": "Dr. Emmanuel Tlacaelel Lopez Bermejo", "cedula": "12345678"},
    "Dra. Mónica": {"nombre": "Dra. Monica Montserrat Rodriguez Alvarez", "cedula": "87654321"}
}

# LISTAS MAESTRAS
LISTA_OCUPACIONES = ["Estudiante", "Empleado/a", "Empresario/a", "Hogar", "Comerciante", "Docente", "Sector Salud", "Jubilado/a", "Desempleado/a", "Otro"]
LISTA_PARENTESCOS = ["Madre", "Padre", "Abuelo(a)", "Tío(a)", "Hermano(a) Mayor", "Tutor Legal Designado", "Otro"]

# TEXTOS JURÍDICOS
CLAUSULA_CIERRE = "Adicionalmente, entiendo que pueden presentarse eventos imprevisibles en cualquier acto médico, tales como: reacciones alérgicas a los anestésicos o materiales (incluso si no tengo antecedentes conocidos), síncope (desmayo), trismus (dificultad para abrir la boca), hematomas, o infecciones secundarias. Acepto que el éxito del tratamiento depende también de mi biología y de seguir estrictamente las indicaciones post-operatorias."
TXT_DATOS_SENSIBLES = "DATOS PERSONALES SENSIBLES: Además de los datos de identificación, y para cumplir con la Normatividad Sanitaria (NOM-004-SSA3-2012 y NOM-013-SSA2-2015), recabamos: Estado de salud presente, pasado y futuro; Antecedentes Heredo-Familiares y Patológicos; Historial Farmacológico y Alergias; Hábitos de vida (tabaquismo/alcoholismo); e Imágenes diagnósticas/Biometría."
TXT_CONSENTIMIENTO_EXPRESO = "CONSENTIMIENTO EXPRESO: De conformidad con el artículo 9 de la LFPDPPP, otorgo mi consentimiento expreso para el tratamiento de mis datos sensibles. Reconozco que la firma digital en este documento tiene plena validez legal, equiparándose a mi firma autógrafa."

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
        .sticky-header { position: fixed; top: 0; left: 0; width: 100%; z-index: 99999; color: white; padding: 15px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.3); font-family: 'Helvetica Neue', sans-serif; transition: background-color 0.3s; }
        .alerta-medica { background-color: #FFEBEE; color: #D32F2F; padding: 20px; border-radius: 8px; border: 3px solid #D32F2F; font-weight: 900; font-size: 1.4em; text-align: center; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 15px; text-transform: uppercase; }
        .alerta-activa { animation: pulse-red 2s infinite; }
        @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(211, 47, 47, 0); } 100% { box-shadow: 0 0 0 0 rgba(211, 47, 47, 0); } }
        h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; transition: all 0.3s; }
        .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        input[type=number] { text-align: right; }
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
    try: c.execute(f"ALTER TABLE servicios ADD COLUMN duracion INTEGER")
    except: pass
    try: c.execute(f"ALTER TABLE citas ADD COLUMN duracion INTEGER")
    except: pass
    for col in ['parentesco_tutor', 'telefono_emergencia', 'antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo', 'domicilio', 'tutor', 'contacto_emergencia', 'ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
        except: pass
    try: c.execute(f"ALTER TABLE servicios ADD COLUMN consent_level TEXT")
    except: pass
    conn.commit()
    conn.close()

def actualizar_duraciones():
    tiempos = {
        "Profilaxis (Limpieza Ultrasónica)": 30, "Aplicación de Flúor (Niños)": 30, "Sellador de Fosetas y Fisuras": 30,
        "Resina Simple (1 cara)": 45, "Resina Compuesta (2 o más caras)": 60, "Reconstrucción de Muñón": 60, "Curación Temporal (Cavit)": 30,
        "Extracción Simple": 60, "Cirugía de Tercer Molar (Muela del Juicio)": 90, "Drenaje de Absceso": 45,
        "Endodoncia Anterior (1 conducto)": 90, "Endodoncia Premolar (2 conductos)": 90, "Endodoncia Molar (3+ conductos)": 120,
        "Corona Zirconia": 90, "Corona Metal-Porcelana": 90, "Incrustación Estética": 90, "Carilla de Porcelana": 90, "Poste de Fibra de Vidrio": 60,
        "Placa Total (Acrílico) - Una arcada": 30, "Prótesis Flexible (Valplast) - Unilateral": 30,
        "Blanqueamiento (Consultorio 2 sesiones)": 90, "Blanqueamiento (Guardas en casa)": 30,
        "Pago Inicial (Brackets Metálicos)": 60, "Mensualidad Ortodoncia": 30, "Recolocación de Bracket (Reposición)": 30,
        "Pulpotomía": 60, "Corona Acero-Cromo": 60, "Garantía (Retoque/Reparación)": 30
    }
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE servicios SET duracion = 30 WHERE duracion IS NULL")
    for nombre, mins in tiempos.items():
        c.execute("UPDATE servicios SET duracion = ? WHERE nombre_tratamiento = ?", (mins, nombre))
    conn.commit(); conn.close()

def actualizar_niveles_riesgo():
    mapping = {
        'HIGH_RISK': [
            "Extracción Simple", "Cirugía de Tercer Molar (Muela del Juicio)", "Drenaje de Absceso", 
            "Endodoncia Anterior (1 conducto)", "Endodoncia Premolar (2 conductos)", "Endodoncia Molar (3+ conductos)",
            "Corona Zirconia", "Corona Metal-Porcelana", "Incrustación Estética", "Carilla de Porcelana", "Poste de Fibra de Vidrio",
            "Pulpotomía", "Corona Acero-Cromo", "Pago Inicial (Brackets Metálicos)"
        ],
        'NO_CONSENT': [
            "Mensualidad Ortodoncia", "Recolocación de Bracket (Reposición)", "Garantía (Retoque/Reparación)"
        ]
    }
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE servicios SET consent_level = 'LOW_RISK'")
    for t in mapping['HIGH_RISK']:
        c.execute("UPDATE servicios SET consent_level = 'HIGH_RISK' WHERE nombre_tratamiento = ?", (t,))
    for t in mapping['NO_CONSENT']:
        c.execute("UPDATE servicios SET consent_level = 'NO_CONSENT' WHERE nombre_tratamiento = ?", (t,))
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
        domicilio TEXT, tutor TEXT, parentesco_tutor TEXT, contacto_emergencia TEXT, telefono_emergencia TEXT,
        ocupacion TEXT, estado_civil TEXT, motivo_consulta TEXT, exploracion_fisica TEXT, diagnostico TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT,
        duracion INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (id_evento INTEGER PRIMARY KEY AUTOINCREMENT, fecha_evento TEXT, usuario TEXT, accion TEXT, detalle TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL, consent_level TEXT, duracion INTEGER)''')
    conn.commit()
    conn.close()

def seed_data():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        tratamientos = [("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0),("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0),("Preventiva", "Sellador de Fosetas y Fisuras", 400.0, 0.0),("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0),("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0),("Operatoria", "Reconstrucción de Muñón", 1500.0, 0.0),("Operatoria", "Curación Temporal (Cavit)", 300.0, 0.0),("Cirugía", "Extracción Simple", 900.0, 0.0),("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0),("Cirugía", "Drenaje de Absceso", 800.0, 0.0),("Endodoncia", "Endodoncia Anterior (1 conducto)", 2800.0, 0.0),("Endodoncia", "Endodoncia Premolar (2 conductos)", 3200.0, 0.0),("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0),("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0),("Prótesis Fija", "Corona Metal-Porcelana", 3500.0, 600.0),("Prótesis Fija", "Incrustación Estética", 3800.0, 700.0),("Prótesis Fija", "Carilla de Porcelana", 5500.0, 1100.0),("Prótesis Fija", "Poste de Fibra de Vidrio", 1200.0, 0.0),("Prótesis Removible", "Placa Total (Acrílico) - Una arcada", 6000.0, 1200.0),("Prótesis Removible", "Prótesis Flexible (Valplast) - Unilateral", 4500.0, 900.0),("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0),("Estética", "Blanqueamiento (Guardas en casa)", 2500.0, 500.0),("Ortodoncia", "Pago Inicial (Brackets Metálicos)", 4000.0, 1500.0),("Ortodoncia", "Mensualidad Ortodoncia", 700.0, 0.0),("Ortodoncia", "Recolocación de Bracket (Reposición)", 200.0, 0.0),("Pediatría", "Pulpotomía", 1500.0, 0.0),("Pediatría", "Corona Acero-Cromo", 1800.0, 0.0),("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0)]
        c.executemany("INSERT INTO servicios (categoria, nombre_tratamiento, precio_lista, costo_laboratorio_base) VALUES (?,?,?,?)", tratamientos)
        conn.commit()
    conn.close()

init_db(); migrar_tablas(); seed_data(); actualizar_niveles_riesgo(); actualizar_duraciones()

# ==========================================
# 3. HELPERS Y FUNCIONES DE FORMATO
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def formato_nombre_legal(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    for old, new in {'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U','Ñ':'N'}.items(): 
        texto = texto.replace(old, new)
    return " ".join(texto.split())

def formato_titulo(texto):
    if not texto: return ""
    return str(texto).strip().title()

def formato_oracion(texto):
    if not texto: return ""
    txt = str(texto).strip()
    return txt.capitalize()

def limpiar_email(texto): return texto.lower().strip() if texto else ""

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)", (datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, formato_nombre_legal(detalle)))
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
        nombre = formato_nombre_legal(nombre); paterno = formato_nombre_legal(paterno)
        part1 = paterno[:3] if len(paterno) >=3 else paterno + "X"; part2 = nombre[0]; part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"

def formatear_telefono_db(numero): return re.sub(r'\D', '', str(numero))

# [FIX V34.0] GENERADOR DE SLOTS 8:00 - 18:00
def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("18:00", "%H:%M") # Cierre operativo para inicio de cita
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales(): return ["605 - Sueldos y Salarios", "612 - PFAEP (Actividad Empresarial)", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]
def get_usos_cfdi(): return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]

def verificar_disponibilidad(fecha_str, hora_str, duracion_minutos=30):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT hora, duracion FROM citas WHERE fecha=? AND estado_pago != 'CANCELADO' AND (precio_final IS NULL OR precio_final = 0)", (fecha_str,))
    citas_dia = c.fetchall()
    conn.close()
    
    try:
        req_start = datetime.strptime(hora_str, "%H:%M")
        req_end = req_start + timedelta(minutes=duracion_minutos)
        req_start_min = req_start.hour * 60 + req_start.minute
        req_end_min = req_end.hour * 60 + req_end.minute
        
        for cit in citas_dia:
            h_inicio = cit['hora']
            d_duracion = cit['duracion'] if cit['duracion'] else 30 
            c_start = datetime.strptime(h_inicio, "%H:%M")
            c_end = c_start + timedelta(minutes=d_duracion)
            c_start_min = c_start.hour * 60 + c_start.minute
            c_end_min = c_end.hour * 60 + c_end.minute
            
            if (req_start_min < c_end_min) and (req_end_min > c_start_min):
                return True 
        return False 
    except: return True 

def calcular_rfc_10(nombre, paterno, materno, nacimiento):
    try:
        nombre = formato_nombre_legal(nombre); paterno = formato_nombre_legal(paterno); materno = formato_nombre_legal(materno)
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
            try: self.image(LOGO_FILE, 10, 8, 50)
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
    try:
        img_data = re.sub('^data:image/.+;base64,', '', firma_img_data)
        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
        temp_filename = f"temp_sig_{int(time.time())}_{random.randint(1,1000)}.png"
        img.save(temp_filename)
        return temp_filename
    except: return None

def crear_pdf_consentimiento(paciente_full, nombre_doctor, cedula_doctor, tipo_doc, tratamientos_str, riesgos_str, firma_pac, firma_doc, testigos_data, nivel_riesgo, edad_paciente, tutor_info):
    pdf = PDFGenerator(); pdf.add_page()
    fecha_hoy = get_fecha_mx()
    paciente_full = formato_nombre_legal(paciente_full)
    nombre_doctor = formato_nombre_legal(nombre_doctor)
    
    if "Aviso" in tipo_doc:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "AVISO DE PRIVACIDAD INTEGRAL PARA PACIENTES", 0, 1, 'C'); pdf.ln(5)
        texto = f"""En cumplimiento estricto con lo dispuesto por la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (la "Ley"), su Reglamento y los Lineamientos del Aviso de Privacidad, se emite el presente documento:

IDENTIDAD Y DOMICILIO DEL RESPONSABLE
La clínica dental denominada comercialmente ROYAL DENTAL (en adelante "El Responsable"), con domicilio en {DIRECCION_CONSULTORIO}, es la entidad responsable del uso, manejo, almacenamiento y confidencialidad de sus datos personales.

{TXT_DATOS_SENSIBLES}

FINALIDADES DEL TRATAMIENTO
A) Prestación de servicios odontológicos. B) Creación y conservación del expediente clínico. C) Facturación y cobranza. D) Contacto para seguimiento.
Finalidades Secundarias: Envío de promociones y encuestas de calidad.

TRANSFERENCIA DE DATOS
Sus datos pueden ser compartidos con: Laboratorios dentales y gabinetes radiológicos (para prótesis/estudios), Especialistas interconsultantes, Compañías Aseguradoras y Autoridades sanitarias.

DERECHOS ARCO
Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse al tratamiento de sus datos presentando solicitud en recepción.

{TXT_CONSENTIMIENTO_EXPRESO}"""
        try: pdf.chapter_body(texto.encode('latin-1', 'replace').decode('latin-1'))
        except: pdf.chapter_body(texto)

    else:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "CARTA DE CONSENTIMIENTO INFORMADO", 0, 1, 'C'); pdf.ln(5)
        cuerpo = f"""LUGAR Y FECHA: Ciudad de México, a {fecha_hoy}
NOMBRE DEL PACIENTE: {paciente_full}
ODONTÓLOGO TRATANTE: {nombre_doctor} (Céd. Prof. {cedula_doctor})

DECLARACIÓN DEL PACIENTE:
Yo, el paciente arriba mencionado, declaro en pleno uso de mis facultades que he recibido una explicación clara sobre mi diagnóstico y el plan de tratamiento.

PROCEDIMIENTO(S) A REALIZAR: {tratamientos_str}

RIESGOS Y COMPLICACIONES ADVERTIDOS:
{riesgos_str}

{CLAUSULA_CIERRE}

OBLIGACIÓN DE MEDIOS Y NO DE RESULTADOS: Entiendo que la Odontología no es una ciencia exacta y el profesional se compromete a usar todos los medios técnicos, pero no puede garantizar resultados biológicos al 100%.

AUTORIZACIÓN: Autorizo la anestesia local y procedimientos necesarios, asumiendo los riesgos inherentes."""
        try: pdf.chapter_body(cuerpo.encode('latin-1', 'replace').decode('latin-1'))
        except: pdf.chapter_body(cuerpo)

    pdf.ln(10)
    y_firmas = pdf.get_y()
    
    pdf.set_font('Arial', 'B', 8)
    
    if edad_paciente < 18:
        pdf.text(20, y_firmas + 40, f"FIRMA DEL TUTOR: {tutor_info.get('nombre', '')} ({tutor_info.get('relacion', '')})")
        pdf.text(20, y_firmas + 45, f"En representación de: {paciente_full}")
    else:
        pdf.text(20, y_firmas + 40, "FIRMA DEL PACIENTE")
        pdf.text(20, y_firmas + 45, paciente_full) 
    
    if firma_pac:
        f_path = procesar_firma_digital(firma_pac)
        if f_path: pdf.image(f_path, x=20, y=y_firmas, w=45, h=30); os.remove(f_path)
    else: pdf.line(20, y_firmas + 35, 70, y_firmas + 35)

    if "Aviso" not in tipo_doc:
        pdf.text(110, y_firmas + 40, f"FIRMA ODONTOLOGO TRATANTE")
        if firma_doc:
            f_path_d = procesar_firma_digital(firma_doc)
            if f_path_d: pdf.image(f_path_d, x=110, y=y_firmas, w=45, h=30); os.remove(f_path_d)
        else: pdf.line(110, y_firmas + 35, 160, y_firmas + 35)

        if nivel_riesgo == "HIGH_RISK":
            pdf.ln(50)
            y_testigos = pdf.get_y()
            pdf.text(20, y_testigos + 40, f"TESTIGO 1: {formato_nombre_legal(testigos_data.get('n1',''))}")
            if testigos_data.get('img_t1'):
                 f_path_t1 = procesar_firma_digital(testigos_data['img_t1'])
                 if f_path_t1: pdf.image(f_path_t1, x=20, y=y_testigos, w=45, h=30); os.remove(f_path_t1)
            else: pdf.line(20, y_testigos + 35, 70, y_testigos + 35)

            pdf.text(110, y_testigos + 40, f"TESTIGO 2: {formato_nombre_legal(testigos_data.get('n2',''))}")
            if testigos_data.get('img_t2'):
                 f_path_t2 = procesar_firma_digital(testigos_data['img_t2'])
                 if f_path_t2: pdf.image(f_path_t2, x=110, y=y_testigos, w=45, h=30); os.remove(f_path_t2)
            else: pdf.line(110, y_testigos + 35, 160, y_testigos + 35)
        
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

def crear_pdf_historia(p, historial):
    pdf = PDFGenerator(); pdf.add_page()
    nombre_p = formato_nombre_legal(f"{p['nombre']} {p['apellido_paterno']} {p.get('apellido_materno','')}")
    edad, _ = calcular_edad_completa(p.get('fecha_nacimiento', ''))
    
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "HISTORIA CLÍNICA ODONTOLÓGICA (NOM-004-SSA3-2012)", 0, 1, 'C'); pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230); pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "I. FICHA DE IDENTIFICACIÓN", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    info = f"""Nombre: {nombre_p}\nEdad: {edad} | Sexo: {p.get('sexo','N/A')} | Nacimiento: {p.get('fecha_nacimiento','N/A')}\nOcupación: {formato_titulo(p.get('ocupacion','N/A'))} | Estado Civil: {formato_titulo(p.get('estado_civil','N/A'))}\nDomicilio: {formato_titulo(p.get('domicilio','N/A'))}\nTel: {p['telefono']} | Email: {p.get('email','N/A')}\nContacto Emergencia: {formato_nombre_legal(p.get('contacto_emergencia','N/A'))} ({p.get('telefono_emergencia','S/N')})\nTutor: {formato_nombre_legal(p.get('tutor','N/A'))} ({p.get('parentesco_tutor','')})"""
    pdf.multi_cell(0, 5, info, 1); pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "II. ANTECEDENTES (ANAMNESIS)", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    ant = f"""HEREDO-FAMILIARES (AHF): {formato_oracion(p.get('ahf','Negados'))}\n\nPERSONALES PATOLÓGICOS (APP - Alergias/Enf): {formato_oracion(p.get('app','Negados'))}\n\nNO PATOLÓGICOS (APNP): {formato_oracion(p.get('apnp','Negados'))}"""
    pdf.multi_cell(0, 5, ant, 1); pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "III. MOTIVO DE CONSULTA Y DIAGNÓSTICO", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    diag = f"""Motivo: {formato_oracion(p.get('motivo_consulta','N/A'))}\n\nExploración Física: {formato_oracion(p.get('exploracion_fisica','N/A'))}\n\nDiagnóstico: {formato_oracion(p.get('diagnostico','N/A'))}"""
    pdf.multi_cell(0, 5, diag, 1); pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, "IV. NOTAS DE EVOLUCIÓN", 0, 1, 'L')
    
    if not historial.empty:
        pdf.set_font('Arial', 'B', 8)
        x_start = pdf.get_x()
        pdf.cell(25, 6, "FECHA", 1, 0, 'C')
        pdf.cell(60, 6, "TRATAMIENTO", 1, 0, 'C')
        pdf.cell(105, 6, "NOTAS / EVOLUCIÓN", 1, 1, 'C')
        
        pdf.set_font('Arial', '', 8)
        
        for _, row in historial.iterrows():
            txt_fecha = str(row['fecha'])
            txt_trat = str(row['tratamiento'])[:45] 
            txt_nota = str(row['notas']) if row['notas'] else ""
            txt_nota = formato_oracion(txt_nota) 
            
            x_curr = pdf.get_x()
            y_curr = pdf.get_y()
            
            pdf.set_xy(x_curr + 85, y_curr) 
            pdf.multi_cell(105, 5, txt_nota, 0, 'L') 
            y_end = pdf.get_y()
            h_row = y_end - y_curr
            
            if h_row < 6: h_row = 6
            
            if y_curr + h_row > 270: 
                pdf.add_page()
                y_curr = pdf.get_y()
                pdf.set_font('Arial', 'B', 8)
                pdf.cell(25, 6, "FECHA", 1, 0, 'C')
                pdf.cell(60, 6, "TRATAMIENTO", 1, 0, 'C')
                pdf.cell(105, 6, "NOTAS / EVOLUCIÓN", 1, 1, 'C')
                pdf.set_font('Arial', '', 8)
                y_curr = pdf.get_y()

            pdf.set_xy(x_curr, y_curr)
            pdf.rect(x_curr, y_curr, 25, h_row) 
            pdf.set_xy(x_curr, y_curr)
            pdf.multi_cell(25, 5, txt_fecha, 0, 'C') 
            
            pdf.rect(x_curr + 25, y_curr, 60, h_row) 
            pdf.set_xy(x_curr + 25, y_curr)
            pdf.multi_cell(60, 5, txt_trat, 0, 'L') 
            
            pdf.rect(x_curr + 85, y_curr, 105, h_row) 
            pdf.set_xy(x_curr + 85, y_curr)
            pdf.multi_cell(105, 5, txt_nota, 0, 'L') 
            
            pdf.set_xy(x_curr, y_curr + h_row)
            
    val = pdf.output(dest='S'); return val.encode('latin-1') if isinstance(val, str) else bytes(val)

# ==========================================
# 5. SISTEMA DE LOGIN
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None
if 'id_paciente_activo' not in st.session_state: st.session_state.id_paciente_activo = None

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

# [MODIFICADO V30.1] HEADER CON ALERTA VISUAL AGRESIVA
def render_header(conn):
    if st.session_state.id_paciente_activo:
        try:
            p = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{st.session_state.id_paciente_activo}'", conn).iloc[0]
            edad, _ = calcular_edad_completa(p['fecha_nacimiento'])
            
            raw_app = str(p.get('app', '')).strip()
            # Lógica: Si hay texto > 2 letras y no dice "negado", es alerta
            tiene_alerta = len(raw_app) > 2 and not any(x in raw_app.upper() for x in ["NEGADO", "NINGUNO", "N/A", "SIN"])
            
            bg_color = "#D32F2F" if tiene_alerta else "#002B5B"
            clase_animacion = "alerta-activa" if tiene_alerta else ""
            icono_alerta = "🚨 ALERTA MÉDICA:" if tiene_alerta else "✅ APP:"
            texto_app = raw_app if tiene_alerta else "Negados / Sin datos relevantes"
            
            st.markdown(f"""
            <div class="sticky-header {clase_animacion}" style="background-color: {bg_color};">
                <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;">
                    <span style="font-size:1.3em; font-weight:bold;">👤 {p['nombre']} {p['apellido_paterno']}</span>
                    <span style="font-size:1.1em;">🎂 {edad} Años</span>
                    <span style="font-size:1.2em; font-weight:bold; background-color: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px;">
                        {icono_alerta} {texto_app}
                    </span>
                </div>
            </div>
            <div style="margin-bottom: 80px;"></div> 
            """, unsafe_allow_html=True)
        except Exception as e: pass

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    conn = get_db_connection()
    render_header(conn)
    
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_column_width=True)
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Documentos & Firmas", "5. Control Asistencia"])
    
    with st.sidebar.expander("🛠️ Mantenimiento"):
        if st.button("🗑️ RESETEAR BASE DE DATOS (CUIDADO)", type="primary"):
            try:
                conn_temp = get_db_connection(); c_temp = conn_temp.cursor()
                c_temp.execute("DELETE FROM pacientes"); c_temp.execute("DELETE FROM citas"); c_temp.execute("DELETE FROM asistencia")
                conn_temp.commit(); conn_temp.close()
                st.cache_data.clear()
                if 'perfil' in st.session_state: del st.session_state['perfil']
                st.success("✅ Sistema y memoria limpiados."); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error crítico: {e}")

    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()

    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        with st.expander("🔍 BUSCAR CITAS", expanded=False):
            q_cita = st.text_input("Buscar cita por nombre:")
            if q_cita:
                # [FIX V35.0] QUERY ROBUSTA CON FALLBACK PARA NOMBRE
                query = f"""
                    SELECT c.fecha, c.hora, c.tratamiento, c.doctor_atendio, c.nombre_paciente as nombre_prospecto,
                           p.nombre, p.apellido_paterno, p.apellido_materno, c.duracion, c.estado_pago
                    FROM citas c
                    LEFT JOIN pacientes p ON c.id_paciente = p.id_paciente
                    WHERE c.nombre_paciente LIKE '%{formato_nombre_legal(q_cita)}%'
                    AND (c.precio_final IS NULL OR c.precio_final = 0)
                    ORDER BY c.timestamp DESC
                """
                df = pd.read_sql(query, conn)
                
                if not df.empty:
                    # [FIX V35.0] Lógica de nombre con respaldo
                    df['NOMBRE DEL PACIENTE'] = df.apply(lambda x: f"{x['nombre']} {x['apellido_paterno']} {x['apellido_materno'] if x['apellido_materno'] else ''}".strip() if x['nombre'] else x['nombre_prospecto'], axis=1)
                    
                    df_show = df[['fecha', 'hora', 'NOMBRE DEL PACIENTE', 'tratamiento', 'doctor_atendio']].copy()
                    df_show.columns = ['FECHA', 'HORA', 'NOMBRE DEL PACIENTE', 'TRATAMIENTO', 'DOCTOR']
                    
                    df_show.index = range(1, len(df_show) + 1)
                    df_show.index.name = 'CVO'
                    
                    st.dataframe(df_show, use_container_width=True)
                else:
                    st.info("No se encontraron citas.")

        col_cal1, col_cal2 = st.columns([1, 2.5])
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver_obj = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX), format="DD/MM/YYYY")
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            
            with st.expander("➕ Agendar Cita Nueva", expanded=False):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                with tab_reg:
                    # [FIX V35.1] CASCADA DINAMICA - REGISTRADO
                    servicios = pd.read_sql("SELECT * FROM servicios", conn)
                    cats = servicios['categoria'].unique()
                    
                    # 1. Selector de PACIENTE
                    pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                    lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not pacientes_raw.empty else []
                    
                    with st.form("cita_registrada", clear_on_submit=True):
                        p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                        
                        # 2. Selector CATEGORÍA (Filtro Nivel 1)
                        # Nota: Streamlit Forms no permiten reactividad instantánea interna (refresh parcial).
                        # Para "simular" dinamismo real dentro de un form, se debe usar st.empty o sacar los selectores fuera.
                        # PERO: Para mantener la estructura solicitada, usaremos la estrategia de sacar los selectores de "Qué se hará" FUERA del form submit.
                        # CORRECCION ARQUITECTURA V35.1: Sacamos los selectores fuera del form para que sean reactivos, 
                        # y luego pasamos sus valores al form o usamos un botón simple.
                        # Dado que el usuario pide "no cambies lo demás", ajustaremos la logica visual aqui mismo.
                        pass # Placeholder para romper el form estricto
                    
                    # [RE-INGENIERÍA UX V35.1] - FLUJO REACTIVO FUERA DE FORM
                    st.info("Configuración de Cita (Registrado)")
                    col_r1, col_r2 = st.columns(2)
                    p_sel_r = col_r1.selectbox("Paciente*", ["Seleccionar..."] + lista_pac, key="p_reg_sel")
                    cat_sel_r = col_r2.selectbox("Categoría Tratamiento", cats, key="cat_reg_sel")
                    
                    # Filtrar tratamientos basados en categoria
                    trats_filtrados_r = servicios[servicios['categoria'] == cat_sel_r]['nombre_tratamiento'].unique()
                    trat_sel_r = st.selectbox("Tratamiento*", trats_filtrados_r, key="trat_reg_sel")
                    
                    # Calcular duración
                    dur_default_r = 30
                    if trat_sel_r:
                        row_dur = servicios[servicios['nombre_tratamiento'] == trat_sel_r]
                        if not row_dur.empty: dur_default_r = int(row_dur.iloc[0]['duracion'])
                    
                    col_r3, col_r4, col_r5 = st.columns(3)
                    duracion_cita_r = col_r3.number_input("Duración (min)", value=dur_default_r, step=30, key="dur_reg")
                    h_sel_r = col_r4.selectbox("Hora Inicio", generar_slots_tiempo(), key="hora_reg")
                    d_sel_r = col_r5.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"], key="doc_reg")
                    
                    urgencia_r = st.checkbox("🚨 Es Urgencia / Sobrecupo", key="urg_reg")
                    
                    if st.button("💾 Agendar Cita (Registrado)"):
                        ocupado = verificar_disponibilidad(fecha_ver_str, h_sel_r, duracion_cita_r)
                        if ocupado and not urgencia_r: st.error(f"⚠️ Horario OCUPADO. Revise la agenda.")
                        elif p_sel_r != "Seleccionar...":
                            id_p = p_sel_r.split(" - ")[0]; nom_p = p_sel_r.split(" - ")[1]
                            c = conn.cursor()
                            nota_final = formato_oracion(f"Cita: {trat_sel_r}")
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria, duracion) 
                                                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                        (int(time.time()), fecha_ver_str, h_sel_r, id_p, nom_p, "General", trat_sel_r, d_sel_r, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", nota_final, "", 0, cat_sel_r, duracion_cita_r))
                            conn.commit(); st.success(f"Agendado"); time.sleep(1); st.rerun()
                        else: st.error("Seleccione paciente")


                with tab_new:
                    # [FIX V35.1] CASCADA DINAMICA - PROSPECTO
                    st.info("Configuración de Cita (Prospecto)")
                    col_p1, col_p2 = st.columns(2)
                    nombre_pros = col_p1.text_input("Nombre Completo*", key="nom_pros")
                    tel_pros = col_p2.text_input("Teléfono (10)*", max_chars=10, key="tel_pros")
                    
                    col_p3, col_p4 = st.columns(2)
                    cat_sel_p = col_p3.selectbox("Categoría Tratamiento", cats, key="cat_pros_sel")
                    
                    # Filtro reactivo
                    trats_filtrados_p = servicios[servicios['categoria'] == cat_sel_p]['nombre_tratamiento'].unique()
                    trat_sel_p = col_p4.selectbox("Tratamiento*", trats_filtrados_p, key="trat_pros_sel")
                    
                    # Duración reactiva
                    dur_default_p = 30
                    if trat_sel_p:
                        row_dur_p = servicios[servicios['nombre_tratamiento'] == trat_sel_p]
                        if not row_dur_p.empty: dur_default_p = int(row_dur_p.iloc[0]['duracion'])
                    
                    col_p5, col_p6, col_p7 = st.columns(3)
                    duracion_cita_p = col_p5.number_input("Duración (min)", value=dur_default_p, step=30, key="dur_pros_inp")
                    hora_pros = col_p6.selectbox("Hora Inicio", generar_slots_tiempo(), key="hora_pros")
                    doc_pros = col_p7.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"], key="doc_pros")
                    
                    urgencia_p = st.checkbox("🚨 Es Urgencia", key="urg_pros")
                    
                    if st.button("💾 Agendar Prospecto"):
                        ocupado = verificar_disponibilidad(fecha_ver_str, hora_pros, duracion_cita_p)
                        if ocupado and not urgencia_p: st.error(f"⚠️ Horario OCUPADO.")
                        elif nombre_pros and len(tel_pros) == 10:
                            id_temp = f"PROS-{int(time.time())}"; nom_final = formato_nombre_legal(nombre_pros)
                            c = conn.cursor()
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria, duracion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                        (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", trat_sel_p, doc_pros, 0, 0, 0, "Pendiente", f"Tel: {tel_pros}", 0, 0, "No", 0, 0, "", "No", "", 0, cat_sel_p, duracion_cita_p))
                            conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()
                        else: st.error("Datos incompletos")
            
            st.markdown("### 🔄 Modificar Agenda")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                if not df_dia.empty:
                    lista_citas_dia = [f"{r['hora']} - {r['nombre_paciente']} ({r['tratamiento']})" for i, r in df_dia.iterrows()]
                    cita_sel = st.selectbox("Seleccionar Cita:", ["Seleccionar..."] + lista_citas_dia)
                    if cita_sel != "Seleccionar...":
                        hora_target = cita_sel.split(" - ")[0]; nom_target = cita_sel.split(" - ")[1].split(" (")[0]
                        col_inputs, col_actions = st.columns([2, 1])
                        with col_inputs:
                            new_date_res = st.date_input("Nueva Fecha", datetime.now(TZ_MX))
                            new_h_res = st.selectbox("Nueva Hora", generar_slots_tiempo(), key="reag_time")
                        with col_actions:
                            st.write("") 
                            st.write("") 
                            if st.button("🗓️ MOVER", use_container_width=True):
                                c = conn.cursor(); c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", (format_date_latino(new_date_res), new_h_res, fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.success(f"Reagendada"); time.sleep(1); st.rerun()
                            
                            if st.button("❌ CANCELAR", type="secondary", use_container_width=True):
                                 c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                 conn.commit(); st.warning("Cancelada"); time.sleep(1); st.rerun()
                            
                            if st.button("🗑️ ELIMINAR", type="primary", use_container_width=True):
                                 c = conn.cursor(); c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                 conn.commit(); registrar_auditoria("Consultorio", "ELIMINACION CITA", f"Se eliminó cita de {nom_target}"); st.error("Eliminado."); time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 {fecha_ver_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_ver_str]
                slots = generar_slots_tiempo()
                
                # Mapa de ocupación
                ocupacion_map = {} 
                
                for _, r in df_dia.iterrows():
                    if r['estado_pago'] == 'CANCELADO': continue
                    h_inicio = r['hora']
                    # [FIX V35.0] DURACION DEFAULT 30 SI ES NULL/0
                    try:
                        dur = int(r['duracion']) if r['duracion'] and r['duracion'] > 0 else 30
                    except: dur = 30
                    
                    try:
                        start_dt = datetime.strptime(h_inicio, "%H:%M")
                        for i in range(0, dur, 30):
                            bloque_time = start_dt + timedelta(minutes=i)
                            bloque_str = bloque_time.strftime("%H:%M")
                            if bloque_str not in ocupacion_map:
                                if i == 0:
                                    ocupacion_map[bloque_str] = {"tipo": "inicio", "data": r, "dur": dur}
                                else:
                                    ocupacion_map[bloque_str] = {"tipo": "bloqueado", "parent": r['nombre_paciente']}
                    except: pass
                
                for slot in slots:
                    if slot in ocupacion_map:
                        info = ocupacion_map[slot]
                        if info["tipo"] == "inicio":
                            r = info["data"]
                            color = "#FF5722" if "PROS" in str(r['id_paciente']) else "#002B5B"
                            st.markdown(f"""<div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;"><b>{slot} | {r['nombre_paciente']}</b><br><span style="color:#666; font-size:0.9em;">{r['tratamiento']} ({info['dur']} min)</span></div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; background-color:#f0f0f0; color:#888; font-size:0.8em; margin-left: 20px;">⬇️ EN TRATAMIENTO ({info['parent']})</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)

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
                    st.session_state.id_paciente_activo = id_sel_str
                    
                    edad, tipo_pac = calcular_edad_completa(p_data.get('fecha_nacimiento', ''))
                    
                    antecedentes = str(p_data.get('app', '')).strip()
                    if antecedentes and len(antecedentes) > 2 and "NEGADO" not in antecedentes.upper():
                        st.markdown(f"""
                        <div class='alerta-medica'>
                            <span>🚨</span>
                            <span>ATENCIÓN CLÍNICA: {antecedentes}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    c_info, c_hist = st.columns([1, 2])
                    with c_info:
                        st.markdown(f"""<div class="royal-card"><h3>👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3><b>Edad:</b> {edad} Años<br><b>Tel:</b> {format_tel_visual(p_data['telefono'])}<br><b>RFC:</b> {p_data.get('rfc', 'N/A')}</div>""", unsafe_allow_html=True)
                        
                        hoy = datetime.now(TZ_MX).date()
                        df_raw_notas = pd.read_sql(f"SELECT fecha, tratamiento, notas FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn)
                        df_raw_notas['fecha_dt'] = pd.to_datetime(df_raw_notas['fecha'], format="%d/%m/%Y", errors='coerce').dt.date
                        hist_notas = df_raw_notas[df_raw_notas['fecha_dt'] <= hoy].drop(columns=['fecha_dt'])
                        
                        if st.button("🖨️ Descargar Historia (PDF)"):
                            pdf_bytes = crear_pdf_historia(p_data, hist_notas)
                            clean_name = f"{p_data['id_paciente']}_HISTORIAL_{formato_nombre_legal(p_data['nombre'])}_{formato_nombre_legal(p_data['apellido_paterno'])}.pdf".replace(" ", "_")
                            st.download_button("📥 Bajar PDF", pdf_bytes, clean_name, "application/pdf")
                    with c_hist:
                        st.markdown("#### 📜 Notas")
                        if not hist_notas.empty:
                            df_notes = hist_notas[['fecha', 'tratamiento', 'notas']].copy()
                            df_notes.index = range(1, len(df_notes) + 1)
                            df_notes.index.name = "CVO" 
                            df_notes.columns = ["FECHA", "TRATAMIENTO", "NOTAS"]
                            st.dataframe(
                                df_notes,
                                use_container_width=True,
                                hide_index=False,
                                column_config={
                                    "CVO": st.column_config.NumberColumn("CVO", width="small"),
                                    "NOTAS": st.column_config.TextColumn("NOTAS", width="large")
                                }
                            )
                        else:
                            st.info("Sin notas registradas.")

        with tab_n:
            st.markdown("#### Formulario Alta (NOM-004)")
            with st.form("alta_paciente", clear_on_submit=True):
                # DATOS PERSONALES
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)")
                paterno = c2.text_input("A. Paterno")
                materno = c3.text_input("A. Materno")
                
                c4, c5, c6 = st.columns(3)
                nacimiento = c4.date_input("Fecha de Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now(TZ_MX).date(), value=datetime.now(TZ_MX).date())
                sexo = c5.selectbox("Sexo", ["Masculino", "Femenino"])
                ocupacion = c6.selectbox("Ocupación", LISTA_OCUPACIONES)
                
                st.markdown("**Datos de Contacto y Residencia**")
                ce1, ce2, ce3 = st.columns(3)
                tel = ce1.text_input("Celular Paciente (10)", max_chars=10)
                email = ce2.text_input("Email")
                estado_civil = ce3.selectbox("Estado Civil", ["Soltero", "Casado", "Divorciado", "Viudo", "Unión Libre"])
                domicilio = st.text_input("Domicilio Completo")

                edad_calc = 0
                if nacimiento:
                    hoy = datetime.now().date()
                    edad_calc = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
                
                if edad_calc < 18:
                    st.info(f"Paciente menor de edad ({edad_calc} años). Tutor obligatorio.")
                
                st.markdown("**Responsable / Tutor (Obligatorio si es menor)**")
                ct1, ct2 = st.columns(2)
                tutor = ct1.text_input("Nombre Completo Tutor")
                parentesco = ct2.selectbox("Parentesco", LISTA_PARENTESCOS)

                st.markdown("**Contacto de Emergencia**")
                cem1, cem2 = st.columns(2)
                contacto_emer_nom = cem1.text_input("Nombre Contacto Emergencia")
                contacto_emer_tel = cem2.text_input("Tel Emergencia (10)", max_chars=10)
                
                motivo_consulta = st.text_area("Motivo de Consulta*")

                st.markdown("**Historia Médica**")
                ahf = st.text_area("AHF", placeholder="Diabetes, Hipertensión..."); app = st.text_area("APP", placeholder="Alergias, Cirugías..."); apnp = st.text_area("APNP", placeholder="Tabaquismo, Alcoholismo...")
                st.markdown("**Exploración y Diagnóstico (Dr)**")
                exploracion = st.text_area("Exploración Física"); diagnostico = st.text_area("Diagnóstico Presuntivo")
                
                rfc_final = "" 
                regimen = ""
                uso_cfdi = ""
                cp = ""
                
                with st.expander("Datos de Facturación (Opcional)", expanded=False):
                    cf1, cf2, cf3 = st.columns([2, 1, 1])
                    rfc_base = cf1.text_input("RFC (Sin Homoclave)", max_chars=13)
                    homoclave = cf2.text_input("Homoclave", max_chars=3)
                    cp = cf3.text_input("C.P.", max_chars=5)
                    
                    cf4, cf5 = st.columns(2)
                    regimen = cf4.selectbox("Régimen", get_regimenes_fiscales())
                    uso_cfdi = cf5.selectbox("Uso CFDI", get_usos_cfdi())
                    
                aviso = st.checkbox("Acepto Aviso de Privacidad")
                
                if st.form_submit_button("💾 GUARDAR EXPEDIENTE"):
                    if not aviso: st.error("Acepte Aviso Privacidad"); st.stop()
                    if not tel.isdigit() or len(tel) != 10: st.error("Teléfono Paciente incorrecto"); st.stop()
                    if contacto_emer_tel and (not contacto_emer_tel.isdigit() or len(contacto_emer_tel) != 10): 
                        st.error("Teléfono Emergencia incorrecto"); st.stop()
                    if not nombre or not paterno: st.error("Nombre incompleto"); st.stop()
                    
                    if edad_calc < 18:
                        if not tutor or not parentesco:
                            st.error("⛔ ERROR: Para menores de 18 años, el Nombre del Tutor y Parentesco son OBLIGATORIOS."); st.stop()

                    if rfc_base:
                        rfc_final = formato_nombre_legal(rfc_base) + formato_nombre_legal(homoclave)
                    else:
                        base_10 = calcular_rfc_10(nombre, paterno, materno, nacimiento)
                        homo_sufijo = formato_nombre_legal(homoclave) if homoclave else "XXX"
                        rfc_final = base_10 + homo_sufijo
                    
                    nuevo_id = generar_id_unico(nombre, paterno, nacimiento)
                    c = conn.cursor()
                    c.execute("INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, email, rfc, regimen, uso_cfdi, cp, nota_fiscal, sexo, estado, fecha_nacimiento, antecedentes_medicos, ahf, app, apnp, ocupacion, estado_civil, domicilio, tutor, contacto_emergencia, motivo_consulta, exploracion_fisica, diagnostico, parentesco_tutor, telefono_emergencia) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (nuevo_id, get_fecha_mx(), formato_nombre_legal(nombre), formato_nombre_legal(paterno), formato_nombre_legal(materno), tel, limpiar_email(email), rfc_final, regimen, uso_cfdi, cp, "", sexo, "Activo", format_date_latino(nacimiento), "", formato_oracion(ahf), formato_oracion(app), formato_oracion(apnp), formato_titulo(ocupacion), estado_civil, formato_titulo(domicilio), formato_nombre_legal(tutor), formato_nombre_legal(contacto_emer_nom), formato_oracion(motivo_consulta), formato_oracion(exploracion), formato_oracion(diagnostico), parentesco, contacto_emer_tel))
                    conn.commit(); st.success(f"✅ Paciente {nombre} guardado."); time.sleep(1.5); st.rerun()
        
        with tab_e:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
                sel_edit = st.selectbox("Buscar Paciente:", ["Select..."] + lista_edit)
                if sel_edit != "Select...":
                    id_target = sel_edit.split(" - ")[0]; p = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    with st.form("form_editar_full"):
                        st.info("Editando a: " + p['nombre'])
                        ec1, ec2, ec3 = st.columns(3)
                        e_nom = ec1.text_input("Nombre", p['nombre']); e_pat = ec2.text_input("A. Paterno", p['apellido_paterno']); e_mat = ec3.text_input("A. Materno", p['apellido_materno'])
                        ec4, ec5 = st.columns(2)
                        e_tel = ec4.text_input("Teléfono", p['telefono']); e_email = ec5.text_input("Email", p['email'])
                        st.markdown("**Médico & Contacto**")
                        e_app = st.text_area("APP (Alergias)", p['app'] if p['app'] else ""); e_ahf = st.text_area("AHF", p['ahf'] if p['ahf'] else ""); e_apnp = st.text_area("APNP", p['apnp'] if p['apnp'] else "")
                        cem1, cem2 = st.columns(2)
                        e_cont_nom = cem1.text_input("Nombre Contacto Emergencia", p.get('contacto_emergencia', ''))
                        e_cont_tel = cem2.text_input("Tel Emergencia", p.get('telefono_emergencia', ''))

                        st.markdown("**Fiscal**")
                        ec6, ec7, ec8 = st.columns(3)
                        e_rfc = ec6.text_input("RFC Completo", p['rfc']); e_cp = ec7.text_input("C.P.", p['cp'])
                        idx_reg = 0
                        reg_list = get_regimenes_fiscales()
                        if p['regimen'] in reg_list: idx_reg = reg_list.index(p['regimen'])
                        e_reg = ec8.selectbox("Régimen", reg_list, index=idx_reg)
                        
                        if st.form_submit_button("💾 ACTUALIZAR TODO"):
                            c = conn.cursor()
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, app=?, ahf=?, apnp=?, rfc=?, cp=?, regimen=?, contacto_emergencia=?, telefono_emergencia=? WHERE id_paciente=?", 
                                     (formato_nombre_legal(e_nom), formato_nombre_legal(e_pat), formato_nombre_legal(e_mat), formatear_telefono_db(e_tel), limpiar_email(e_email), formato_oracion(e_app), formato_oracion(e_ahf), formato_oracion(e_apnp), formato_nombre_legal(e_rfc), e_cp, e_reg, formato_nombre_legal(e_cont_nom), e_cont_tel, id_target))
                            conn.commit(); st.success("Datos actualizados."); time.sleep(1.5); st.rerun()

    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Finanzas")
        pacientes = pd.read_sql("SELECT * FROM pacientes", conn); servicios = pd.read_sql("SELECT * FROM servicios", conn)
        if not pacientes.empty:
            sel = st.selectbox("Paciente:", pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
            id_p = sel.split(" - ")[0]; nom_p = sel.split(" - ")[1]
            st.session_state.id_paciente_activo = id_p
            
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            df_f = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_p}' AND estado_pago != 'CANCELADO' AND (precio_final > 0 OR monto_pagado > 0)", conn)
            if not df_f.empty:
                deuda = pd.to_numeric(df_f['saldo_pendiente'], errors='coerce').fillna(0).sum()
                c1, c2 = st.columns(2); c1.metric("Deuda", f"${deuda:,.2f}")
                if deuda > 0: c2.error("PENDIENTE") 
                else: c2.success("AL CORRIENTE")
                
                df_show = df_f[['fecha', 'tratamiento', 'precio_final', 'monto_pagado', 'saldo_pendiente']].reset_index(drop=True)
                df_show.index = df_show.index + 1
                df_show.index.name = 'CONSECUTIVO'
                df_show.columns = ['FECHA', 'TRATAMIENTO', 'PRECIO FINAL', 'MONTO PAGADO', 'SALDO PENDIENTE']
                st.dataframe(
                    df_show, 
                    use_container_width=True,
                    column_config={
                        "CONSECUTIVO": st.column_config.NumberColumn("CONSECUTIVO", width="small")
                    }
                )
                
            st.markdown("---"); st.subheader("Nuevo Plan")
            c1, c2 = st.columns(2)
            if not servicios.empty:
                cat_sel = c1.selectbox("Categoría", servicios['categoria'].unique()); filt = servicios[servicios['categoria'] == cat_sel]
                trat_sel = c2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]; precio_sug = float(item['precio_lista']); costo_lab = float(item['costo_laboratorio_base'])
                riesgo_auto = RIESGOS_DB.get(trat_sel, "Riesgos generales inherentes al procedimiento.")
            else:
                cat_sel = "Manual"; trat_sel = c2.text_input("Tratamiento"); precio_sug = 0.0; costo_lab = 0.0; riesgo_auto = ""
            
            with st.form("cobro", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                precio = c1.number_input("Precio", value=precio_sug, step=50.0); abono = c2.number_input("Abono", step=50.0); saldo = precio - abono
                c3.metric("Saldo", f"${saldo:,.2f}")
                num_sessions = st.number_input("Sesiones Estimadas", min_value=1, value=1)
                doc_name = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"]); metodo = st.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia", "Garantía", "Pendiente de Pago"])
                notas = st.text_area("Notas Evolución"); agendar = st.checkbox("¿Agendar Cita?"); f_cita = st.date_input("Fecha"); h_cita = st.selectbox("Hora", generar_slots_tiempo())
                if st.form_submit_button("Registrar"):
                    if not notas.strip():
                         st.warning("⚠️ Guardando sin nota de evolución. Se recomienda documentar el procedimiento.")
                    
                    ocupado = verificar_disponibilidad(format_date_latino(f_cita), h_cita) if agendar else False
                    if ocupado: st.error("Horario Ocupado.")
                    else:
                        estatus = "Pagado" if saldo <= 0 else "Pendiente"
                        c = conn.cursor()
                        nota_final = formato_oracion(notas)
                        c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                 (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, cat_sel, trat_sel, doc_name, precio_sug, precio, 0, metodo, estatus, nota_final, abono, saldo, get_fecha_mx(), costo_lab))
                        if agendar:
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago, categoria) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                                     (int(time.time())+1, format_date_latino(f_cita), h_cita, id_p, nom_p, "Tratamiento", trat_sel, doc_name, "Pendiente", cat_sel))
                        conn.commit(); st.success("Registrado"); time.sleep(1); st.rerun()

    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Centro Legal"); df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", ["..."]+df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
            if sel != "...":
                id_target = sel.split(" - ")[0]; p_obj = df_p[df_p['id_paciente'] == id_target].iloc[0]
                st.session_state.id_paciente_activo = id_target
                
                tipo_doc = st.selectbox("Documento", ["Consentimiento Informado", "Aviso de Privacidad"])
                
                tratamiento_legal = ""
                riesgo_legal = ""
                nivel_riesgo = "LOW_RISK" 
                t1_name = ""; t2_name = ""
                img_t1 = None; img_t2 = None
                
                if "Consentimiento" in tipo_doc:
                    # BUSCAR TRATAMIENTOS DE HOY
                    hoy_str = get_fecha_mx()
                    citas_hoy = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_target}' AND fecha='{hoy_str}' AND (precio_final > 0 OR monto_pagado > 0)", conn)
                    
                    if not citas_hoy.empty:
                        lista_tratamientos = citas_hoy['tratamiento'].unique().tolist()
                        tratamiento_legal = ", ".join(lista_tratamientos)
                        riesgo_legal = ""
                        nivel_riesgo = "LOW_RISK" 
                        
                        servicios = pd.read_sql("SELECT * FROM servicios", conn)
                        
                        for trat in lista_tratamientos:
                            riesgo_item = RIESGOS_DB.get(trat, "")
                            if riesgo_item: riesgo_legal += f"- {trat}: {riesgo_item}\n"
                            if not servicios.empty:
                                row_s = servicios[servicios['nombre_tratamiento'] == trat]
                                if not row_s.empty and row_s.iloc[0]['consent_level'] == 'HIGH_RISK':
                                    nivel_riesgo = 'HIGH_RISK'
                        
                        st.info(f"📋 Procedimientos de hoy: {tratamiento_legal}")
                        if nivel_riesgo == 'HIGH_RISK': st.error("🔴 ALTO RIESGO DETECTADO: Se requieren testigos.")
                        else: st.success("🟢 BAJO RIESGO: Solo Doctor y Paciente.")
                        
                    else:
                        st.warning("⚠️ No hay tratamientos registrados HOY para este paciente. Registre primero en 'Planes de Tratamiento'.")
                        st.stop()
                
                col_doc_sel = st.columns(2)
                doc_name_sel = col_doc_sel[0].selectbox("Odontólogo Tratante:", list(DOCS_INFO.keys()))
                
                if nivel_riesgo != 'NO_CONSENT':
                    st.markdown("### Firmas Digitales")
                    col_firmas_1, col_firmas_2 = st.columns(2)
                    
                    with col_firmas_1:
                        st.caption("Firma del Paciente")
                        canvas_pac = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_paciente")
                    
                    if "Aviso" not in tipo_doc:
                        with col_firmas_2:
                            st.caption(f"Firma Dr. {doc_name_sel.split()[1]}")
                            canvas_doc = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_doctor")
                        
                        if nivel_riesgo == 'HIGH_RISK':
                            st.markdown("#### Testigos (Obligatorios)")
                            c_t1, c_t2 = st.columns(2)
                            with c_t1:
                                t1_name = st.text_input("Nombre Testigo 1")
                                canvas_t1 = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_testigo1")
                            with c_t2:
                                t2_name = st.text_input("Nombre Testigo 2")
                                canvas_t2 = st_canvas(stroke_width=2, height=150, width=300, drawing_mode="freedraw", key="firma_testigo2")

                    if st.button("Generar PDF Legal"):
                        bloqueo = False
                        if "Consentimiento" in tipo_doc and nivel_riesgo == 'HIGH_RISK':
                            if not (t1_name and t2_name):
                                st.error("⛔ ERROR LEGAL: Faltan nombres de testigos para procedimiento de Alto Riesgo."); bloqueo = True
                            if canvas_t1.image_data is None or canvas_t2.image_data is None: 
                                st.error("⛔ ERROR: Faltan firmas de testigos."); bloqueo = True

                        if not bloqueo:
                            img_pac = None; img_doc = None
                            
                            if canvas_pac.image_data is not None:
                                if not np.all(canvas_pac.image_data[:,:,3] == 0):
                                    img = Image.fromarray(canvas_pac.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_pac = base64.b64encode(buf.getvalue()).decode()
                            
                            if "Aviso" not in tipo_doc:
                                if canvas_doc.image_data is not None:
                                    if not np.all(canvas_doc.image_data[:,:,3] == 0):
                                        img = Image.fromarray(canvas_doc.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_doc = base64.b64encode(buf.getvalue()).decode()
                                
                                if nivel_riesgo == 'HIGH_RISK':
                                    if canvas_t1.image_data is not None:
                                        if not np.all(canvas_t1.image_data[:,:,3] == 0):
                                            img = Image.fromarray(canvas_t1.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_t1 = base64.b64encode(buf.getvalue()).decode()
                                    if canvas_t2.image_data is not None:
                                        if not np.all(canvas_t2.image_data[:,:,3] == 0):
                                            img = Image.fromarray(canvas_t2.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG"); img_t2 = base64.b64encode(buf.getvalue()).decode()

                            doc_full = DOCS_INFO[doc_name_sel]['nombre']
                            cedula_full = DOCS_INFO[doc_name_sel]['cedula']
                            nombre_paciente_full = f"{p_obj['nombre']} {p_obj['apellido_paterno']} {p_obj.get('apellido_materno','')}"
                            
                            testigos_dict = {'n1': t1_name, 'n2': t2_name, 'img_t1': img_t1, 'img_t2': img_t2}
                            
                            edad_actual, _ = calcular_edad_completa(p_obj['fecha_nacimiento'])
                            tutor_info = {'nombre': p_obj.get('tutor', ''), 'relacion': p_obj.get('parentesco_tutor', '')}
                            
                            pdf_bytes = crear_pdf_consentimiento(nombre_paciente_full, doc_full, cedula_full, tipo_doc, tratamiento_legal, riesgo_legal, img_pac, img_doc, testigos_dict, nivel_riesgo, edad_actual, tutor_info)
                            
                            prefix = "CONSENTIMIENTO" if "Consentimiento" in tipo_doc else "AVISO_PRIVACIDAD"
                            clean_filename = f"{prefix}_{formato_nombre_legal(p_obj['nombre'])}_{formato_nombre_legal(p_obj['apellido_paterno'])}.pdf".replace(" ", "_")
                            
                            st.download_button("Descargar PDF Firmado", pdf_bytes, clean_filename, "application/pdf")
                else:
                    st.warning("⚠️ No se genera documento legal para este concepto.")

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
