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
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas

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
    """Actualiza la DB con nuevos campos clínicos si no existen"""
    conn = get_db_connection()
    c = conn.cursor()
    # Campos Historia Clínica NOM-004
    try: c.execute("ALTER TABLE pacientes ADD COLUMN antecedentes_medicos TEXT")
    except: pass
    try: c.execute("ALTER TABLE pacientes ADD COLUMN ahf TEXT")
    except: pass
    try: c.execute("ALTER TABLE pacientes ADD COLUMN app TEXT")
    except: pass
    try: c.execute("ALTER TABLE pacientes ADD COLUMN apnp TEXT")
    except: pass
    
    # Campos Citas
    try: c.execute("ALTER TABLE citas ADD COLUMN costo_laboratorio REAL")
    except: pass
    try: c.execute("ALTER TABLE citas ADD COLUMN categoria TEXT")
    except: pass
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT, fecha_registro TEXT, nombre TEXT, apellido_paterno TEXT, 
        apellido_materno TEXT, telefono TEXT, email TEXT, rfc TEXT, regimen TEXT, 
        uso_cfdi TEXT, cp TEXT, nota_fiscal TEXT, sexo TEXT, estado TEXT, fecha_nacimiento TEXT,
        antecedentes_medicos TEXT, ahf TEXT, app TEXT, apnp TEXT
    )''')
    
    # NOTA: Esta tabla tiene 24 columnas. Los INSERT deben coincidir.
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        timestamp INTEGER, fecha TEXT, hora TEXT, id_paciente TEXT, nombre_paciente TEXT, 
        tipo TEXT, tratamiento TEXT, diente TEXT, doctor_atendio TEXT, precio_lista REAL, 
        precio_final REAL, porcentaje REAL, tiene_factura TEXT, iva REAL, subtotal REAL, 
        metodo_pago TEXT, estado_pago TEXT, requiere_factura TEXT, notas TEXT, 
        monto_pagado REAL, saldo_pendiente REAL, fecha_pago TEXT, costo_laboratorio REAL, categoria TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (
        id_evento INTEGER PRIMARY KEY AUTOINCREMENT, fecha_evento TEXT, usuario TEXT, accion TEXT, detalle TEXT
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
migrar_tablas()
seed_data()

# ==========================================
# 3. HELPERS Y SANITIZACIÓN
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%d/%m/%Y")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")
def format_date_latino(date_obj): return date_obj.strftime("%d/%m/%Y")

def sanitizar(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    reemplazos = {'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ü': 'U', 'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U'}
    for old, new in reemplazos.items(): texto = texto.replace(old, new)
    texto = " ".join(texto.split())
    return texto

def limpiar_email(texto): return texto.lower().strip() if texto else ""

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO auditoria (fecha_evento, usuario, accion, detalle) VALUES (?,?,?,?)",
                  (datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, sanitizar(detalle)))
        conn.commit(); conn.close()
    except: pass

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
        nombre = sanitizar(nombre); paterno = sanitizar(paterno)
        part1 = paterno[:3] if len(paterno) >=3 else paterno + "X"
        part2 = nombre[0]; part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except: return f"P-{int(time.time())}"

def formatear_telefono_db(numero): return re.sub(r'\D', '', str(numero))

def generar_slots_tiempo():
    slots = []; hora_actual = datetime.strptime("08:00", "%H:%M"); hora_fin = datetime.strptime("20:00", "%H:%M")
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M")); hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales(): return ["605 - Sueldos y Salarios", "612 - PFAEP (Actividad Empresarial)", "626 - RESICO", "616 - Sin obligaciones fiscales", "601 - General de Ley Personas Morales"]
def get_usos_cfdi(): return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]

# --- FUNCIÓN NUEVA: Verificar Disponibilidad (Unidad Única) ---
def verificar_disponibilidad(fecha_str, hora_str):
    """Devuelve True si el horario está ocupado por una cita activa"""
    conn = get_db_connection()
    c = conn.cursor()
    # Contamos citas en esa fecha/hora que NO estén canceladas
    c.execute("SELECT count(*) FROM citas WHERE fecha=? AND hora=? AND estado_pago != 'CANCELADO'", (fecha_str, hora_str))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

# ==========================================
# 4. GENERADOR DE PDF LEGALES (Clase Auxiliar)
# ==========================================
class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__() # FIX: Inicializar clase padre para evitar AttributeError
        
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 43, 91) # Azul Royal
        self.cell(0, 10, 'ROYAL DENTAL - Documento Legal', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, body)
        self.ln()

def crear_pdf_consentimiento(paciente, doctor, tratamiento, firma_img_data):
    pdf = PDFGenerator()
    pdf.add_page()
    
    texto_legal = f"""
    FECHA: {datetime.now().strftime("%d/%m/%Y")}
    PACIENTE: {paciente}
    DOCTOR TRATANTE: {doctor}
    PROCEDIMIENTO: {tratamiento}

    CONSENTIMIENTO INFORMADO PARA TRATAMIENTO ODONTOLÓGICO

    1. Declaro que he sido informado(a) detalladamente sobre el diagnóstico y el plan de tratamiento necesario para mi salud bucal.
    2. Se me han explicado los riesgos, complicaciones posibles y beneficios del procedimiento mencionado.
    3. Entiendo que la odontología no es una ciencia exacta y que no se pueden garantizar resultados específicos, aunque el personal médico pondrá todos los medios a su alcance.
    4. Autorizo la administración de anestesia local y los procedimientos auxiliares necesarios.
    5. Me comprometo a seguir las instrucciones post-operatorias para asegurar el éxito del tratamiento.
    
    Declaro que he leído y comprendido este documento, y otorgo mi consentimiento voluntariamente.
    """
    
    texto_safe = texto_legal.encode('latin-1', 'replace').decode('latin-1')
    pdf.chapter_body(texto_safe)
    
    pdf.ln(10)
    pdf.cell(0, 10, "FIRMA DEL PACIENTE:", 0, 1)
    
    if firma_img_data:
        import io
        from PIL import Image
        img_data = re.sub('^data:image/.+;base64,', '', firma_img_data)
        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
        temp_filename = f"temp_sig_{int(time.time())}.png"
        img.save(temp_filename)
        pdf.image(temp_filename, x=10, w=50)
        
    return pdf.output(dest='S').encode('latin-1')

def crear_pdf_historia(paciente_data, historial_citas):
    pdf = PDFGenerator()
    pdf.add_page()
    
    p = paciente_data
    # FIX: Manejo seguro de 'sexo' para evitar KeyError en pacientes viejos
    sexo_safe = p['sexo'] if 'sexo' in p.keys() and p['sexo'] else "N/A"
    
    texto_gral = f"""
    EXPEDIENTE CLÍNICO - NOM-004-SSA3-2012
    
    DATOS GENERALES
    Nombre: {p['nombre']} {p['apellido_paterno']} {p['apellido_materno']}
    Edad/Nac: {p['fecha_nacimiento']} ({calcular_edad_completa(p['fecha_nacimiento'])[0]} años)
    Sexo: {sexo_safe}
    Teléfono: {p['telefono']}
    
    HISTORIA MÉDICA (ANAMNESIS)
    > Antecedentes Heredo-Familiares (AHF):
    {p.get('ahf', 'Negados')}
    
    > Antecedentes Personales Patológicos (APP - Alergias/Enf):
    {p.get('app', 'Negados')}
    
    > Antecedentes No Patológicos (APNP - Hábitos):
    {p.get('apnp', 'Negados')}
    
    NOTA DE EVOLUCIÓN (Últimas citas):
    """
    
    texto_safe = texto_gral.encode('latin-1', 'replace').decode('latin-1')
    pdf.chapter_body(texto_safe)
    
    if not historial_citas.empty:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(30, 7, 'FECHA', 1)
        pdf.cell(60, 7, 'TRATAMIENTO', 1)
        pdf.cell(90, 7, 'NOTAS / EVOLUCION', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        for _, row in historial_citas.iterrows():
            f = str(row['fecha']).encode('latin-1', 'replace').decode('latin-1')
            t = str(row['tratamiento']).encode('latin-1', 'replace').decode('latin-1')
            n = str(row['notas']).encode('latin-1', 'replace').decode('latin-1')
            
            pdf.cell(30, 6, f, 1)
            pdf.cell(60, 6, t[:35], 1)
            pdf.cell(90, 6, n[:50], 1)
            pdf.ln()
            
    return pdf.output(dest='S').encode('latin-1')

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
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Documentos & Firmas", "5. Control Asistencia"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    conn = get_db_connection()

    # --- MÓDULO 1: AGENDA ---
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        with st.expander("🔍 BUSCADOR DE CITAS", expanded=False):
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
                        
                        # CHECKBOX URGENCIA
                        urgencia = st.checkbox("🚨 Es Urgencia (Sobrecupo)", help="Marca esto para agendar aunque el horario esté ocupado.")
                        
                        if st.form_submit_button("Agendar"):
                            # VALIDAR DISPONIBILIDAD
                            ocupado = verificar_disponibilidad(fecha_ver_str, h_sel)
                            if ocupado and not urgencia:
                                st.error(f"⚠️ El horario {h_sel} ya está ocupado. Marca 'Urgencia' si deseas encimar.")
                            elif p_sel != "Seleccionar...":
                                id_p = p_sel.split(" - ")[0]; nom_p = p_sel.split(" - ")[1]
                                c = conn.cursor()
                                # FIX: Insert ajustado a 24 columnas exactas
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria, diente) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, h_sel, id_p, nom_p, "General", sanitizar(m_sel), d_sel, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General", ""))
                                conn.commit()
                                st.success(f"Agendado"); time.sleep(1); st.rerun()
                            else: st.error("Seleccione paciente")

                with tab_new:
                    with st.form("cita_prospecto", clear_on_submit=True):
                        nombre_pros = st.text_input("Nombre"); tel_pros = st.text_input("Tel (10)", max_chars=10)
                        hora_pros = st.selectbox("Hora", generar_slots_tiempo()); motivo_pros = st.text_input("Motivo", "Revisión 1ra Vez")
                        doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                        urgencia_p = st.checkbox("🚨 Urgencia (Sobrecupo)")
                        
                        if st.form_submit_button("Agendar Prospecto"):
                            ocupado_p = verificar_disponibilidad(fecha_ver_str, hora_pros)
                            if ocupado_p and not urgencia_p:
                                st.error(f"⚠️ El horario {hora_pros} ya está ocupado.")
                            elif nombre_pros and len(tel_pros) == 10:
                                id_temp = f"PROSPECTO-{int(time.time())}"; nom_final = sanitizar(nombre_pros)
                                c = conn.cursor()
                                # FIX: Insert ajustado a 24 columnas exactas
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria, diente) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_ver_str, hora_pros, id_temp, nom_final, "Primera Vez", sanitizar(motivo_pros), doc_pros, 0, 0, 0, "Pendiente", f"Tel: {tel_pros}", 0, 0, "No", 0, 0, "", "No", "", 0, "Primera Vez", ""))
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
                            if st.button("🗓️ Mover y Activar"):
                                c = conn.cursor()
                                c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", (format_date_latino(new_date_res), new_h_res, fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.success(f"Reagendada"); time.sleep(1); st.rerun()
                        with c_cancel:
                             st.write(""); st.write("") 
                             if st.button("❌ Cancelar", type="secondary"):
                                c = conn.cursor()
                                c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
                                conn.commit(); st.warning("Cita cancelada."); time.sleep(1); st.rerun()
                        with c_delete:
                             st.write(""); st.write("") 
                             if st.button("🗑️ Eliminar Def.", type="primary"):
                                c = conn.cursor()
                                c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_ver_str, hora_target, nom_target))
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
                            color = "#FF5722" if "PROSPECTO" in str(r['id_paciente']) else "#002B5B"
                            st.markdown(f"""<div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;"><b>{slot} | {r['nombre_paciente']}</b><br><span style="color:#666; font-size:0.9em;">{r['tratamiento']} - {r['doctor_atendio']}</span></div>""", unsafe_allow_html=True)

    # --- MÓDULO 2: PACIENTES ---
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente Clínico Completo")
        tab_b, tab_n, tab_e = st.tabs(["🔍 BUSCAR/IMPRIMIR", "➕ NUEVO (ALTA)", "✏️ EDITAR COMPLETO"])
        
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
                    
                    antecedentes = p_data.get('app', '')
                    if antecedentes: st.markdown(f"<div class='alerta-medica'>⚠️ ALERTA: {antecedentes}</div><br>", unsafe_allow_html=True)
                    
                    c_info, c_hist = st.columns([1, 2])
                    with c_info:
                        st.markdown(f"""<div class="royal-card">
                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3>
                            <b>Edad:</b> {edad} Años<br><b>Tel:</b> {format_tel_visual(p_data['telefono'])}<br>
                            <b>RFC:</b> {p_data.get('rfc', 'N/A')}
                        </div>""", unsafe_allow_html=True)
                        
                        hist_notas = pd.read_sql(f"SELECT fecha, tratamiento, doctor_atendio, notas FROM citas WHERE id_paciente='{id_sel_str}' ORDER BY timestamp DESC", conn)
                        if st.button("🖨️ Descargar Historia Clínica (PDF)"):
                            # FIX: Llamada segura a PDF para evitar error de 'sexo'
                            pdf_bytes = crear_pdf_historia(p_data, hist_notas)
                            st.download_button(label="📥 Bajar PDF", data=pdf_bytes, file_name=f"Historia_{p_data['nombre']}.pdf", mime="application/pdf")

                    with c_hist:
                        st.markdown("#### 📜 Notas de Evolución")
                        st.dataframe(hist_notas[['fecha', 'tratamiento', 'notas']], use_container_width=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta (NOM-004)")
            with st.form("alta_paciente", clear_on_submit=True):
                st.subheader("1. Datos Generales")
                c1, c2, c3 = st.columns(3)
                nombre = c1.text_input("Nombre(s)"); paterno = c2.text_input("Apellido Paterno"); materno = c3.text_input("Apellido Materno")
                c4, c5, c6 = st.columns(3)
                nacimiento = c4.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1)); tel = c5.text_input("Teléfono (10 dígitos)", max_chars=10); email = c6.text_input("Email")
                c7, c8 = st.columns(2)
                sexo = c7.selectbox("Sexo", ["Mujer", "Hombre"]); rfc = c8.text_input("RFC (Opcional)")
                
                st.subheader("2. Historia Médica (Anamnesis)")
                ahf = st.text_area("AHF (Heredo-Familiares)", placeholder="Diabetes, Hipertensión en padres/abuelos...")
                app = st.text_area("APP (Personales Patológicos - Alergias/Cirugías)", placeholder="Alergias a medicamentos, cirugías previas, enfermedades crónicas...")
                apnp = st.text_area("APNP (No Patológicos)", placeholder="Tabaquismo, Alcoholismo, Higiene bucal...")
                
                st.subheader("3. Fiscal")
                c9, c10, c11 = st.columns(3)
                regimen = c9.selectbox("Régimen Fiscal", get_regimenes_fiscales()); uso_cfdi = c10.selectbox("Uso CFDI", get_usos_cfdi()); cp = c11.text_input("C.P.", max_chars=5)
                
                aviso = st.checkbox("El paciente ha leído y aceptado el Aviso de Privacidad.")
                
                if st.form_submit_button("💾 GUARDAR EXPEDIENTE"):
                    if not aviso: st.error("Debe aceptar el Aviso de Privacidad."); st.stop()
                    if not tel.isdigit() or len(tel) != 10: st.error("❌ Teléfono incorrecto."); st.stop()
                    if not nombre or not paterno: st.error("❌ Nombre incompleto."); st.stop()
                    
                    nuevo_id = generar_id_unico(sanitizar(nombre), sanitizar(paterno), nacimiento)
                    c = conn.cursor()
                    c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (nuevo_id, get_fecha_mx(), sanitizar(nombre), sanitizar(paterno), sanitizar(materno), tel, limpiar_email(email), sanitizar(rfc), regimen, uso_cfdi, cp, "", sexo, "Activo", format_date_latino(nacimiento), "", sanitizar(ahf), sanitizar(app), sanitizar(apnp)))
                    conn.commit(); st.success(f"✅ Paciente {nombre} guardado."); time.sleep(1.5); st.rerun()

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
                        st.info("Editando datos de: " + p['nombre'])
                        ec1, ec2, ec3 = st.columns(3)
                        e_nom = ec1.text_input("Nombre", p['nombre']); e_pat = ec2.text_input("A. Paterno", p['apellido_paterno']); e_mat = ec3.text_input("A. Materno", p['apellido_materno'])
                        ec4, ec5 = st.columns(2)
                        e_tel = ec4.text_input("Teléfono", p['telefono']); e_email = ec5.text_input("Email", p['email'])
                        
                        st.markdown("**Actualizar Historia Médica**")
                        e_app = st.text_area("APP (Alergias/Enf)", value=p['app'] if p['app'] else "")
                        e_ahf = st.text_area("AHF (Hereditarios)", value=p['ahf'] if p['ahf'] else "")
                        
                        if st.form_submit_button("💾 ACTUALIZAR TODO"):
                            c = conn.cursor()
                            c.execute("UPDATE pacientes SET nombre=?, apellido_paterno=?, apellido_materno=?, telefono=?, email=?, app=?, ahf=? WHERE id_paciente=?", 
                                      (sanitizar(e_nom), sanitizar(e_pat), sanitizar(e_mat), formatear_telefono_db(e_tel), e_email, sanitizar(e_app), sanitizar(e_ahf), id_target))
                            conn.commit(); st.success("Datos actualizados."); time.sleep(1.5); st.rerun()

    # --- MÓDULO 3: PLANES DE TRATAMIENTO ---
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes y Finanzas")
        try:
            pacientes = pd.read_sql("SELECT * FROM pacientes", conn)
            servicios = pd.read_sql("SELECT * FROM servicios", conn)
            df_finanzas = pd.read_sql("SELECT * FROM citas", conn)
        except Exception as e: st.error(f"Error DB: {e}"); st.stop()
            
        if pacientes.empty: st.warning("Registra pacientes primero.")
        else:
            lista_pac = pacientes.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist()
            seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
            if seleccion_pac != "Buscar...":
                id_p = seleccion_pac.split(" - ")[0]; nom_p = seleccion_pac.split(" - ")[1]
                
                st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
                if not df_finanzas.empty:
                    historial = df_finanzas[df_finanzas['id_paciente'] == id_p]
                    if not historial.empty:
                        hist_valid = historial[historial['estado_pago'] != 'CANCELADO']
                        deuda_total = pd.to_numeric(hist_valid['saldo_pendiente'], errors='coerce').fillna(0).sum()
                        col_sem1, col_sem2 = st.columns(2)
                        col_sem1.metric("Deuda Total", f"${deuda_total:,.2f}")
                        if deuda_total > 0: col_sem2.error(f"🚨 SALDO PENDIENTE: ${deuda_total:,.2f}")
                        else: col_sem2.success("✅ SIN ADEUDOS")
                        with st.expander("📜 Ver Historial Completo", expanded=True):
                            st.dataframe(historial[['fecha', 'tratamiento', 'doctor_atendio', 'precio_final', 'monto_pagado', 'saldo_pendiente', 'estado_pago', 'notas']])
                
                st.markdown("---")
                st.subheader("Nuevo Plan / Procedimiento")
                c1, c2, c3 = st.columns(3)
                if not servicios.empty:
                    cats = servicios['categoria'].unique(); cat_sel = c1.selectbox("1. Categoría", cats)
                    filt = servicios[servicios['categoria'] == cat_sel]; trat_sel = c2.selectbox("2. Tratamiento", filt['nombre_tratamiento'].unique())
                    item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]; precio_lista_sug = float(item['precio_lista']); costo_lab_sug = float(item['costo_laboratorio_base'])
                else:
                    cat_sel = "Manual"; trat_sel = c2.text_input("Tratamiento"); precio_lista_sug = 0.0; costo_lab_sug = 0.0
                c3.metric("Precio Lista", f"${precio_lista_sug:,.2f}")
                
                with st.form("form_plan_final"):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    precio_final = col_f1.number_input("Precio Final", value=precio_lista_sug, min_value=0.0, format="%.2f")
                    abono = col_f2.number_input("Abono Inicial", min_value=0.0, format="%.2f")
                    saldo_real = precio_final - abono
                    col_f3.metric("Saldo Pendiente", f"${saldo_real:,.2f}")
                    
                    st.markdown("---")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    doctor = col_d1.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"]); diente = col_d2.number_input("Diente (ISO)", min_value=0, max_value=85, step=1)
                    metodo = col_d3.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia", "Pendiente de Pago"])
                    notas_evolucion = st.text_area("Notas del Procedimiento (Evolución)", placeholder="Detalles clínicos...")
                    agendar = st.checkbox("¿Agendar Cita para Realizar el Tratamiento?"); c_date1, c_date2 = st.columns(2)
                    f_cita_plan = c_date1.date_input("Fecha Cita Tratamiento", datetime.now(TZ_MX)); h_cita_plan = c_date2.selectbox("Hora Cita", generar_slots_tiempo())

                    if st.form_submit_button("💾 REGISTRAR"):
                        if metodo == "Pendiente de Pago" and abono > 0: st.warning("Advertencia: Abono en 'Pendiente de Pago'.")
                        nota_final = f"{sanitizar(notas_evolucion)} | Desc: ${precio_lista_sug-precio_final}" if precio_final < precio_lista_sug else sanitizar(notas_evolucion)
                        estatus = "Pagado" if saldo_real <= 0 else "Pendiente"
                        
                        # Validar disponibilidad si se quiere agendar
                        ocupado_plan = verificar_disponibilidad(format_date_latino(f_cita_plan), h_cita_plan) if agendar else False
                        
                        if agendar and ocupado_plan:
                            st.error(f"⚠️ El horario {h_cita_plan} está ocupado. No se pudo agendar la cita, pero ¿deseas registrar solo el cobro?")
                        else:
                            c = conn.cursor()
                            # FIX: Insert ajustado a 24 columnas exactas
                            c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, diente, doctor_atendio, precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio, tiene_factura, iva, subtotal, requiere_factura, categoria) 
                                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                      (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, cat_sel, trat_sel, str(diente), doctor, precio_lista_sug, precio_final, 0, metodo, estatus, nota_final, abono, saldo_real, get_fecha_mx(), costo_lab_sug, "No", 0, 0, "No", cat_sel))
                            
                            if agendar:
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, diente, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria) 
                                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time())+1, format_date_latino(f_cita_plan), h_cita_plan, id_p, nom_p, "Tratamiento", f"{trat_sel}", str(diente), doctor, 0, 0, 0, "Pendiente", "Cita de Tratamiento", 0, 0, "No", 0, 0, "", "No", "", 0, cat_sel))
                            conn.commit(); st.success(f"✅ Registrado."); time.sleep(2); st.rerun()

    # --- MÓDULO 4: DOCUMENTOS Y FIRMAS ---
    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Legal"); df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", df_p['nombre'].tolist())
            canvas = st_canvas(stroke_width=2, height=150, key="firmas")
            if st.button("Generar PDF"):
                if canvas.image_data is not None:
                    import numpy as np; from PIL import Image; import io
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG")
                    img_str = base64.b64encode(buf.getvalue()).decode()
                    pdf_data = crear_pdf_consentimiento(sel, "Dr. Emmanuel", "General", img_str)
                    st.download_button("Bajar PDF", pdf_data, "Consentimiento.pdf", "application/pdf")

    # --- MÓDULO 5: ASISTENCIA ---
    elif menu == "5. Control Asistencia":
        st.title("⏱️ Checador")
        if st.button("Entrada Dr."): 
            ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada"); 
            if ok: st.success(m) 
            else: st.warning(m)
        if st.button("Salida Dr."): 
            ok, m = registrar_movimiento("Dr. Emmanuel", "Salida"); 
            if ok: st.success(m)
            else: st.warning(m)
    conn.close()

if __name__ == "__main__":
    if st.session_state.perfil is None: pantalla_login()
    elif st.session_state.perfil == "Consultorio": vista_consultorio()
    elif st.session_state.perfil == "Administracion": st.title("Admin"); st.button("Salir", on_click=lambda: st.session_state.update(perfil=None))
