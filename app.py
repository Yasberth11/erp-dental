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
    conn = get_db_connection()
    c = conn.cursor()
    # Asegurar columnas NOM-004
    for col in ['antecedentes_medicos', 'ahf', 'app', 'apnp']:
        try: c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT")
        except: pass
    # Asegurar columnas Citas
    for col in ['costo_laboratorio', 'categoria']:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} REAL" if col == 'costo_laboratorio' else f"ALTER TABLE citas ADD COLUMN {col} TEXT")
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

# --- VALIDACIÓN DE DISPONIBILIDAD (NUEVO) ---
def verificar_disponibilidad(fecha_str, hora_str):
    """Retorna True si el horario está ocupado, False si está libre"""
    conn = get_db_connection()
    c = conn.cursor()
    # Buscamos citas que NO estén canceladas en ese horario
    c.execute("SELECT count(*) FROM citas WHERE fecha=? AND hora=? AND estado_pago != 'CANCELADO'", (fecha_str, hora_str))
    ocupado = c.fetchone()[0] > 0
    conn.close()
    return ocupado

# ==========================================
# 4. GENERADOR DE PDF LEGALES
# ==========================================
class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__() # Corrección AttributeError
        
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 43, 91)
        self.cell(0, 10, 'ROYAL DENTAL - Documento Legal', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
    def chapter_body(self, body):
        self.set_font('Arial', '', 10); self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, body); self.ln()

