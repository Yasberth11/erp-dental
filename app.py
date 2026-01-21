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
import shutil

# ==========================================
# 1. CONFIGURACIÓN Y SISTEMA DE ARCHIVOS
# ==========================================
st.set_page_config(page_title="Royal Dental Manager", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")
TZ_MX = pytz.timezone('America/Mexico_City')
LOGO_FILE = "logo.png"
LOGO_UNAM = "logo_unam.png" 
DIRECCION_CONSULTORIO = "CALLE EL CHILAR S/N, SAN MATEO XOLOC, TEPOTZOTLÁN, ESTADO DE MÉXICO"
CARPETA_PACIENTES = "pacientes_files"

# Asegurar directorio de archivos
if not os.path.exists(CARPETA_PACIENTES):
    os.makedirs(CARPETA_PACIENTES)

# [V46.0] ESTILO CSS ROYAL (RESTAURADO DE V41)
st.markdown("""
    <style>
    .stApp { background-color: #F4F6F6; }
    /* TARJETA ROYAL: Fondo blanco, sombra suave, borde dorado izquierdo */
    .royal-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
        border-left: 6px solid #D4AF37; 
        margin-bottom: 25px; 
    }
    
    /* HEADER FIJO ROJO/AZUL */
    .sticky-header { 
        position: fixed; 
        top: 0; 
        left: 0; 
        width: 100%; 
        z-index: 99999; 
        color: white; 
        padding: 15px; 
        text-align: center; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.3); 
        font-family: 'Helvetica Neue', sans-serif; 
        transition: background-color 0.3s; 
    }
    
    /* ALERTA MEDICA EN EXPEDIENTE */
    .alerta-medica { 
        background-color: #FFEBEE; 
        color: #D32F2F; 
        padding: 15px; 
        border-radius: 8px; 
        border: 2px solid #D32F2F; 
        font-weight: bold; 
        font-size: 1.1em; 
        text-align: center; 
        margin-bottom: 20px; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        gap: 10px; 
        text-transform: uppercase; 
    }
    
    h1, h2, h3, h4 { color: #002B5B !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button { background-color: #D4AF37; color: #002B5B; border: none; font-weight: bold; width: 100%; transition: all 0.3s; }
    .stButton>button:hover { background-color: #B5952F; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    input[type=number] { text-align: right; }
    div[data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# CONSTANTES DOCTORES (ORDEN: DRA. MONICA PRIMERO)
DOCS_INFO = {
    "Dra. Mónica": {
        "nombre": "Dra. Monica Montserrat Rodriguez Alvarez", 
        "cedula": "87654321",
        "universidad": "UNAM - FES Iztacala",
        "especialidad": "Cirujano Dentista"
    },
    "Dr. Emmanuel": {
        "nombre": "Dr. Emmanuel Tlacaelel Lopez Bermejo", 
        "cedula": "12345678", 
        "universidad": "UNAM - FES Iztacala",
        "especialidad": "Cirujano Dentista"
    }
}
LISTA_DOCTORES = list(DOCS_INFO.keys())

# LISTAS MAESTRAS
LISTA_OCUPACIONES = ["Estudiante", "Empleado/a", "Empresario/a", "Hogar", "Comerciante", "Docente", "Sector Salud", "Jubilado/a", "Desempleado/a", "Otro"]
LISTA_PARENTESCOS = ["Madre", "Padre", "Abuelo(a)", "Tío(a)", "Hermano(a) Mayor", "Tutor Legal Designado", "Otro"]

# BASES DE DATOS DE TEXTOS (COMPLETAS)
CLAUSULA_CIERRE = "Adicionalmente, entiendo que pueden presentarse eventos imprevisibles en cualquier acto médico, tales como: reacciones alérgicas a los anestésicos o materiales (incluso si no tengo antecedentes conocidos), síncope (desmayo), trismus (dificultad para abrir la boca), hematomas, o infecciones secundarias. Acepto que el éxito del tratamiento depende también de mi biología y de seguir estrictamente las indicaciones post-operatorias."
TXT_DATOS_SENSIBLES = "DATOS PERSONALES SENSIBLES: Además de los datos de identificación, y para cumplir con la Normatividad Sanitaria (NOM-004-SSA3-2012 y NOM-013-SSA2-2015), recabamos: Estado de salud presente, pasado y futuro; Antecedentes Heredo-Familiares y Patológicos; Historial Farmacológico y Alergias; Hábitos de vida (tabaquismo/alcoholismo); e Imágenes diagnósticas/Biometría."
TXT_CONSENTIMIENTO_EXPRESO = "CONSENTIMIENTO EXPRESO: De conformidad con el artículo 9 de la LFPDPPP, otorgo mi consentimiento expreso para el tratamiento de mis datos sensibles. Reconozco que la firma digital en este documento tiene plena validez legal, equiparándose a mi firma autógrafa."

MEDICAMENTOS_DB = {
    "Dolor Leve": "Ketorolaco 10mg.\nTomar 1 tableta cada 8 horas por 3 días en caso de dolor.",
    "Dolor Fuerte": "1. Ketorolaco/Tramadol 10mg/25mg. Tomar 1 tableta cada 8 horas por 3 días.\n2. Ibuprofeno 600mg. Tomar 1 tableta cada 8 horas por 3 días (intercalar con el anterior).",
    "Infección": "1. Amoxicilina/Ac. Clavulánico 875mg/125mg. Tomar 1 tableta cada 12 horas por 7 días.\n2. Ibuprofeno 400mg. Tomar 1 tableta cada 8 horas por 3 días para inflamación.",
    "Alergia Penicilina": "Clindamicina 300mg.\nTomar 1 cápsula cada 6 horas por 7 días.",
    "Profilaxis Antibiótica": "Amoxicilina 2g (4 tabletas de 500mg).\nTomar las 4 tabletas juntas en una sola toma, 1 hora antes del procedimiento.",
    "Pediátrico (General)": "Paracetamol Suspensión.\nAdministrar dosis según peso del paciente cada 6-8 horas en caso de fiebre o dolor."
}

INDICACIONES_DB = {
    "Extracción / Cirugía": """1. CONTROL DE SANGRADO: Muerda la gasa firmemente por 30-40 minutos. Si persiste sangrado activo, coloque una nueva.
2. PROHIBICIONES (24h): NO escupir, NO usar popotes (succión), NO enjuagarse, NO fumar ni beber alcohol (Riesgo grave de infección).
3. ALIMENTACIÓN: Dieta blanda y fría por 48 horas (Nieves sin semillas, gelatinas). Cero grasas, irritantes o semillas pequeñas.
4. HIGIENE: No cepillar la zona hoy. Mañana inicie higiene suave. Enjuagues pasivos con agua y sal.
5. TERAPIA TÉRMICA: Compresas frías hoy (15min puesto/15min descanso). Calor húmedo después de 48 horas.""",

    "Blanqueamiento": """1. DIETA BLANCA (48h): Evite alimentos con colorantes (Café, vino, refresco de cola, salsas oscuras, frutos rojos).
2. SENSIBILIDAD: Evite bebidas muy frías/calientes y cítricos por 3 días. Use analgésico si hay molestia.
3. HÁBITOS: No fumar (pigmentación inmediata).
4. MANTENIMIENTO: El resultado no es permanente, depende de sus hábitos.""",

    "Endodoncia": """1. CUIDADO INMEDIATO: No comer hasta pasar la anestesia.
2. RIESGO DE FRACTURA: Su diente está debilitado. NO mastique cosas duras con ese lado hasta tener la restauración final (corona). Si el diente se fractura, podría requerir extracción.
3. SEGUIMIENTO: Es OBLIGATORIO acudir a la cita de rehabilitación definitiva.""",

    "General / Limpieza": """1. Siga su técnica de cepillado habitual.
2. Utilice hilo dental diariamente.
3. Acuda a sus revisiones semestrales."""
}

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
    
    # [NUEVO V48.0] COLUMNAS PARA EL SEMÁFORO Y OBSERVACIONES
    # Estas son OBLIGATORIAS para que funcionen las mejoras visuales que pediste
    try: c.execute("ALTER TABLE pacientes ADD COLUMN nota_administrativa TEXT")
    except: pass
    try: c.execute("ALTER TABLE citas ADD COLUMN observaciones TEXT")
    except: pass

    # [V41.0] MIGRACIÓN DE TABLA CITAS (NUEVO STATUS) Y ODONTOGRAMA
    try: c.execute(f"ALTER TABLE citas ADD COLUMN estatus_asistencia TEXT")
    except: pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS odontograma (
        id_paciente TEXT, diente TEXT, estado TEXT, fecha_actualizacion TEXT,
        PRIMARY KEY (id_paciente, diente))''')

    # Migraciones previas (Seguridad y Mantenimiento)
    try: c.execute(f"ALTER TABLE servicios ADD COLUMN duracion INTEGER")
    except: pass
    try: c.execute(f"ALTER TABLE citas ADD COLUMN duracion INTEGER")
    except: pass
    
    # Columnas pacientes (Historial médico completo)
    for col in ['parentesco_tutor', 'telefono_emergencia', 'antecedentes_medicos', 'ahf', 'app', 'apnp', 'sexo', 'domicilio', 'tutor', 'contacto_emergencia', 'ocupacion', 'estado_civil', 'motivo_consulta', 'exploracion_fisica', 'diagnostico']:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    
    # Columnas citas (Financiero y Categorías)
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
        except: pass
    
    try: c.execute(f"ALTER TABLE servicios ADD COLUMN consent_level TEXT")
    except: pass
    conn.commit(); conn.close()

# [V41 RESTAURADO] FUNCIONES DE MANTENIMIENTO (No las borres, son útiles)
def actualizar_duraciones():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE servicios SET duracion = 30 WHERE duracion IS NULL")
    conn.commit(); conn.close()

def actualizar_niveles_riesgo():
    conn = get_db_connection(); c = conn.cursor()
    # Asegura que todos los servicios tengan un nivel de riesgo por defecto
    c.execute("UPDATE servicios SET consent_level = 'LOW_RISK' WHERE consent_level IS NULL")
    conn.commit(); conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tablas base (Pacientes, Citas, Auditoria, Asistencia, Servicios, Odontograma)
    
    # [V48.0] INCLUIMOS nota_administrativa EN LA CREACIÓN
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (id_paciente TEXT PRIMARY KEY, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT, antecedentes_medicos TEXT, ahf TEXT, app TEXT, apnp TEXT, domicilio TEXT, tutor TEXT, parentesco_tutor TEXT, contacto_emergencia TEXT, telefono_emergencia TEXT, ocupacion TEXT, estado_civil TEXT, motivo_consulta TEXT, exploracion_fisica TEXT, diagnostico TEXT, nota_administrativa TEXT)''')
    
    # [V48.0] INCLUIMOS observaciones EN LA CREACIÓN
    c.execute('''CREATE TABLE IF NOT EXISTS citas (timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT, duracion INTEGER, estatus_asistencia TEXT, observaciones TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (id_evento INTEGER PRIMARY KEY AUTOINCREMENT, fecha_evento TEXT, usuario TEXT, accion TEXT, detalle TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, doctor TEXT, hora_entrada TEXT, hora_salida TEXT, horas_totales REAL, estado TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servicios (categoria TEXT, nombre_tratamiento TEXT, precio_lista REAL, costo_laboratorio_base REAL, consent_level TEXT, duracion INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS odontograma (id_paciente TEXT, diente TEXT, estado TEXT, fecha_actualizacion TEXT, PRIMARY KEY (id_paciente, diente))''')
    conn.commit(); conn.close()

def seed_data():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        tratamientos = [("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0, 'LOW_RISK', 30),("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0, 'LOW_RISK', 30),("Preventiva", "Sellador de Fosetas y Fisuras", 400.0, 0.0, 'LOW_RISK', 30),("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0, 'LOW_RISK', 45),("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0, 'LOW_RISK', 60),("Operatoria", "Reconstrucción de Muñón", 1500.0, 0.0, 'LOW_RISK', 60),("Operatoria", "Curación Temporal (Cavit)", 300.0, 0.0, 'LOW_RISK', 30),("Cirugía", "Extracción Simple", 900.0, 0.0, 'HIGH_RISK', 60),("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0, 'HIGH_RISK', 90),("Cirugía", "Drenaje de Absceso", 800.0, 0.0, 'HIGH_RISK', 45),("Endodoncia", "Endodoncia Anterior (1 conducto)", 2800.0, 0.0, 'HIGH_RISK', 90),("Endodoncia", "Endodoncia Premolar (2 conductos)", 3200.0, 0.0, 'HIGH_RISK', 90),("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0, 'HIGH_RISK', 120),("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0, 'HIGH_RISK', 90),("Prótesis Fija", "Corona Metal-Porcelana", 3500.0, 600.0, 'HIGH_RISK', 90),("Prótesis Fija", "Incrustación Estética", 3800.0, 700.0, 'HIGH_RISK', 90),("Prótesis Fija", "Carilla de Porcelana", 5500.0, 1100.0, 'HIGH_RISK', 90),("Prótesis Fija", "Poste de Fibra de Vidrio", 1200.0, 0.0, 'HIGH_RISK', 60),("Prótesis Removible", "Placa Total (Acrílico) - Una arcada", 6000.0, 1200.0, 'LOW_RISK', 30),("Prótesis Removible", "Prótesis Flexible (Valplast) - Unilateral", 4500.0, 900.0, 'LOW_RISK', 30),("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0, 'LOW_RISK', 90),("Estética", "Blanqueamiento (Guardas en casa)", 2500.0, 500.0, 'LOW_RISK', 30),("Ortodoncia", "Pago Inicial (Brackets Metálicos)", 4000.0, 1500.0, 'HIGH_RISK', 60),("Ortodoncia", "Mensualidad Ortodoncia", 700.0, 0.0, 'NO_CONSENT', 30),("Ortodoncia", "Recolocación de Bracket (Reposición)", 200.0, 0.0, 'NO_CONSENT', 30),("Pediatría", "Pulpotomía", 1500.0, 0.0, 'HIGH_RISK', 60),("Pediatría", "Corona Acero-Cromo", 1800.0, 0.0, 'HIGH_RISK', 60),("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0, 'NO_CONSENT', 30)]
        c.executemany("INSERT INTO servicios (categoria, nombre_tratamiento, precio_lista, costo_laboratorio_base, consent_level, duracion) VALUES (?,?,?,?,?,?)", tratamientos)
        conn.commit()
    conn.close()

# Ejecución de inicialización completa
init_db(); migrar_tablas(); seed_data(); actualizar_niveles_riesgo(); actualizar_duraciones()
# ==========================================
# 3. HELPERS (FUNCIONES DE AYUDA)
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def normalizar_texto_pdf(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    # CAMBIO V46.1: ELIMINADA LA Ñ DE LA LISTA DE REEMPLAZOS
    replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ü", "U"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    return texto

def formato_nombre_legal(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    # CAMBIO V46.1: Tambien permitimos Ñ en nombres legales eliminando el reemplazo
    for old, new in {'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U'}.items(): 
        texto = texto.replace(old, new)
    return " ".join(texto.split())

def formato_titulo(texto): return str(texto).strip().title() if texto else ""
def formato_oracion(texto): return str(texto).strip().capitalize() if texto else ""
def limpiar_email(texto): return texto.lower().strip() if texto else ""

def format_tel_visual(tel): 
    # Validar que tel sea string y tenga 10 digitos
    tel = str(tel).strip()
    if len(tel) == 10 and tel.isdigit():
        return f"{tel[:2]}-{tel[2:6]}-{tel[6:]}"
    return tel

def calcular_edad_completa(nacimiento_input):
    hoy = datetime.now().date()
    try:
        if isinstance(nacimiento_input, str): nacimiento = datetime.strptime(nacimiento_input, "%d/%m/%Y").date()
        else: nacimiento = nacimiento_input
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return edad, "MENOR" if edad < 18 else "ADULTO"
    except: return 0, "N/A"

def generar_id_unico(nombre, paterno, nacimiento):
    try:
        nombre = formato_nombre_legal(nombre); paterno = formato_nombre_legal(paterno)
        part1 = paterno[:3] if len(paterno) >=3 else paterno + "X"; part2 = nombre[0]; part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"

def formatear_telefono_db(numero): return re.sub(r'\D', '', str(numero))

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("18:00", "%H:%M") 
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales(): return ["605 - Sueldos y Salarios", "612 - PFAEP (Actividad Empresarial)", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]
def get_usos_cfdi(): return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]

def verificar_disponibilidad(fecha_str, hora_str, duracion_minutos=30):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT hora, duracion FROM citas WHERE fecha=? AND estado_pago != 'CANCELADO' AND (estatus_asistencia IS NULL OR estatus_asistencia != 'Canceló') AND (precio_final IS NULL OR precio_final = 0)", (fecha_str,))
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

# [V41.0] GESTOR DE ODONTOGRAMA
def actualizar_diente(id_paciente, diente):
    conn = get_db_connection()
    c = conn.cursor()
    # Ciclo de estados: Sano -> Caries -> Resina -> Ausente -> Corona -> Sano
    estados = ["Sano", "Caries", "Resina", "Ausente", "Corona"]
    # Obtener estado actual
    c.execute("SELECT estado FROM odontograma WHERE id_paciente=? AND diente=?", (id_paciente, diente))
    row = c.fetchone()
    estado_actual = row[0] if row else "Sano"
    
    idx = estados.index(estado_actual)
    nuevo_estado = estados[(idx + 1) % len(estados)]
    
    c.execute("INSERT OR REPLACE INTO odontograma (id_paciente, diente, estado, fecha_actualizacion) VALUES (?,?,?,?)", (id_paciente, diente, nuevo_estado, get_fecha_mx()))
    conn.commit()
    conn.close()

def obtener_estado_dientes(id_paciente):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT diente, estado FROM odontograma WHERE id_paciente=?", (id_paciente,))
    data = dict(c.fetchall())
    conn.close()
    return data

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
            # Calculo horas simple
            c.execute("UPDATE asistencia SET hora_salida=?, estado=? WHERE id_registro=?", (hora_actual, "Finalizado", row[0]))
            conn.commit(); return True, f"Salida: {hora_actual}"
    except Exception as e: return False, str(e)
    finally: conn.close()

# ==========================================
# 4. GENERADOR DE PDF PROFESIONALES (LEGAL SUITE)
# ==========================================
class PDFGenerator(FPDF):
    def __init__(self): super().__init__()
    def header(self):
        if os.path.exists(LOGO_FILE):
            try: self.image(LOGO_FILE, 10, 8, 30)
            except: pass
        
        # [V41.0] LOGO UNAM
        #if os.path.exists(LOGO_UNAM):
        #    try: self.image(LOGO_UNAM, 170, 8, 25) # Logo UNAM
        #    except: pass

        self.set_font('Arial', 'B', 14); self.set_text_color(0, 43, 91)
        self.cell(0, 10, 'ROYAL DENTAL', 0, 1, 'C'); self.ln(1)
        self.set_font('Arial', 'I', 9); self.set_text_color(100, 100, 100)
        self.cell(0, 5, DIRECCION_CONSULTORIO, 0, 1, 'C'); self.ln(10)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} - Documento Oficial Royal Dental', 0, 0, 'C')
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

# [V42.0] PDF RECETA FIX (SIN EMOJIS)
def crear_pdf_receta(datos):
    pdf = PDFGenerator()
    
    # --- PÁGINA 1: RECETA MÉDICA ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "RECETA MEDICA", 0, 1, 'R')
    pdf.ln(5)
    
    # Datos Doctor
    pdf.set_font('Arial', 'B', 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, datos['doctor_nombre'], 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, f"{datos['doctor_uni']} - CED. PROF: {datos['doctor_cedula']}", 0, 1)
    pdf.cell(0, 5, f"ESPECIALIDAD: {datos['doctor_esp']}", 0, 1)
    
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2); pdf.ln(10)
    
    # Datos Paciente (FIX AÑOS)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(20, 6, "PACIENTE:", 0, 0); pdf.set_font('Arial', '', 10)
    pdf.cell(100, 6, normalizar_texto_pdf(datos['paciente_nombre']), 0, 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(15, 6, "FECHA:", 0, 0); pdf.set_font('Arial', '', 10)
    pdf.cell(30, 6, datos['fecha'], 0, 1)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(15, 6, "EDAD:", 0, 0)
    # [V46.1] FIX AÑOS (Ahora sí permitido)
    edad_txt = f"{datos['edad']} AÑOS"
    pdf.set_font('Arial', '', 10); pdf.cell(30, 6, edad_txt, 0, 1) 
    pdf.ln(10)
    
    # Cuerpo Receta
    pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, "PRESCRIPCION", 1, 1, 'L', 1)
    pdf.set_font('Courier', '', 11); pdf.set_text_color(0, 0, 50)
    pdf.multi_cell(0, 8, datos['medicamentos'])
    
    # Firma
    pdf.ln(40)
    pdf.set_draw_color(0, 0, 0); pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, "FIRMA DEL MEDICO", 0, 1, 'C')

    # --- PÁGINA 2: INDICACIONES Y LEGAL ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14); pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, "INDICACIONES Y CUIDADOS POST-TRATAMIENTO", 0, 1, 'C')
    pdf.ln(5)
    
    # Texto Indicaciones
    pdf.set_font('Arial', '', 10); pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, datos['indicaciones'])
    pdf.ln(10)
    
    # SEÑALES DE ALERTA (SIN EMOJIS)
    pdf.set_fill_color(255, 235, 238); pdf.set_text_color(200, 0, 0); pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "SEÑALES DE ALERTA", 1, 1, 'L', 1)
    pdf.set_font('Arial', '', 10); pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, "Contacte al consultorio si presenta: Sangrado que no cede tras 40 min de presion, Fiebre >38 C, Dificultad para respirar/tragar, o Reaccion alergica (ronchas/hinchazon).")
    pdf.ln(5)
    
    # DESLINDE LEGAL
    pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 8, "DESLINDE DE RESPONSABILIDAD Y SEGUIMIENTO", 1, 1, 'L', 1)
    pdf.set_font('Arial', 'I', 8)
    pdf.multi_cell(0, 5, "El exito del tratamiento depende del seguimiento profesional. El consultorio NO se hace responsable por complicaciones, infecciones o fracasos derivados de negligencia en estos cuidados, automedicacion o la INASISTENCIA a las citas de control programadas. La falta de seguimiento exime al clinico de garantias.")

    val = pdf.output(dest='S'); return val.encode('latin-1', 'replace') if isinstance(val, str) else bytes(val)

def crear_recibo_pago(datos_recibo):
    pdf = PDFGenerator(); pdf.add_page()
    pdf.set_font('Arial', 'B', 16); pdf.cell(0, 10, 'RECIBO DE PAGO', 0, 1, 'C'); pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 10)
    pdf.cell(130, 8, "DATOS DEL PACIENTE", 1, 0, 'L', 1); pdf.cell(60, 8, "DETALLES DEL RECIBO", 1, 1, 'L', 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(130, 8, f"Paciente: {normalizar_texto_pdf(datos_recibo['paciente'])}", 1, 0); pdf.cell(60, 8, f"Folio: {datos_recibo['folio']}", 1, 1)
    pdf.cell(130, 8, f"RFC: {datos_recibo.get('rfc', 'XAXX010101000')}", 1, 0); pdf.cell(60, 8, f"Fecha: {datos_recibo['fecha']}", 1, 1)
    pdf.ln(5)

    # [V46.0] ALINEACION DE TOTALES REPARADA (TABLA COMPACTA)
    pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(220, 230, 240)
    pdf.cell(8, 8, "CVO", 1, 0, 'C', 1)
    pdf.cell(65, 8, "TRATAMIENTO", 1, 0, 'C', 1)
    pdf.cell(35, 8, "DOCTOR", 1, 0, 'C', 1)
    pdf.cell(20, 8, "COSTO", 1, 0, 'C', 1)
    pdf.cell(20, 8, "ABONO", 1, 0, 'C', 1)
    pdf.cell(20, 8, "SALDO", 1, 0, 'C', 1)
    pdf.cell(22, 8, "METODO", 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 7) 
    idx = 1
    if datos_recibo['items_hoy']:
        for item in datos_recibo['items_hoy']:
            pdf.cell(8, 6, str(idx), 1, 0, 'C')
            pdf.cell(65, 6, normalizar_texto_pdf(item['tratamiento'][:35]), 1, 0)
            pdf.cell(35, 6, normalizar_texto_pdf(item.get('doctor_atendio', '')[:20]), 1, 0)
            pdf.cell(20, 6, f"${item['precio_final']:,.2f}", 1, 0, 'R')
            pdf.cell(20, 6, f"${item['monto_pagado']:,.2f}", 1, 0, 'R')
            pdf.cell(20, 6, f"${item['saldo_pendiente']:,.2f}", 1, 0, 'R')
            pdf.cell(22, 6, item['metodo_pago'][:15], 1, 1, 'C')
            idx += 1
    else:
        pdf.cell(190, 6, "SIN MOVIMIENTOS REGISTRADOS HOY", 1, 1, 'C')
    pdf.ln(5)
    
    if datos_recibo['items_deuda']:
        pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(255, 235, 238)
        pdf.cell(190, 8, "SALDOS ANTERIORES PENDIENTES", 1, 1, 'L', 1)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(25, 6, "FECHA", 1, 0); pdf.cell(125, 6, "TRATAMIENTO", 1, 0); pdf.cell(40, 6, "SALDO PENDIENTE", 1, 1, 'R')
        pdf.set_font('Arial', '', 8)
        for d in datos_recibo['items_deuda']:
            pdf.cell(25, 6, d['fecha'], 1, 0)
            pdf.cell(125, 6, normalizar_texto_pdf(d['tratamiento'][:80]), 1, 0)
            pdf.cell(40, 6, f"${d['saldo_pendiente']:,.2f}", 1, 1, 'R')
        pdf.ln(5)

    # [V46.0] TOTALES ALINEADOS A LA DERECHA (Fixed Widths)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(110, 8, "", 0, 0)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 8, "TOTAL TRATAMIENTO:", 1, 0, 'R', 1)
    pdf.cell(40, 8, f"${datos_recibo['total_tratamiento_hoy']:,.2f}", 1, 1, 'R')
    
    pdf.cell(110, 8, "", 0, 0)
    pdf.cell(40, 8, "TOTAL PAGADO:", 1, 0, 'R', 1)
    pdf.cell(40, 8, f"${datos_recibo['total_pagado_hoy']:,.2f}", 1, 1, 'R')
    
    if datos_recibo['saldo_total_global'] > 0:
        pdf.cell(110, 8, "", 0, 0)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(40, 8, "PENDIENTE DE PAGO:", 1, 0, 'R', 1)
        pdf.cell(40, 8, f"${datos_recibo['saldo_total_global']:,.2f}", 1, 1, 'R')
        pdf.set_text_color(0, 0, 0)
    
    pdf.ln(10)
    pdf.set_y(-30); pdf.set_font('Arial', 'I', 7)
    pdf.multi_cell(0, 4, "Este documento es un comprobante interno. Si requiere factura fiscal (CFDI), favor de solicitarla dentro del mes en curso.", 0, 'C')
    val = pdf.output(dest='S'); return val.encode('latin-1', 'replace') if isinstance(val, str) else bytes(val)

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
        
    val = pdf.output(dest='S'); return val.encode('latin-1', 'replace') if isinstance(val, str) else bytes(val)

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

def render_header(conn):
    if st.session_state.id_paciente_activo:
        try:
            p = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{st.session_state.id_paciente_activo}'", conn).iloc[0]
            edad, _ = calcular_edad_completa(p['fecha_nacimiento'])
            raw_app = str(p.get('app', '')).strip()
            tiene_alerta = len(raw_app) > 2 and not any(x in raw_app.upper() for x in ["NEGADO", "NINGUNO", "N/A", "SIN"])
            bg_color = "#D32F2F" if tiene_alerta else "#002B5B"
            clase_animacion = "alerta-activa" if tiene_alerta else ""
            icono_alerta = "🚨 ALERTA MÉDICA:" if tiene_alerta else "✅ APP:"
            texto_app = raw_app if tiene_alerta else "Negados / Sin datos relevantes"
            st.markdown(f"""<div class="sticky-header {clase_animacion}" style="background-color: {bg_color};"><div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;"><span style="font-size:1.3em; font-weight:bold;">👤 {p['nombre']} {p['apellido_paterno']}</span><span style="font-size:1.1em;">🎂 {edad} Años</span><span style="font-size:1.2em; font-weight:bold; background-color: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px;">{icono_alerta} {texto_app}</span></div></div><div style="margin-bottom: 80px;"></div>""", unsafe_allow_html=True)
        except Exception as e: pass

# ==========================================
# 6. VISTA CONSULTORIO
# ==========================================
def vista_consultorio():
    conn = get_db_connection(); render_header(conn)
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_column_width=True)
    st.sidebar.markdown("### 🏥 Royal Dental"); st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión de Pacientes", "3. Consentimientos", "4. Tratamientos", "5. Recetas", "6. Control Asistencia"])
    
    with st.sidebar.expander("🛠️ Mantenimiento"):
        if st.button("🗑️ RESETEAR BASE DE DATOS (CUIDADO)", type="primary"):
            try:
                conn_temp = get_db_connection(); c_temp = conn_temp.cursor()
                c_temp.execute("DELETE FROM pacientes"); c_temp.execute("DELETE FROM citas"); c_temp.execute("DELETE FROM asistencia"); c_temp.execute("DELETE FROM odontograma")
                conn_temp.commit(); conn_temp.close(); st.cache_data.clear()
                if 'perfil' in st.session_state: del st.session_state['perfil']
                st.success("✅ Sistema y memoria limpiados."); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error crítico: {e}")
    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()

    if menu == "1. Agenda & Citas":
        # [ESTILO CSS OPTIMIZADO PARA LISTA COMPACTA]
        st.markdown("""
            <style>
            div[data-testid="column"] { justify-content: flex-start !important; }
            
            /* Estilo de los botones dentro de la lista */
            .stButton button {
                padding: 2px 8px !important; 
                font-size: 0.85rem !important;
                height: auto !important;
                min-height: 0px !important;
                margin-top: 0px !important;
            }
            
            /* Fila de la Cita */
            .cita-row-compact {
                background-color: white;
                padding: 8px 12px;
                border-radius: 6px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                margin-bottom: 4px; /* Espacio mínimo entre filas */
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            /* Textos */
            .cita-time { font-weight: bold; color: #002B5B; font-size: 1rem; width: 60px; }
            .cita-name { font-weight: 600; color: #333; font-size: 0.95rem; margin-bottom: 2px; }
            .cita-desc { color: #666; font-size: 0.8rem; }
            </style>
        """, unsafe_allow_html=True)
        
        # Inicializador de estados
        if 'form_reset_id' not in st.session_state: st.session_state.form_reset_id = 0
        reset_id = st.session_state.form_reset_id

        st.title("📅 Control de Citas")
        
        # [SELECTOR DE FECHA MAESTRO]
        col_fecha, col_resumen = st.columns([1, 3])
        with col_fecha:
            fecha_ver_obj = st.date_input("📅 Seleccionar Fecha:", datetime.now(TZ_MX))
            fecha_ver_str = format_date_latino(fecha_ver_obj)
            es_hoy = (fecha_ver_str == get_fecha_mx())
        
        # ==============================================================================
        # ZONA 1: DASHBOARD SCROLLABLE (LA "CAJA" QUE PEDISTE)
        # ==============================================================================
        st.markdown(f"#### ⚡ Gestión Rápida: {fecha_ver_str}")
        
        # Traemos datos
        citas_dia = pd.read_sql(f"SELECT rowid, * FROM citas WHERE fecha='{fecha_ver_str}' AND estado_pago != 'CANCELADO' ORDER BY hora ASC", conn)
        
        if not citas_dia.empty:
            # [NUEVO] CAJA CON SCROLL (HEIGHT=400px)
            # Esto crea el efecto de "ver los primeros 5 y bajar para ver más"
            with st.container(height=400, border=True):
                
                for i, (_, r) in enumerate(citas_dia.iterrows()):
                    rowid = r['rowid']
                    estatus = r.get('estatus_asistencia', 'Programada')
                    
                    # Colores de Estado
                    color_borde = "#D4AF37" # Dorado
                    bg_row = "#ffffff"
                    if estatus == 'Asistió': 
                        color_borde = "#28a745"; bg_row = "#f0fff4"
                    elif estatus == 'No Asistió': 
                        color_borde = "#dc3545"; bg_row = "#fff5f5"

                    # 1. VISUAL (HTML Compacto)
                    st.markdown(f"""
                    <div class="cita-row-compact" style="border-left: 4px solid {color_borde}; background-color: {bg_row};">
                        <div style="display:flex; align-items:center; flex-grow:1;">
                            <div class="cita-time">{r['hora']}</div>
                            <div style="padding-left: 10px;">
                                <div class="cita-name">{r['nombre_paciente']}</div>
                                <div class="cita-desc">{r['tratamiento']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 2. BOTONERA (Debajo de cada fila visual, muy pegadita)
                    # c1: Asistencia, c2: Falta, c3: Espacio, c4: Mover, c5: Cancelar
                    c_btns = st.columns([1, 1, 4, 1, 1])
                    
                    # Solo mostrar botones de asistencia si es HOY o PASADO
                    if es_hoy or fecha_ver_obj <= datetime.now(TZ_MX).date():
                        with c_btns[0]:
                            if st.button("✅", key=f"ok_{rowid}", help="Asistió"):
                                c = conn.cursor(); c.execute("UPDATE citas SET estatus_asistencia='Asistió' WHERE rowid=?", (rowid,)); conn.commit(); st.rerun()
                        with c_btns[1]:
                            if st.button("❌", key=f"no_{rowid}", help="No Asistió"):
                                c = conn.cursor(); nota = f"\n[SISTEMA]: Inasistencia {fecha_ver_str}."; c.execute("UPDATE citas SET estatus_asistencia='No Asistió', notas=ifnull(notas,'') || ? WHERE rowid=?", (nota, rowid)); conn.commit(); st.warning("Falta"); time.sleep(0.5); st.rerun()
                    
                    # Botones de Gestión siempre disponibles
                    with c_btns[3]:
                        if st.button("🔄", key=f"ed_{rowid}", help="Reprogramar"):
                            # Toggle del modo edición
                            st.session_state[f"edit_mode_{rowid}"] = not st.session_state.get(f"edit_mode_{rowid}", False)
                    with c_btns[4]:
                        if st.button("🚫", key=f"del_{rowid}", help="Cancelar Cita"):
                            c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO', estatus_asistencia='Canceló' WHERE rowid=?", (rowid,)); conn.commit(); st.success("Cancelada"); time.sleep(0.5); st.rerun()

                    # 3. PANEL DE REPROGRAMACIÓN (Se despliega solo si das click en 🔄)
                    if st.session_state.get(f"edit_mode_{rowid}", False):
                        with st.container():
                            cc1, cc2, cc3 = st.columns([2, 2, 1])
                            n_f = cc1.date_input("Fecha", datetime.now(TZ_MX), key=f"nf_{rowid}", label_visibility="collapsed")
                            n_h = cc2.selectbox("Hora", generar_slots_tiempo(), key=f"nh_{rowid}", label_visibility="collapsed")
                            if cc3.button("💾", key=f"sv_{rowid}"):
                                c = conn.cursor()
                                # Limpiamos estatus al mover
                                c.execute("UPDATE citas SET fecha=?, hora=?, estatus_asistencia='Programada' WHERE rowid=?", (format_date_latino(n_f), n_h, rowid))
                                conn.commit()
                                del st.session_state[f"edit_mode_{rowid}"] # Limpiar estado visual
                                st.success("Movido")
                                time.sleep(0.5); st.rerun()
                    
                    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True) # Pequeño separador real

        else:
            # Estado vacío elegante
            st.info(f"☕ Agenda libre para el {fecha_ver_str}. Disfruta tu café.")

        st.divider()

        # ==============================================================================
        # ZONA 2: FORMULARIOS Y VISUALIZADOR (MANTENIDO IGUAL)
        # ==============================================================================
        col_cal1, col_cal2 = st.columns([1, 1]) 
        
        with col_cal1:
            st.markdown("### 🛠️ Panel de Gestión")
            
            # [BUSCADOR]
            with st.expander("🔍 Buscar Cita (Global)", expanded=False):
                q_cita = st.text_input("Nombre del paciente:", key="search_global_v471")
                if q_cita:
                    query = f"""SELECT c.rowid, c.fecha, c.hora, c.tratamiento, c.nombre_paciente, c.estatus_asistencia FROM citas c WHERE c.nombre_paciente LIKE '%{formato_nombre_legal(q_cita)}%' ORDER BY c.timestamp DESC"""
                    df = pd.read_sql(query, conn)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            # [AGENDAR CITA NUEVA - CON RESET ID]
            with st.expander("➕ Agendar Cita Nueva", expanded=True):
                tab_reg, tab_new = st.tabs(["Registrado", "Prospecto"])
                
                # --- TAB REGISTRADO ---
                with tab_reg:
                    servicios = pd.read_sql("SELECT * FROM servicios", conn); cats = servicios['categoria'].unique()
                    pacientes_raw = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                    lista_pac = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not pacientes_raw.empty else []
                    
                    p_sel_r = st.selectbox("Paciente*", ["Seleccionar..."] + lista_pac, key=f"p_reg_{reset_id}")
                    cat_sel_r = st.selectbox("Categoría", cats, key=f"cat_reg_{reset_id}")
                    trats_filtrados_r = servicios[servicios['categoria'] == cat_sel_r]['nombre_tratamiento'].unique()
                    trat_sel_r = st.selectbox("Tratamiento*", trats_filtrados_r, key=f"trat_reg_{reset_id}")
                    
                    dur_default_r = 30
                    if trat_sel_r:
                        row_dur = servicios[servicios['nombre_tratamiento'] == trat_sel_r]
                        if not row_dur.empty: dur_default_r = int(row_dur.iloc[0]['duracion'])
                    
                    c_d1, c_d2 = st.columns(2)
                    duracion_cita_r = c_d1.number_input("Minutos", value=dur_default_r, step=30, key=f"dur_reg_{reset_id}")
                    h_sel_r = c_d2.selectbox("Hora Inicio", generar_slots_tiempo(), key=f"hora_reg_{reset_id}")
                    d_sel_r = st.selectbox("Doctor", LISTA_DOCTORES, key=f"doc_reg_{reset_id}")
                    
                    urgencia_r = st.checkbox("🚨 Agendar como Urgencia (Permitir cruce)", key=f"urg_reg_{reset_id}")
                    
                    if st.button("💾 Confirmar Cita (Registrado)", use_container_width=True):
                         if p_sel_r != "Seleccionar...":
                             ocupado = verificar_disponibilidad(fecha_ver_str, h_sel_r, duracion_cita_r)
                             if ocupado and not urgencia_r: 
                                 st.error("⚠️ Horario OCUPADO. Marque 'Urgencia' para empalmar.")
                             else:
                                 id_p = p_sel_r.split(" - ")[0]; nom_p = p_sel_r.split(" - ")[1]
                                 c = conn.cursor()
                                 c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, estado_pago, estatus_asistencia, duracion, notas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                           (int(time.time()), fecha_ver_str, h_sel_r, id_p, nom_p, cat_sel_r, trat_sel_r, d_sel_r, "Pendiente", "Programada", duracion_cita_r, f"Cita: {trat_sel_r}"))
                                 conn.commit()
                                 st.success("Agendado")
                                 st.session_state.form_reset_id += 1 # Limpieza
                                 time.sleep(1); st.rerun()
                         else: st.error("Seleccione un paciente.")

                # --- TAB PROSPECTO ---
                with tab_new:
                    c_n1, c_n2 = st.columns(2)
                    nom_pros = c_n1.text_input("Nombre Completo*", key=f"new_p_nom_{reset_id}")
                    tel_pros = c_n2.text_input("Teléfono (10)*", key=f"new_p_tel_{reset_id}", max_chars=10)
                    
                    servicios_p = pd.read_sql("SELECT * FROM servicios", conn); cats_p = servicios_p['categoria'].unique()
                    cat_sel_p = st.selectbox("Categoría", cats_p, key=f"cat_pros_{reset_id}")
                    trats_filtrados_p = servicios_p[servicios_p['categoria'] == cat_sel_p]['nombre_tratamiento'].unique()
                    trat_sel_p = st.selectbox("Tratamiento*", trats_filtrados_p, key=f"trat_pros_{reset_id}")
                    
                    dur_default_p = 30
                    if trat_sel_p:
                        row_dur_p = servicios_p[servicios_p['nombre_tratamiento'] == trat_sel_p]
                        if not row_dur_p.empty: dur_default_p = int(row_dur_p.iloc[0]['duracion'])
                    
                    c_tp1, c_tp2 = st.columns(2)
                    duracion_cita_p = c_tp1.number_input("Minutos", value=dur_default_p, step=30, key=f"dur_pros_{reset_id}")
                    hora_pros = c_tp2.selectbox("Hora Inicio", generar_slots_tiempo(), key=f"hora_pros_{reset_id}")
                    doc_pros = st.selectbox("Doctor", LISTA_DOCTORES, key=f"doc_pros_{reset_id}")
                    
                    urgencia_p = st.checkbox("🚨 Es Urgencia / Sobrecupo", key=f"urg_pros_{reset_id}")
                    
                    if st.button("💾 Agendar Prospecto", use_container_width=True):
                        if nom_pros and len(tel_pros) == 10:
                             ocupado = verificar_disponibilidad(fecha_ver_str, hora_pros, duracion_cita_p)
                             if ocupado and not urgencia_p: 
                                 st.error("⚠️ Horario OCUPADO. Marque 'Urgencia' para empalmar.")
                             else:
                                 id_temp = f"PROS-{int(time.time())}"
                                 c = conn.cursor()
                                 c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago, estatus_asistencia, notas, duracion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                           (int(time.time()), fecha_ver_str, hora_pros, id_temp, formato_nombre_legal(nom_pros), "Primera Vez", trat_sel_p, doc_pros, "Pendiente", "Programada", f"Tel: {tel_pros}", duracion_cita_p))
                                 conn.commit()
                                 st.success("Prospecto Agendado")
                                 st.session_state.form_reset_id += 1 # Limpieza
                                 time.sleep(1); st.rerun()
                        else: st.error("Datos incompletos.")

        # === COLUMNA DERECHA: VISUALIZADOR ===
        with col_cal2:
            st.markdown(f"#### 🗓️ Visual: {fecha_ver_str}")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            df_dia = df_c[df_c['fecha'] == fecha_ver_str]
            slots = generar_slots_tiempo()
            ocupacion_map = {} 
            if not df_dia.empty:
                for _, r in df_dia.iterrows():
                    if r['estado_pago'] == 'CANCELADO': continue
                    h_inicio = r['hora']
                    try: dur = int(r['duracion']) if r['duracion'] and r['duracion'] > 0 else 30
                    except: dur = 30
                    try:
                        start_dt = datetime.strptime(h_inicio, "%H:%M")
                        for i in range(0, dur, 30):
                            bloque_time = start_dt + timedelta(minutes=i)
                            bloque_str = bloque_time.strftime("%H:%M")
                            if bloque_str not in ocupacion_map:
                                if i == 0: ocupacion_map[bloque_str] = {"tipo": "inicio", "data": r, "dur": dur}
                                else: ocupacion_map[bloque_str] = {"tipo": "bloqueado", "parent": r['nombre_paciente']}
                    except: pass
            
            # HTML LIST JOIN
            html_parts = []
            html_parts.append("<div style='height: 600px; overflow-y: auto; padding: 5px; background-color: white; border: 1px solid #eee; border-radius: 8px;'>")
            
            for slot in slots:
                if slot in ocupacion_map:
                    info = ocupacion_map[slot]
                    if info["tipo"] == "inicio": 
                        r = info["data"]
                        color_border = "#FF5722" if "PROS" in str(r['id_paciente']) else "#002B5B"
                        bg_c = "#e3f2fd" if r['estatus_asistencia'] == 'Asistió' else "#f8f9fa"
                        
                        item = f"<div style='padding:8px; margin-bottom:4px; background-color:{bg_c}; border-left:5px solid {color_border}; border-radius:4px; font-size:0.9em; box-shadow: 0 1px 2px rgba(0,0,0,0.1);'><b>{slot}</b> | {r['nombre_paciente']}<br><span style='color:#666; font-size:0.85em;'>{r['tratamiento']} ({info['dur']}m)</span></div>"
                        html_parts.append(item)
                    else: 
                        item = f"<div style='padding:4px; margin-bottom:4px; background-color:#f1f1f1; color:#aaa; font-size:0.8em; margin-left: 15px; border-left: 2px solid #ddd;'>⬇️ <i>En tratamiento ({info['parent']})</i></div>"
                        html_parts.append(item)
                else: 
                    item = f"<div style='padding:8px; margin-bottom:2px; border-bottom:1px dashed #eee; display:flex; align-items:center;'><span style='font-weight:bold; color:#4CAF50; width:60px;'>{slot}</span><span style='color:#81C784; font-size:0.9em;'>Disponible</span></div>"
                    html_parts.append(item)
            
            html_parts.append("</div>")
            st.markdown("".join(html_parts), unsafe_allow_html=True)
    
    elif menu == "2. Gestión de Pacientes":
        st.title(" 📇 Expediente Clínico Digital"); tab_b, tab_n, tab_e, tab_odo, tab_img = st.tabs(["🔍 BUSCAR", "➕ ALTA", "✏️ EDITAR", "🦷 ODONTOGRAMA", "📸 IMÁGENES"])
        with tab_b:
            # [V46.0] RESTAURACIÓN COMPLETA VISUAL ROYAL CARD
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_busqueda = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist(); seleccion = st.selectbox("Seleccionar:", ["..."] + lista_busqueda)
                if seleccion != "...":
                    id_sel_str = seleccion.split(" - ")[0]; p_data = pacientes_raw[pacientes_raw['id_paciente'] == id_sel_str].iloc[0]; st.session_state.id_paciente_activo = id_sel_str; edad, tipo_pac = calcular_edad_completa(p_data.get('fecha_nacimiento', '')); antecedentes = str(p_data.get('app', '')).strip()
                    if antecedentes and len(antecedentes) > 2 and "NEGADO" not in antecedentes.upper(): st.markdown(f"""<div class='alerta-medica'><span>🚨</span><span>ATENCIÓN CLÍNICA: {antecedentes}</span></div>""", unsafe_allow_html=True)
                    
                    # [V46.0] LAYOUT ASIMÉTRICO 1:2 (FOTO / DATOS)
                    c_card, c_hist = st.columns([1, 2])
                    with c_card:
                        # [V46.0] ROYAL CARD HTML PURO
                        st.markdown(f"""
                        <div class="royal-card">
                            <h3 style="color:#002B5B; margin-top:0;">👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3>
                            <hr style="border: 1px solid #D4AF37;">
                            <p><b>Edad:</b> {edad} Años</p>
                            <p><b>Tel:</b> {format_tel_visual(p_data['telefono'])}</p>
                            <p><b>RFC:</b> {p_data.get('rfc', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        hoy = datetime.now(TZ_MX).date(); df_raw_notas = pd.read_sql(f"SELECT fecha, tratamiento, notas FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn); df_raw_notas['fecha_dt'] = pd.to_datetime(df_raw_notas['fecha'], format="%d/%m/%Y", errors='coerce').dt.date; hist_notas = df_raw_notas[df_raw_notas['fecha_dt'] <= hoy].drop(columns=['fecha_dt'])
                        if st.button("🖨️ Descargar Historia (PDF)"): 
                            # 1. CONSULTA SQL (ORDEN CRONOLÓGICO ASCENDENTE)
                            # [MEJORA] Cambiamos DESC por ASC para leer la historia en orden de sucesos
                            query_historia = f"""
                                SELECT fecha, tratamiento, notas, categoria, estatus_asistencia 
                                FROM citas 
                                WHERE id_paciente='{id_sel_str}' 
                                ORDER BY timestamp ASC
                            """
                            df_raw = pd.read_sql(query_historia, conn)
                            
                            # 2. FILTRADO ESTRICTO DE EJECUCIÓN (MOTOR V47.6)
                            if not df_raw.empty:
                                # A) Normalización
                                df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'], format="%d/%m/%Y", errors='coerce')
                                hoy_date = datetime.now(TZ_MX).date()
                                
                                # B) LISTA NEGRA (Términos Administrativos)
                                palabras_prohibidas = ['ABONO', 'PAGO', 'MENSUALIDAD', 'ANTICIPO', 'DEUDA', 'SALDO', 'COTIZACION', 'PRESUPUESTO']
                                pattern_prohibido = '|'.join(palabras_prohibidas)
                                
                                # --- REGLAS DE BLINDAJE ---
                                # 1. Nada Financiero
                                mask_cat = (df_raw['categoria'] != 'Financiero')
                                # 2. Nada con palabras de dinero
                                mask_txt = (~df_raw['tratamiento'].str.contains(pattern_prohibido, case=False, na=False))
                                # 3. Fechas válidas (Pasado/Presente)
                                mask_time = (df_raw['fecha_dt'].dt.date <= hoy_date)
                                
                                # 4. [CRÍTICO] SOLO TRATAMIENTOS COMPLETADOS
                                # Esto elimina "Programada", "Pendiente" y cualquier cita futura no realizada.
                                # Solo pasa si el doctor presionó el botón verde "Asistió" o "Llegó".
                                mask_status = (df_raw['estatus_asistencia'] == 'Asistió')

                                # Aplicar Filtros
                                df_clean = df_raw[mask_cat & mask_txt & mask_time & mask_status].copy()
                                
                                # C) LIMPIEZA DE TEXTO (Relleno de notas vacías)
                                df_clean['notas'] = df_clean['notas'].fillna("Procedimiento realizado sin incidencias.")
                                df_clean.loc[df_clean['notas'] == "", 'notas'] = "Procedimiento realizado sin incidencias."
                                
                                # Selección Final
                                hist_notas_final = df_clean[['fecha', 'tratamiento', 'notas']]
                            else:
                                hist_notas_final = pd.DataFrame(columns=['fecha', 'tratamiento', 'notas'])

                            # 3. GENERACIÓN DEL PDF
                            try:
                                odo_data = obtener_estado_dientes(id_sel_str)
                                pdf_bytes = crear_pdf_historia(p_data, hist_notas_final, odo_data)
                            except TypeError:
                                pdf_bytes = crear_pdf_historia(p_data, hist_notas_final)
                                
                            clean_name = f"{p_data['id_paciente']}_HISTORIAL_CLINICO.pdf"
                            st.download_button("📥 Bajar PDF Historial", pdf_bytes, clean_name, "application/pdf")
                    
                    with c_hist:
                        st.markdown("#### 📜 Notas Clínicas")
                        if not hist_notas.empty: 
                            df_notes = hist_notas[['fecha', 'tratamiento', 'notas']].copy()
                            df_notes.index = range(1, len(df_notes) + 1); df_notes.index.name = "CVO"; df_notes.columns = ["FECHA", "TRATAMIENTO", "NOTAS"]
                            st.dataframe(df_notes, use_container_width=True, hide_index=False)
                        else: st.info("Sin notas registradas.")

        # [V46.0] ODONTOGRAMA SIN EMOJIS
        with tab_odo:
            if 'id_paciente_activo' in st.session_state and st.session_state.id_paciente_activo:
                p = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{st.session_state.id_paciente_activo}'", conn).iloc[0]
                edad, _ = calcular_edad_completa(p['fecha_nacimiento'])
                st.subheader(f"Odontograma ({edad} años)")
                if edad < 12:
                    st.info("DENTICIÓN INFANTIL / MIXTA")
                    dientes_sup = [55,54,53,52,51,61,62,63,64,65]; dientes_inf = [85,84,83,82,81,71,72,73,74,75]
                else:
                    st.info("DENTICIÓN PERMANENTE (ADULTO)")
                    dientes_sup = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28]; dientes_inf = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38]

                colores = {"Sano": "⚪", "Caries": "🔴", "Resina": "🔵", "Ausente": "⚫", "Corona": "🟡"}
                estados_pac = obtener_estado_dientes(st.session_state.id_paciente_activo)
                
                cols_sup = st.columns(len(dientes_sup))
                for idx, d in enumerate(dientes_sup):
                    est = estados_pac.get(str(d), "Sano")
                    if cols_sup[idx].button(f"{colores[est]}\n{d}", key=f"d_{d}"): actualizar_diente(st.session_state.id_paciente_activo, str(d)); st.rerun()
                st.divider()
                cols_inf = st.columns(len(dientes_inf))
                for idx, d in enumerate(dientes_inf):
                    est = estados_pac.get(str(d), "Sano")
                    if cols_inf[idx].button(f"{colores[est]}\n{d}", key=f"d_{d}"): actualizar_diente(st.session_state.id_paciente_activo, str(d)); st.rerun()
                st.caption("Clic para cambiar: ⚪Sano -> 🔴Caries -> 🔵Resina -> ⚫Ausente -> 🟡Corona")
            else: st.warning("Seleccione un paciente primero.")

        # ... (Resto de tabs Alta/Editar/Imagenes V41 intactos) ...
        with tab_n:
            st.markdown("#### Formulario Alta (NOM-004)"); 
            with st.form("alta_paciente", clear_on_submit=True):
                c1, c2, c3 = st.columns(3); nombre = c1.text_input("Nombre(s)"); paterno = c2.text_input("A. Paterno"); materno = c3.text_input("A. Materno")
                c4, c5, c6 = st.columns(3); nacimiento = c4.date_input("Fecha de Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now(TZ_MX).date(), value=datetime.now(TZ_MX).date()); sexo = c5.selectbox("Sexo", ["Masculino", "Femenino"]); ocupacion = c6.selectbox("Ocupación", LISTA_OCUPACIONES)
                st.markdown("**Datos de Contacto y Residencia**"); ce1, ce2, ce3 = st.columns(3); tel = ce1.text_input("Celular Paciente (10)", max_chars=10); email = ce2.text_input("Email"); estado_civil = ce3.selectbox("Estado Civil", ["Soltero", "Casado", "Divorciado", "Viudo", "Unión Libre"]); domicilio = st.text_input("Domicilio Completo")
                edad_calc = 0; 
                if nacimiento: hoy = datetime.now().date(); edad_calc = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
                if edad_calc < 18: st.info(f"Paciente menor de edad ({edad_calc} años). Tutor obligatorio.")
                st.markdown("**Responsable / Tutor (Obligatorio si es menor)**"); ct1, ct2 = st.columns(2); tutor = ct1.text_input("Nombre Completo Tutor"); parentesco = ct2.selectbox("Parentesco", LISTA_PARENTESCOS)
                st.markdown("**Contacto de Emergencia**"); cem1, cem2 = st.columns(2); contacto_emer_nom = cem1.text_input("Nombre Contacto Emergencia"); contacto_emer_tel = cem2.text_input("Tel Emergencia (10)", max_chars=10)
                motivo_consulta = st.text_area("Motivo de Consulta*"); st.markdown("**Historia Médica**"); ahf = st.text_area("AHF", placeholder="Diabetes..."); app = st.text_area("APP", placeholder="Alergias..."); apnp = st.text_area("APNP", placeholder="Tabaquismo..."); st.markdown("**Exploración y Diagnóstico (Dr)**"); exploracion = st.text_area("Exploración Física"); diagnostico = st.text_area("Diagnóstico Presuntivo")
                rfc_final = ""; regimen = ""; uso_cfdi = ""; cp = ""
                with st.expander("Datos de Facturación (Opcional)", expanded=False): cf1, cf2, cf3 = st.columns([2, 1, 1]); rfc_base = cf1.text_input("RFC (Sin Homoclave)", max_chars=13); homoclave = cf2.text_input("Homoclave", max_chars=3); cp = cf3.text_input("C.P.", max_chars=5); cf4, cf5 = st.columns(2); regimen = cf4.selectbox("Régimen", get_regimenes_fiscales()); uso_cfdi = cf5.selectbox("Uso CFDI", get_usos_cfdi())
                aviso = st.checkbox("Acepto Aviso de Privacidad")
                if st.form_submit_button("💾 GUARDAR EXPEDIENTE"):
                    if not aviso: st.error("Acepte Aviso Privacidad"); st.stop()
                    if not tel.isdigit() or len(tel) != 10: st.error("Teléfono Paciente incorrecto"); st.stop()
                    if contacto_emer_tel and (not contacto_emer_tel.isdigit() or len(contacto_emer_tel) != 10): st.error("Teléfono Emergencia incorrecto"); st.stop()
                    if not nombre or not paterno: st.error("Nombre incompleto"); st.stop()
                    if edad_calc < 18: 
                        if not tutor or not parentesco: st.error("⛔ ERROR: Para menores de 18 años, el Nombre del Tutor y Parentesco son OBLIGATORIOS."); st.stop()
                    if rfc_base: rfc_final = formato_nombre_legal(rfc_base) + formato_nombre_legal(homoclave)
                    else: base_10 = calcular_rfc_10(nombre, paterno, materno, nacimiento); homo_sufijo = formato_nombre_legal(homoclave) if homoclave else "XXX"; rfc_final = base_10 + homo_sufijo
                    nuevo_id = generar_id_unico(nombre, paterno, nacimiento); c = conn.cursor()
                    c.execute("INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, email, rfc, regimen, uso_cfdi, cp, nota_fiscal, sexo, estado, fecha_nacimiento, antecedentes_medicos, ahf, app, apnp, ocupacion, estado_civil, domicilio, tutor, contacto_emergencia, motivo_consulta, exploracion_fisica, diagnostico, parentesco_tutor, telefono_emergencia) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (nuevo_id, get_fecha_mx(), formato_nombre_legal(nombre), formato_nombre_legal(paterno), formato_nombre_legal(materno), tel, limpiar_email(email), rfc_final, regimen, uso_cfdi, cp, "", sexo, "Activo", format_date_latino(nacimiento), "", formato_oracion(ahf), formato_oracion(app), formato_oracion(apnp), formato_titulo(ocupacion), estado_civil, formato_titulo(domicilio), formato_nombre_legal(tutor), formato_nombre_legal(contacto_emer_nom), formato_oracion(motivo_consulta), formato_oracion(exploracion), formato_oracion(diagnostico), parentesco, contacto_emer_tel))
                    conn.commit(); st.success(f"✅ Paciente {nombre} guardado."); time.sleep(1.5); st.rerun()
        with tab_e:
            pacientes_raw = pd.read_sql("SELECT * FROM pacientes", conn)
            if not pacientes_raw.empty:
                lista_edit = pacientes_raw.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist(); sel_edit = st.selectbox("Buscar Paciente:", ["Select..."] + lista_edit)
                if sel_edit != "Select...":
                    id_target = sel_edit.split(" - ")[0]; p = pacientes_raw[pacientes_raw['id_paciente'] == id_target].iloc[0]
                    with st.form("form_editar_full"):
                        st.info("Editando a: " + p['nombre']); ec1, ec2, ec3 = st.columns(3); e_nom = ec1.text_input("Nombre", p['nombre']); e_pat = ec2.text_input("A. Paterno", p['apellido_paterno']); e_mat = ec3.text_input("A. Materno", p['apellido_materno']); ec4, ec5 = st.columns(2); e_tel = ec4.text_input("Teléfono", p['telefono']); e_email = ec5.text_input("Email", p['email']); st.markdown("**Médico & Contacto**"); e_app = st.text_area("APP", p['app'] if p['app'] else ""); e_ahf = st.text_area("AHF", p['ahf'] if p['ahf'] else ""); e_apnp = st.text_area("APNP", p['apnp'] if p['apnp'] else ""); cem1, cem2 = st.columns(2); e_cont_nom = cem1.text_input("Nombre Contacto Emergencia", p.get('contacto_emergencia', '')); e_cont_tel = cem2.text_input("Tel Emergencia", p.get('telefono_emergencia', '')); st.markdown("**Fiscal**"); ec6, ec7, ec8 = st.columns(3); e_rfc = ec6.text_input("RFC Completo", p['rfc']); e_cp = ec7.text_input("C.P.", p['cp']); idx_reg = 0; reg_list = get_regimenes_fiscales()
                        if p['regimen'] in reg_list: idx_reg = reg_list.index(p['regimen'])
                        e_reg = ec8.selectbox("Régimen", reg_list, index=idx_reg)
                        if st.form_submit_button("💾 ACTUALIZAR TODO"): c = conn.cursor(); c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, app=?, ahf=?, apnp=?, rfc=?, cp=?, regimen=?, contacto_emergencia=?, telefono_emergencia=? WHERE id_paciente=?", (formato_nombre_legal(e_nom), formato_nombre_legal(e_pat), formato_nombre_legal(e_mat), formatear_telefono_db(e_tel), limpiar_email(e_email), formato_oracion(e_app), formato_oracion(e_ahf), formato_oracion(e_apnp), formato_nombre_legal(e_rfc), e_cp, e_reg, formato_nombre_legal(e_cont_nom), e_cont_tel, id_target)); conn.commit(); st.success("Datos actualizados."); time.sleep(1.5); st.rerun()

        with tab_img:
            if 'id_paciente_activo' in st.session_state:
                id_p = str(st.session_state.id_paciente_activo)
                uploaded = st.file_uploader("Subir Archivo", type=['png','jpg','jpeg','pdf'])
                if uploaded:
                    path = os.path.join(CARPETA_PACIENTES, id_p)
                    if not os.path.exists(path): os.makedirs(path)
                    with open(os.path.join(path, uploaded.name), "wb") as f: f.write(uploaded.getbuffer())
                    st.success("Guardado"); time.sleep(1); st.rerun()
                
                path = os.path.join(CARPETA_PACIENTES, id_p)
                if os.path.exists(path):
                    for f in os.listdir(path): st.image(os.path.join(path,f), caption=f, width=200)

    elif menu == "5. Recetas":
        # ... (Mantener V44 que funciona) ...
        st.title("📝 Prescripción Clínica")
        pacientes = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
        if not pacientes.empty:
            lista_pacientes = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
            paciente_sel_farm = st.selectbox("Seleccionar Paciente para Receta:", ["Seleccionar..."] + lista_pacientes)
            
            if paciente_sel_farm != "Seleccionar...":
                id_p = paciente_sel_farm.split(" - ")[0]
                st.session_state.id_paciente_activo = id_p 
                p = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{id_p}'", conn).iloc[0]
                edad, _ = calcular_edad_completa(p['fecha_nacimiento'])
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    doc_sel = c1.selectbox("Médico que Prescribe", LISTA_DOCTORES)
                    combo_sel = c2.selectbox("Combo Medicamento (Relleno Rápido)", list(MEDICAMENTOS_DB.keys()))
                    texto_medicamentos = st.text_area("Cuerpo de la Receta (Editable)", value=MEDICAMENTOS_DB[combo_sel], height=150)
                    indicacion_sel = st.selectbox("Hoja de Cuidados (Página 2)", list(INDICACIONES_DB.keys()))
                    texto_indicaciones = INDICACIONES_DB[indicacion_sel] 
                    if st.button("🖨️ Generar Receta + Indicaciones (PDF)"):
                        info_doc = DOCS_INFO[doc_sel]
                        datos_receta = {
                            "doctor_nombre": info_doc['nombre'], "doctor_cedula": info_doc['cedula'], "doctor_uni": info_doc['universidad'], "doctor_esp": info_doc['especialidad'],
                            "paciente_nombre": f"{p['nombre']} {p['apellido_paterno']} {p['apellido_materno']}", "edad": edad, "fecha": get_fecha_mx(),
                            "medicamentos": texto_medicamentos, "indicaciones": texto_indicaciones
                        }
                        pdf_bytes = crear_pdf_receta(datos_receta); st.download_button("Descargar PDF Receta", pdf_bytes, f"RECETA_{p['nombre']}.pdf", "application/pdf")
            else: st.info("Seleccione un paciente para comenzar.")

    elif menu == "4. Tratamientos":
        st.title(" 🩺 Ejecución Clínica & Cobros")
        pacientes = pd.read_sql("SELECT * FROM pacientes", conn); servicios = pd.read_sql("SELECT * FROM servicios", conn)
        
        if not pacientes.empty:
            sel = st.selectbox("Paciente:", pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
            id_p = sel.split(" - ")[0]; nom_p = sel.split(" - ")[1]; st.session_state.id_paciente_activo = id_p
            
            # --- SEMÁFORO FINANCIERO PROFESIONAL ---
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            
            # Calcular deuda real
            deuda_total = pd.read_sql(f"SELECT SUM(saldo_pendiente) FROM citas WHERE id_paciente='{id_p}' AND estado_pago != 'CANCELADO'", conn).iloc[0,0]
            if deuda_total is None: deuda_total = 0.0
            
            # Semáforo
            if deuda_total > 0:
                st.error(f"⚠️ **SALDO PENDIENTE:** El paciente presenta un adeudo acumulado de **${deuda_total:,.2f}**. Se sugiere regularizar pagos.")
            else:
                st.success("🎉 **CUENTA AL CORRIENTE:** El paciente no tiene adeudos pendientes.")
            
            # --- CAJÓN DE OBSERVACIONES ADMINISTRATIVAS (PERSISTENTE) ---
            # Recuperamos la nota actual de la base de datos
            p_actual = pacientes[pacientes['id_paciente'] == id_p].iloc[0]
            nota_actual = p_actual.get('nota_administrativa', '')
            if nota_actual is None: nota_actual = ""
            
            with st.expander("📋 Observaciones Administrativas (Bitácora)", expanded=bool(nota_actual)):
                with st.form("form_nota_admin_finanzas"):
                    obs_admin_persistent = st.text_area("Notas internas sobre el paciente:", 
                                           value=nota_actual, 
                                           height=80,
                                           placeholder="Ej: Paciente VIP, requiere factura siempre, suele llegar tarde...")
                    if st.form_submit_button("💾 Actualizar Observaciones"):
                        c = conn.cursor()
                        c.execute("UPDATE pacientes SET nota_administrativa = ? WHERE id_paciente = ?", (obs_admin_persistent, id_p))
                        conn.commit()
                        st.success("Observaciones actualizadas.")
                        time.sleep(0.5); st.rerun()
            # ------------------------------------------------

            tab_cobro, tab_abono = st.tabs(["🆕 Nuevo Plan / Tratamiento", "💳 Abonar a Deuda"])
            
            with tab_cobro:
                with st.container(border=True):
                    col_up1, col_up2, col_up3 = st.columns(3)
                    if not servicios.empty:
                        cat_sel = col_up1.selectbox("Categoría", servicios['categoria'].unique()); filt = servicios[servicios['categoria'] == cat_sel]
                        trat_sel = col_up2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                        item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]; precio_sug = float(item['precio_lista']); costo_lab = float(item['costo_laboratorio_base'])
                    else: cat_sel = "Manual"; trat_sel = col_up2.text_input("Tratamiento"); precio_sug = 0.0; costo_lab = 0.0
                    doc_name = col_up3.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    with st.form("cobro", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3); precio = c1.number_input("Precio", value=precio_sug, step=50.0); abono = c2.number_input("Abono", step=50.0); saldo = precio - abono; c3.metric("Saldo", f"${saldo:,.2f}")
                        c4, c5, c6 = st.columns([1.5, 1, 1]); metodo = c4.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia", "Garantía", "Pendiente de Pago"]); num_sessions = c5.number_input("Sesiones", min_value=1, value=1); agendar = c6.checkbox("¿Agendar Cita?")
                        
                        if agendar: 
                            c7, c8 = st.columns(2); f_cita = c7.date_input("Fecha Cita", datetime.now(TZ_MX)); h_cita = c8.selectbox("Hora Cita", generar_slots_tiempo())
                        else: f_cita = datetime.now(TZ_MX); h_cita = "00:00"
                        
                        st.markdown("---")
                        # SEPARACIÓN DE NOTAS
                        col_nota1, col_nota2 = st.columns(2)
                        with col_nota1:
                            notas = st.text_area("📝 Nota de Evolución (Clínico - PDF)", height=80, placeholder="Procedimiento realizado...")
                        with col_nota2:
                            obs_admin = st.text_area("👁️ Observación Transacción (Interno)", height=80, placeholder="Ej: Pago parcial autorizado...")

                        if st.form_submit_button("Registrar Cobro/Tratamiento"):
                            if not notas.strip(): st.warning("⚠️ Guardando sin nota clínica.")
                            if metodo == "Garantía": abono = 0; saldo = 0; precio = 0 
                            estatus = "Pagado" if saldo <= 0 else "Pendiente"; c = conn.cursor()
                            
                            nota_final = formato_oracion(notas)
                            obs_final = formato_oracion(obs_admin)
                            
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, observaciones, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                      (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, cat_sel, trat_sel, doc_name, precio_sug, precio, 0, metodo, estatus, nota_final, obs_final, abono, saldo, get_fecha_mx(), costo_lab))
                            
                            if agendar: 
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, estado_pago, categoria, estatus_asistencia, notas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                          (int(time.time())+1, format_date_latino(f_cita), h_cita, id_p, nom_p, "Tratamiento", trat_sel, doc_name, "Pendiente", cat_sel, "Programada", f"Cita agendada. Obs: {obs_final}"))
                            
                            conn.commit(); st.success("Registrado correctamente"); time.sleep(1); st.rerun()

            with tab_abono:
                 with st.container(border=True):
                    deudas = pd.read_sql(f"SELECT rowid, fecha, tratamiento, saldo_pendiente FROM citas WHERE id_paciente='{id_p}' AND saldo_pendiente > 0 AND estado_pago != 'CANCELADO'", conn)
                    if not deudas.empty:
                        lista_deudas = deudas.apply(lambda x: f"ID: {x['rowid']} | {x['fecha']} | {x['tratamiento']} | Resta: ${x['saldo_pendiente']}", axis=1).tolist()
                        deuda_sel = st.selectbox("Seleccionar Cuenta por Cobrar:", lista_deudas)
                        if deuda_sel:
                            id_row_target = int(deuda_sel.split(" | ")[0].replace("ID: ", "")); row_deuda = deudas[deudas['rowid'] == id_row_target].iloc[0]; saldo_actual = row_deuda['saldo_pendiente']
                            st.info(f"Abonando a: **{row_deuda['tratamiento']}** ({row_deuda['fecha']})")
                            col_ab1, col_ab2 = st.columns(2); monto_abono = col_ab1.number_input("Monto a Abonar", min_value=0.0, max_value=float(saldo_actual), step=50.0); metodo_abono = col_ab2.selectbox("Forma de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                            nuevo_saldo = saldo_actual - monto_abono; st.metric("Nuevo Saldo Restante", f"${nuevo_saldo:,.2f}")
                            if st.button("✅ Registrar Abono"):
                                c = conn.cursor(); nuevo_estado = "Pagado" if nuevo_saldo <= 0 else "Pendiente"
                                c.execute("UPDATE citas SET saldo_pendiente = ?, estado_pago = ? WHERE rowid = ?", (nuevo_saldo, nuevo_estado, id_row_target))
                                texto_concepto = f"ABONO A: {row_deuda['tratamiento']}"
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, observaciones, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                          (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, "Financiero", texto_concepto, "Caja", 0, 0, 0, metodo_abono, "Pagado", "", "Abono registrado", monto_abono, 0, get_fecha_mx(), 0))
                                conn.commit(); st.success("Abono registrado correctamente"); time.sleep(1.5); st.rerun()
                    else: st.success("🎉 Este paciente no tiene adeudos pendientes.")

            st.divider()
            with st.container(border=True):
                st.markdown("#### 📊 Historial de Movimientos")
                df_f = pd.read_sql(f"SELECT rowid, fecha, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, metodo_pago FROM citas WHERE id_paciente='{id_p}' AND estado_pago != 'CANCELADO' AND (precio_final > 0 OR monto_pagado > 0) ORDER BY timestamp DESC", conn)
                
                if not df_f.empty:
                    # [CORRECCIÓN CVO V48.2]
                    # 1. Seleccionamos columnas y reseteamos el índice
                    df_show = df_f[['fecha', 'tratamiento', 'precio_final', 'monto_pagado', 'saldo_pendiente', 'metodo_pago']].reset_index(drop=True)
                    
                    # 2. Creamos el índice CVO iniciando en 1
                    df_show.index = np.arange(1, len(df_show) + 1)
                    
                    # 3. Lo convertimos en columna para que Streamlit lo muestre con nombre
                    df_show = df_show.reset_index()
                    df_show.columns = ['CVO', 'FECHA', 'CONCEPTO', 'CARGO ($)', 'ABONO ($)', 'SALDO ($)', 'MÉTODO']
                    
                    # 4. Mostramos ocultando el índice por defecto de pandas (para que solo salga CVO)
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                    
                    # Generación de Recibos (Mantenido)
                    st.caption("🖨️ Generar Recibo de Pago")
                    opciones_recibo = df_f.apply(lambda x: f"{x['fecha']} | {x['tratamiento']} | Abono: ${x['monto_pagado']} ({x['metodo_pago']})", axis=1).tolist(); sel_recibo = st.selectbox("Seleccionar Movimiento:", opciones_recibo)
                    if st.button("Descargar Recibo Seleccionado"):
                        index_sel = opciones_recibo.index(sel_recibo); row_sel = df_f.iloc[index_sel]; p_info = pacientes[pacientes['id_paciente'] == id_p].iloc[0]
                        fecha_corte = row_sel['fecha']
                        items_hoy = df_f[df_f['fecha'] == fecha_corte].to_dict('records')
                        items_deuda = df_f[(df_f['saldo_pendiente'] > 0) & (df_f['fecha'] != fecha_corte)].to_dict('records')
                        total_tratamiento_hoy = sum(item['precio_final'] for item in items_hoy)
                        total_pagado_hoy = sum(item['monto_pagado'] for item in items_hoy)
                        saldo_total_global = df_f['saldo_pendiente'].sum()
                        datos_pdf = { "paciente": f"{p_info['nombre']} {p_info['apellido_paterno']} {p_info['apellido_materno']}", "rfc": p_info.get('rfc', 'XAXX010101000'), "folio": f"RD-{int(time.time())}-{row_sel['rowid']}", "fecha": fecha_corte, "items_hoy": items_hoy, "items_deuda": items_deuda, "total_tratamiento_hoy": total_tratamiento_hoy, "total_pagado_hoy": total_pagado_hoy, "saldo_total_global": saldo_total_global }
                        pdf_bytes = crear_recibo_pago(datos_pdf); clean_name = f"RECIBO_{datos_pdf['folio']}.pdf"; st.download_button("📥 Bajar PDF", pdf_bytes, clean_name, "application/pdf")
                else: st.info("No hay movimientos financieros registrados.")

    elif menu == "3. Consentimientos":
    st.title("✒️ Autorización de Tratamientos")
    df_p = pd.read_sql("SELECT * FROM pacientes", conn)
    
    if not df_p.empty:
        sel = st.selectbox("Paciente:", ["..."] + df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
        
        if sel != "...":
            id_target = sel.split(" - ")[0]
            p_obj = df_p[df_p['id_paciente'] == id_target].iloc[0]
            st.session_state.id_paciente_activo = id_target
            
            tipo_doc = st.selectbox("Documento", ["Consentimiento Informado", "Aviso de Privacidad"])
            tratamiento_legal = ""
            riesgo_legal = ""
            nivel_riesgo = "LOW_RISK"
            t1_name = ""
            t2_name = ""
            img_t1 = None
            img_t2 = None
            
            if "Consentimiento" in tipo_doc:
                hoy_str = get_fecha_mx()
                # -----------------------------------------------------------------------------
                # CORRECCIÓN 1: Desbloqueo financiero.
                # Se eliminó "(precio_final > 0...)" y se cambió por "estatus_asistencia != 'Canceló'"
                # Esto permite firmar citas programadas sin haber cobrado antes.
                # -----------------------------------------------------------------------------
                citas_hoy = pd.read_sql(f"SELECT * FROM citas WHERE id_paciente='{id_target}' AND fecha='{hoy_str}' AND estatus_asistencia != 'Canceló'", conn) # <--- CORRECCIÓN 1
                
                if not citas_hoy.empty:
                    lista_tratamientos = citas_hoy['tratamiento'].unique().tolist()
                    tratamiento_legal = ", ".join(lista_tratamientos)
                    riesgo_legal = ""
                    nivel_riesgo = "LOW_RISK"
                    servicios = pd.read_sql("SELECT * FROM servicios", conn)
                    
                    for trat in lista_tratamientos:
                        riesgo_item = RIESGOS_DB.get(trat, "")
                        if riesgo_item: 
                            riesgo_legal += f"- {trat}: {riesgo_item}\n"
                        
                        if not servicios.empty:
                            row_s = servicios[servicios['nombre_tratamiento'] == trat]
                            if not row_s.empty and row_s.iloc[0]['consent_level'] == 'HIGH_RISK': 
                                nivel_riesgo = 'HIGH_RISK'
                    
                    st.info(f"📋 Procedimientos de hoy: {tratamiento_legal}")
                    if nivel_riesgo == 'HIGH_RISK': 
                        st.error("🔴 ALTO RIESGO DETECTADO: Se requieren testigos.")
                    else: 
                        st.success("🟢 BAJO RIESGO: Solo Doctor y Paciente.")
                else: 
                    st.warning("⚠️ No hay tratamientos programados para HOY.")
                    st.stop()
            
            col_doc_sel = st.columns(2)
            doc_name_sel = col_doc_sel[0].selectbox("Odontólogo Tratante:", LISTA_DOCTORES)
            
            if nivel_riesgo != 'NO_CONSENT':
                # -----------------------------------------------------------------------------
                # CORRECCIÓN 2: Firma a Ciegas (Blind Signing).
                # Mostramos el texto legal y riesgos ANTES de dibujar los recuadros de firma.
                # -----------------------------------------------------------------------------
                st.markdown("---")
                st.warning("⚠️ DECLARACIÓN LEGAL PREVIA A LA FIRMA:") # <--- CORRECCIÓN 2 (INICIO)
                if riesgo_legal:
                    st.info(f"**AL FIRMAR ACEPTO LOS RIESGOS ESPECÍFICOS:**\n\n{riesgo_legal}")
                
                # Mostramos la cláusula legal general (la que está en el PDF) en pantalla pequeña
                st.markdown(f"<div style='font-size:0.85em; color:#555; background-color:#f9f9f9; padding:10px; border-radius:5px;'>{CLAUSULA_CIERRE}</div>", unsafe_allow_html=True)
                st.markdown("---") # <--- CORRECCIÓN 2 (FIN)

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
                            st.error("⛔ ERROR LEGAL: Faltan nombres de testigos.")
                            bloqueo = True
                        if canvas_t1.image_data is None or canvas_t2.image_data is None: 
                            st.error("⛔ ERROR: Faltan firmas de testigos.")
                            bloqueo = True
                    
                    if not bloqueo:
                        img_pac = None
                        img_doc = None
                        
                        if canvas_pac.image_data is not None:
                            if not np.all(canvas_pac.image_data[:,:,3] == 0): 
                                img = Image.fromarray(canvas_pac.image_data.astype('uint8'), 'RGBA')
                                buf = io.BytesIO()
                                img.save(buf, format="PNG")
                                img_pac = base64.b64encode(buf.getvalue()).decode()
                        
                        if "Aviso" not in tipo_doc:
                            if canvas_doc.image_data is not None:
                                if not np.all(canvas_doc.image_data[:,:,3] == 0): 
                                    img = Image.fromarray(canvas_doc.image_data.astype('uint8'), 'RGBA')
                                    buf = io.BytesIO()
                                    img.save(buf, format="PNG")
                                    img_doc = base64.b64encode(buf.getvalue()).decode()
                            
                            if nivel_riesgo == 'HIGH_RISK':
                                if canvas_t1.image_data is not None:
                                    if not np.all(canvas_t1.image_data[:,:,3] == 0): 
                                        img = Image.fromarray(canvas_t1.image_data.astype('uint8'), 'RGBA')
                                        buf = io.BytesIO()
                                        img.save(buf, format="PNG")
                                        img_t1 = base64.b64encode(buf.getvalue()).decode()
                                if canvas_t2.image_data is not None:
                                    if not np.all(canvas_t2.image_data[:,:,3] == 0): 
                                        img = Image.fromarray(canvas_t2.image_data.astype('uint8'), 'RGBA')
                                        buf = io.BytesIO()
                                        img.save(buf, format="PNG")
                                        img_t2 = base64.b64encode(buf.getvalue()).decode()
                        
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

    elif menu == "6. Control Asistencia":
        st.title("🆔 Asistencia")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Entrada Dr. Emmanuel"): 
                ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(m) 
                else: st.warning(m)
        with col_b:
            if st.button("Salida Dr. Emmanuel"): 
                ok, m = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(m)
                else: st.warning(m)
    
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Administracion": 
        st.title("Admin")
        st.button("Salir", on_click=lambda: st.session_state.update(perfil=None))