def crear_pdf_consentimiento(paciente, doctor, tratamiento, firma_img_data):
    pdf = PDFGenerator(); pdf.add_page()
    texto_legal = f"""
    FECHA: {datetime.now().strftime("%d/%m/%Y")} | PACIENTE: {paciente} | DOCTOR: {doctor}
    PROCEDIMIENTO: {tratamiento}

    CONSENTIMIENTO INFORMADO:
    1. Declaro que he sido informado(a) sobre el diagnóstico y plan de tratamiento.
    2. Se me han explicado los riesgos y beneficios.
    3. Autorizo la anestesia y procedimientos necesarios.
    4. Me comprometo a seguir las instrucciones post-operatorias.
    """
    pdf.chapter_body(texto_legal.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(10); pdf.cell(0, 10, "FIRMA DEL PACIENTE:", 0, 1)
    if firma_img_data:
        import io; from PIL import Image
        img_data = re.sub('^data:image/.+;base64,', '', firma_img_data)
        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
        temp_filename = f"temp_sig_{int(time.time())}.png"
        img.save(temp_filename); pdf.image(temp_filename, x=10, w=50)
    return pdf.output(dest='S').encode('latin-1')

def crear_pdf_historia(paciente_data, historial_citas):
    pdf = PDFGenerator(); pdf.add_page()
    p = paciente_data
    # Corrección KeyError: Usamos .get() para evitar error en datos viejos
    sexo_safe = p['sexo'] if 'sexo' in p.keys() and p['sexo'] else "N/A"
    
    texto_gral = f"""
    EXPEDIENTE CLÍNICO
    Nombre: {p['nombre']} {p['apellido_paterno']}
    Edad: {calcular_edad_completa(p['fecha_nacimiento'])[0]} | Sexo: {sexo_safe}
    Tel: {p['telefono']}
    
    HISTORIA MÉDICA:
    AHF: {p.get('ahf', 'N/A')}
    APP: {p.get('app', 'N/A')}
    APNP: {p.get('apnp', 'N/A')}
    """
    pdf.chapter_body(texto_gral.encode('latin-1', 'replace').decode('latin-1'))
    if not historial_citas.empty:
        pdf.set_font('Arial', 'B', 9); pdf.cell(30, 7, 'FECHA', 1); pdf.cell(60, 7, 'TRATAMIENTO', 1); pdf.cell(90, 7, 'NOTAS', 1); pdf.ln()
        pdf.set_font('Arial', '', 8)
        for _, row in historial_citas.iterrows():
            f = str(row['fecha']); t = str(row['tratamiento']); n = str(row['notas'])
            pdf.cell(30, 6, f, 1); pdf.cell(60, 6, t[:35], 1); pdf.cell(90, 6, n[:50], 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. LOGIN Y VISTAS
# ==========================================
if 'perfil' not in st.session_state: st.session_state.perfil = None

def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""<div style="background-color: #002B5B; padding: 30px; border-radius: 15px; text-align: center;"><h2 style="color: #D4AF37 !important;">ROYAL DENTAL</h2></div><br>""", unsafe_allow_html=True)
        tipo = st.selectbox("Perfil", ["Seleccionar...", "🏥 CONSULTORIO", "💼 ADMINISTRACIÓN"])
        pwd = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            if tipo == "🏥 CONSULTORIO" and pwd == "ROYALCLINIC": st.session_state.perfil = "Consultorio"; st.rerun()
            elif tipo == "💼 ADMINISTRACIÓN" and pwd == "ROYALADMIN": st.session_state.perfil = "Administracion"; st.rerun()
            else: st.error("Acceso Denegado")

def vista_consultorio():
    st.sidebar.markdown("### 🏥 Royal Dental")
    st.sidebar.caption(f"Fecha: {get_fecha_mx()}")
    menu = st.sidebar.radio("Menú", ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Documentos & Firmas", "5. Control Asistencia"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.perfil = None; st.rerun()
    conn = get_db_connection()

    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda")
        with st.expander("🔍 BUSCAR CITA"):
            q = st.text_input("Nombre paciente:"); 
            if q: st.dataframe(pd.read_sql(f"SELECT fecha, hora, nombre_paciente, estado_pago FROM citas WHERE nombre_paciente LIKE '%{sanitizar(q)}%' ORDER BY timestamp DESC", conn))

        col_cal1, col_cal2 = st.columns([1, 2.5])
        with col_cal1:
            st.markdown("### 📆 Gestión")
            fecha_ver = st.date_input("Fecha", datetime.now(TZ_MX)); fecha_str = format_date_latino(fecha_ver)
            
            with st.expander("➕ Agendar Cita", expanded=False):
                tab_r, tab_p = st.tabs(["Registrado", "Prospecto"])
                with tab_r:
                    with st.form("cita_reg", clear_on_submit=True):
                        df_p = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
                        l_p = df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist() if not df_p.empty else []
                        p_sel = st.selectbox("Paciente", ["..."]+l_p); h_sel = st.selectbox("Hora", generar_slots_tiempo()); m_sel = st.text_input("Motivo"); d_sel = st.selectbox("Dr", ["Dr. Emmanuel", "Dra. Mónica"])
                        
                        # VALIDACIÓN DE SOBRECUPO
                        urgencia = st.checkbox("🚨 Es Urgencia (Permitir Sobrecupo)")
                        
                        if st.form_submit_button("Agendar"):
                            ocupado = verificar_disponibilidad(fecha_str, h_sel)
                            if ocupado and not urgencia:
                                st.error(f"⚠️ El horario {h_sel} ya está ocupado. Marca 'Urgencia' para encimar.")
                            elif p_sel == "...": st.error("Selecciona paciente")
                            else:
                                id_p, nom_p = p_sel.split(" - ")[0], p_sel.split(" - ")[1]
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, monto_pagado, saldo_pendiente, estado_pago, precio_lista, precio_final, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, notas, fecha_pago, costo_laboratorio, categoria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_str, h_sel, id_p, nom_p, "General", sanitizar(m_sel), d_sel, 0, 0, "Pendiente", 0, 0, 0, "No", 0, 0, "", "No", "", "", 0, "General"))
                                conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()

                with tab_p:
                    with st.form("cita_pros", clear_on_submit=True):
                        n_pros = st.text_input("Nombre"); t_pros = st.text_input("Tel"); h_pros = st.selectbox("Hora", generar_slots_tiempo()); m_pros = st.text_input("Motivo"); d_pros = st.selectbox("Dr", ["Dr. Emmanuel", "Dra. Mónica"])
                        urgencia_p = st.checkbox("🚨 Urgencia (Sobrecupo)")
                        if st.form_submit_button("Agendar Prospecto"):
                            ocupado = verificar_disponibilidad(fecha_str, h_pros)
                            if ocupado and not urgencia_p: st.error(f"⚠️ Horario {h_pros} ocupado.")
                            elif n_pros:
                                c = conn.cursor()
                                c.execute('''INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tipo, tratamiento, doctor_atendio, precio_final, monto_pagado, saldo_pendiente, estado_pago, notas, precio_lista, porcentaje, tiene_factura, iva, subtotal, metodo_pago, requiere_factura, fecha_pago, costo_laboratorio, categoria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                          (int(time.time()), fecha_str, h_pros, f"PROS-{int(time.time())}", sanitizar(n_pros), "Primera Vez", sanitizar(m_pros), d_pros, 0, 0, 0, "Pendiente", f"Tel: {t_pros}", 0, 0, "No", 0, 0, "", "No", "", 0, "Primera Vez"))
                                conn.commit(); st.success("Agendado"); time.sleep(1); st.rerun()

            st.markdown("### 🔄 Modificar")
            df_c = pd.read_sql("SELECT * FROM citas", conn)
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_str]
                if not df_dia.empty:
                    l_citas = [f"{r['hora']} - {r['nombre_paciente']} ({r['estado_pago']})" for i, r in df_dia.iterrows()]
                    sel_cita = st.selectbox("Seleccionar:", ["..."] + l_citas)
                    if sel_cita != "...":
                        h_t = sel_cita.split(" - ")[0]; n_t = sel_cita.split(" - ")[1].split(" (")[0]
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            nf = st.date_input("N. Fecha", datetime.now(TZ_MX)); nh = st.selectbox("N. Hora", generar_slots_tiempo(), key="r_h")
                            if st.button("Mover"):
                                c = conn.cursor(); c.execute("UPDATE citas SET fecha=?, hora=?, estado_pago='Pendiente' WHERE fecha=? AND hora=? AND nombre_paciente=?", (format_date_latino(nf), nh, fecha_str, h_t, n_t))
                                conn.commit(); st.success("Movido"); time.sleep(1); st.rerun()
                        with c2:
                            if st.button("Cancelar"):
                                c = conn.cursor(); c.execute("UPDATE citas SET estado_pago='CANCELADO' WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_str, h_t, n_t))
                                conn.commit(); st.warning("Cancelado"); time.sleep(1); st.rerun()
                        with c3:
                            if st.button("Eliminar"):
                                c = conn.cursor(); c.execute("DELETE FROM citas WHERE fecha=? AND hora=? AND nombre_paciente=?", (fecha_str, h_t, n_t))
                                conn.commit(); registrar_auditoria("Consultorio", "ELIMINAR", f"Cita {n_t}"); st.error("Eliminado"); time.sleep(1); st.rerun()

        with col_cal2:
            st.markdown(f"#### 📋 {fecha_str}")
            if not df_c.empty:
                df_dia = df_c[df_c['fecha'] == fecha_str]
                for slot in generar_slots_tiempo():
                    ocupado = df_dia[(df_dia['hora'] == slot) & (df_dia['estado_pago'] != 'CANCELADO')]
                    if ocupado.empty: st.markdown(f"<div style='color:#ccc; border-bottom:1px solid #eee;'>{slot} Disponible</div>", unsafe_allow_html=True)
                    else:
                        for _, r in ocupado.iterrows():
                            color = "#FF5722" if "PROS" in str(r['id_paciente']) else "#002B5B"
                            st.markdown(f"<div style='padding:5px; border-left:4px solid {color}; background:#fff; margin-bottom:2px;'><b>{slot} {r['nombre_paciente']}</b><br><small>{r['tratamiento']}</small></div>", unsafe_allow_html=True)

    # --- MÓDULO 2 Y 3 (RESUMIDO PARA NO REPETIR LÓGICA, PEGA IGUAL QUE V10 PERO CON CORRECCIONES DE PDF) ---
    elif menu == "2. Gestión Pacientes":
        st.title("📂 Expediente"); tab1, tab2, tab3 = st.tabs(["BUSCAR", "NUEVO", "EDITAR"])
        with tab1: # BUSCAR CON PDF FIX
            df_p = pd.read_sql("SELECT * FROM pacientes", conn)
            if not df_p.empty:
                sel = st.selectbox("Paciente:", ["..."] + df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']} {x['apellido_paterno']}", axis=1).tolist())
                if sel != "...":
                    p = df_p[df_p['id_paciente'] == sel.split(" - ")[0]].iloc[0]
                    st.write(f"👤 {p['nombre']} {p['apellido_paterno']} | Tel: {p['telefono']}")
                    st.markdown(f"**Historial:**"); hist = pd.read_sql(f"SELECT fecha, tratamiento, notas FROM citas WHERE id_paciente='{p['id_paciente']}' ORDER BY timestamp DESC", conn); st.dataframe(hist)
                    if st.button("🖨️ PDF Historia"):
                        pdf_data = crear_pdf_historia(p, hist); st.download_button("Descargar", pdf_data, "Historia.pdf", "application/pdf")
        with tab2: # ALTA
            with st.form("alta", clear_on_submit=True):
                n = st.text_input("Nombre"); p = st.text_input("Paterno"); m = st.text_input("Materno"); t = st.text_input("Tel"); fn = st.date_input("Nacimiento", datetime(1990,1,1))
                s = st.selectbox("Sexo", ["Mujer", "Hombre"]); av = st.checkbox("Aviso Privacidad")
                if st.form_submit_button("Guardar"):
                    if av and n and p and len(t)==10:
                        id_n = generar_id_unico(sanitizar(n), sanitizar(p), fn)
                        c = conn.cursor(); c.execute("INSERT INTO pacientes (id_paciente, fecha_registro, nombre, apellido_paterno, apellido_materno, telefono, sexo, fecha_nacimiento) VALUES (?,?,?,?,?,?,?,?)", (id_n, get_fecha_mx(), sanitizar(n), sanitizar(p), sanitizar(m), t, s, format_date_latino(fn)))
                        conn.commit(); st.success("Guardado"); time.sleep(1); st.rerun()
                    else: st.error("Datos incompletos")
        with tab3: # EDITAR
            df_p = pd.read_sql("SELECT * FROM pacientes", conn)
            if not df_p.empty:
                sel = st.selectbox("Editar:", ["..."] + df_p['id_paciente'].tolist())
                if sel != "...":
                    curr = df_p[df_p['id_paciente'] == sel].iloc[0]
                    with st.form("edit"):
                        en = st.text_input("Nombre", curr['nombre']); et = st.text_input("Tel", curr['telefono'])
                        if st.form_submit_button("Actualizar"):
                            c=conn.cursor(); c.execute("UPDATE pacientes SET nombre=?, telefono=? WHERE id_paciente=?", (sanitizar(en), et, sel)); conn.commit(); st.success("Listo"); time.sleep(1); st.rerun()

    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Finanzas"); 
        df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", df_p.apply(lambda x: f"{x['id_paciente']} - {x['nombre']}", axis=1).tolist())
            id_p = sel.split(" - ")[0]; nom_p = sel.split(" - ")[1]
            st.markdown("#### Nuevo Cobro")
            with st.form("cobro"):
                trat = st.text_input("Tratamiento"); precio = st.number_input("Precio", step=50.0); abono = st.number_input("Abono", step=50.0)
                metodo = st.selectbox("Método", ["Efectivo", "Tarjeta", "Pendiente de Pago"])
                agendar = st.checkbox("¿Agendar Cita tratamiento?")
                f_cita = st.date_input("Fecha Cita"); h_cita = st.selectbox("Hora", generar_slots_tiempo())
                
                if st.form_submit_button("Registrar"):
                    # VALIDACIÓN DISPONIBILIDAD PARA CITA DE TRATAMIENTO
                    ocupado = verificar_disponibilidad(format_date_latino(f_cita), h_cita) if agendar else False
                    
                    if agendar and ocupado:
                        st.error(f"⚠️ No se pudo agendar la cita: El horario {h_cita} está ocupado. Registra el cobro y agenda manualmente como Urgencia si es necesario.")
                    else:
                        saldo = precio - abono; estatus = "Pagado" if saldo <=0 else "Pendiente"
                        c = conn.cursor()
                        c.execute("INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tratamiento, precio_final, monto_pagado, saldo_pendiente, estado_pago, metodo_pago, fecha_pago) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (int(time.time()), get_fecha_mx(), get_hora_mx(), id_p, nom_p, sanitizar(trat), precio, abono, saldo, estatus, metodo, get_fecha_mx()))
                        if agendar:
                            c.execute("INSERT INTO citas (timestamp, fecha, hora, id_paciente, nombre_paciente, tratamiento, estado_pago, notas) VALUES (?,?,?,?,?,?,?,?)",
                                      (int(time.time())+1, format_date_latino(f_cita), h_cita, id_p, nom_p, f"Tratamiento: {sanitizar(trat)}", "Pendiente", "Agendado desde Plan"))
                        conn.commit(); st.success("Registrado"); time.sleep(1); st.rerun()

    elif menu == "4. Documentos & Firmas":
        st.title("⚖️ Legal"); df_p = pd.read_sql("SELECT * FROM pacientes", conn)
        if not df_p.empty:
            sel = st.selectbox("Paciente:", df_p['nombre'].tolist())
            canvas = st_canvas(stroke_width=2, height=150, key="firmas")
            if st.button("Generar PDF"):
                if canvas.image_data is not None:
                    # Simulación de guardado de imagen para PDF
                    import numpy as np; from PIL import Image; import io
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); buf = io.BytesIO(); img.save(buf, format="PNG")
                    img_str = base64.b64encode(buf.getvalue()).decode()
                    pdf_data = crear_pdf_consentimiento(sel, "Dr. Emmanuel", "General", img_str)
                    st.download_button("Bajar PDF", pdf_data, "Consentimiento.pdf", "application/pdf")

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
