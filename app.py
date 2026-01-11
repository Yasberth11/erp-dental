import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time
import random
import string
from fpdf import FPDF
import os
import urllib.parse
import re  # Para validar email

# --- 1. CONFIGURACIÓN VISUAL (DISEÑO ROYAL PREMIUM) ---
st.set_page_config(page_title="ROYAL Dental", layout="wide", page_icon="🦷")

# Colores
ROYAL_BLUE = "#002B5B"
ROYAL_LIGHT = "#E6F0FF" # Azul muy clarito para fondos de sección
GOLD = "#D4AF37"
WHITE = "#FFFFFF"

st.markdown(f"""
    <style>
    /* Ocultar elementos default */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Fondo Blanco Puro */
    .stApp {{background-color: {WHITE};}}
    
    /* Títulos con estilo corporativo */
    h1 {{color: {ROYAL_BLUE} !important; font-weight: 800;}}
    h2, h3 {{color: {ROYAL_BLUE} !important; border-bottom: 2px solid {GOLD}; padding-bottom: 5px;}}
    
    /* Contenedores de Sección (Cajas Azules) */
    .block-container {{padding-top: 2rem;}}
    
    /* Botones */
    div.stButton > button {{
        background-color: {ROYAL_BLUE};
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 16px;
        font-weight: bold;
        padding: 0.5rem 1rem;
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: {GOLD};
        color: {ROYAL_BLUE};
        transform: scale(1.02);
    }}
    
    /* Inputs más visibles */
    .stTextInput > div > div > input {{
        border: 1px solid #ced4da;
        background-color: #f8f9fa;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {ROYAL_BLUE};
        background-color: #fff;
    }}
    
    /* Tarjetas de Feedback */
    .card-success {{
        padding: 20px; background-color: #d1e7dd; color: #0f5132;
        border-radius: 8px; border-left: 6px solid #198754; margin-top: 20px;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    try: return client.open("ERP_DENTAL_DB")
    except: return client.open("ERP_Dental_DB")

# --- 3. LÓGICA DE NEGOCIO ---
def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        df = pd.DataFrame(worksheet.get_all_records())
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
        return df
    except: return pd.DataFrame()

def guardar_fila(hoja, pestaña, datos):
    worksheet = hoja.worksheet(pestaña)
    worksheet.append_row(datos)

def generar_id(nombre, apellido):
    iniciales = (nombre[0] + apellido[0]).upper()
    anio = datetime.now().strftime("%y")
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{iniciales}-{anio}-{rand}"

def validar_email(email):
    # Regex simple para validar email
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, email) is not None

def generar_link_calendar(titulo, fecha, hora, detalles=""):
    fecha_dt = datetime.combine(fecha, hora)
    inicio = fecha_dt.strftime("%Y%m%dT%H%M00")
    fin = (fecha_dt).strftime("%Y%m%dT%H%M00")
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    params = f"&text={urllib.parse.quote(titulo)}&dates={inicio}/{fin}&details={urllib.parse.quote(detalles)}"
    return base + params

# --- 4. PDF GENERATOR (CORREGIDO) ---
class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 30)
            except: pass
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 43, 91)
        self.cell(80)
        self.cell(30, 10, 'ROYAL DENTAL', 0, 0, 'C')
        self.ln(6)
        self.set_font('Arial', '', 9)
        self.set_text_color(100)
        self.cell(80)
        self.cell(30, 10, 'Odontología Especializada', 0, 0, 'C')
        self.ln(20)

def crear_pdf_expediente(datos):
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0,0,0)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "EXPEDIENTE CLÍNICO DIGITAL", ln=1, align="C")
    pdf.ln(5)
    
    # Datos
    pdf.set_fill_color(230, 240, 255) # Azul muy suave
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 1. DATOS GENERALES", 1, 1, 'L', True)
    
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.cell(0, 6, f"Paciente: {datos['nombre']}", ln=1)
    pdf.cell(0, 6, f"ID: {datos['id']} | Fecha: {datos['fecha']}", ln=1)
    pdf.cell(0, 6, f"Teléfono: {datos['tel']} | Email: {datos['email']}", ln=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. HISTORIA CLÍNICA (ALERTAS)", 1, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, f"\n{datos['alertas']}\n")
    
    # --- CORRECCIÓN DEL ERROR ROJO ---
    # En fpdf2, output() devuelve bytes directamente. NO usar encode('latin-1').
    return pdf.output()

def crear_pdf_consentimiento(paciente, tratamiento, doctor):
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "CONSENTIMIENTO INFORMADO", ln=1, align="C")
    
    texto = f"\nYo, {paciente}, autorizo al C.D. {doctor} el tratamiento de: {tratamiento.upper()}.\n\nSe me han explicado riesgos y beneficios.\n\nFirma: ____________________ Fecha: {datetime.now().strftime('%d/%m/%Y')}"
    
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, texto)
    return pdf.output()

# --- 5. APP PRINCIPAL ---
def main():
    try: sheet = conectar_google_sheets()
    except: st.error("⚠️ Error de conexión."); st.stop()

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=180)
        else: st.header("ROYAL DENTAL")
        
        st.markdown("---")
        opcion = st.radio("Menú Principal", ["Agenda & Caja", "Nuevo Paciente", "Buscador"], label_visibility="collapsed")
        
        st.markdown("---")
        if st.checkbox("Director"):
            if st.text_input("Clave", type="password") == "ROYALADMIN":
                st.success("Modo Admin")

    # --- PANTALLA: NUEVO PACIENTE ---
    if opcion == "Nuevo Paciente":
        st.title("👤 Nuevo Expediente")
        st.markdown("---")
        
        with st.form("form_alta"):
            st.subheader("1. Identificación Personal")
            
            # FILA 1: NOMBRES (Tab Order: 1 -> 2 -> 3)
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre(s) *", placeholder="Ej. Juan Carlos")
            ap_pat = c2.text_input("Apellido Paterno *", placeholder="Ej. Pérez")
            ap_mat = c3.text_input("Apellido Materno", placeholder="Ej. López")
            
            # FILA 2: CONTACTO (Tab Order: 4 -> 5)
            c4, c5 = st.columns(2)
            tel = c4.text_input("Teléfono Móvil (10 Dígitos) *", placeholder="5512345678", max_chars=10)
            email = c5.text_input("Correo Electrónico", placeholder="cliente@gmail.com")
            
            st.subheader("2. Historia Clínica")
            alertas = st.text_area("Alertas Médicas / Enfermedades", placeholder="Ej. Diabético, Hipertenso, Alérgico a Penicilina...")
            
            st.subheader("3. Datos Fiscales (2026)")
            fc1, fc2, fc3 = st.columns(3)
            rfc = fc1.text_input("RFC")
            regimen = fc2.selectbox("Régimen", ["605 - Sueldos y Salarios", "612 - Act. Empresarial", "626 - RESICO", "616 - Sin Obligaciones"])
            uso = fc3.selectbox("Uso CFDI", ["D01 - Honorarios médicos", "G03 - Gastos general", "S01 - Sin efectos"])
            cp = st.text_input("Código Postal")
            
            btn_guardar = st.form_submit_button("💾 Guardar Expediente")
            
            if btn_guardar:
                # --- VALIDACIONES ---
                errores = []
                if not nombre or not ap_pat: errores.append("• Falta Nombre o Apellido Paterno.")
                
                # Validación Teléfono (10 dígitos numéricos)
                if not tel or len(tel) != 10 or not tel.isdigit():
                    errores.append("• El teléfono debe tener exactamente 10 números (Sin guiones ni espacios).")
                
                # Validación Email (Si escribió algo)
                if email and not validar_email(email):
                    errores.append("• El correo electrónico no parece válido (falta @ o .com).")
                
                if errores:
                    for e in errores: st.error(e)
                else:
                    # PROCESO DE GUARDADO
                    nombre_comp = f"{nombre} {ap_pat} {ap_mat}".strip().upper()
                    
                    # Checar duplicados
                    df_check = cargar_datos(sheet, "pacientes")
                    duplicado = False
                    if not df_check.empty and 'nombre' in df_check.columns:
                        nombres_ex = (df_check['nombre'] + " " + df_check['apellido_paterno']).str.upper()
                        if f"{nombre.upper()} {ap_pat.upper()}" in nombres_ex.values:
                            duplicado = True
                    
                    if duplicado:
                        st.warning(f"⚠️ El paciente {nombre_comp} ya existe. Búscalo en la Agenda.")
                    else:
                        id_p = generar_id(nombre, ap_pat)
                        fecha = datetime.now().strftime("%Y-%m-%d")
                        
                        fila = [id_p, fecha, nombre, ap_pat, ap_mat, tel, email, rfc, regimen, uso, cp, alertas, "", "Activo", fecha]
                        guardar_fila(sheet, "pacientes", fila)
                        
                        # Generar PDF (Sin error)
                        datos_pdf = {'id': id_p, 'nombre': nombre_comp, 'fecha': fecha, 'tel': tel, 'email': email, 'alertas': alertas}
                        pdf_bytes = crear_pdf_expediente(datos_pdf)
                        
                        st.markdown(f"""<div class="card-success"><h3>✅ ¡Expediente Creado!</h3><b>{nombre_comp}</b><br>ID: {id_p}</div>""", unsafe_allow_html=True)
                        st.download_button("📥 Descargar Historia Clínica PDF", data=pdf_bytes, file_name=f"HC_{id_p}.pdf", mime="application/pdf")

    # --- PANTALLA: AGENDA ---
    elif opcion == "Agenda & Caja":
        st.title("📅 Agenda y Caja")
        # (Código de Agenda igual que antes, se mantiene funcional...)
        # Para abreviar respuesta, asumo que mantienes la lógica de agenda que ya funcionaba
        # Solo asegúrate de que al final del archivo esté el `if __name__ == "__main__": main()`
        
        df_p = cargar_datos(sheet, "pacientes")
        df_s = cargar_datos(sheet, "servicios")
        
        if df_p.empty:
            st.info("No hay pacientes.")
        else:
            try:
                df_p['display'] = df_p['nombre'] + " " + df_p['apellido_paterno'] + " (" + df_p['id_paciente'] + ")"
                lista = df_p['display'].tolist()
            except: lista = []
            
            c1, c2 = st.columns(2)
            paciente_sel = c1.selectbox("Paciente", lista)
            doctor = c2.radio("Doctor", ["Dra. Mónica", "Dr. Emmanuel"], horizontal=True)
            
            st.markdown("---")
            col_izq, col_der = st.columns([2, 1])
            
            with col_izq:
                st.subheader("Tratamiento")
                if not df_s.empty:
                    cat = st.selectbox("Categoría", df_s['categoria'].unique())
                    trat = st.selectbox("Procedimiento", df_s[df_s['categoria']==cat]['nombre_tratamiento'])
                else: trat = "Consulta"
                fecha_cita = st.date_input("Fecha")
                hora_cita = st.time_input("Hora")

            with col_der:
                st.subheader("Cobro")
                monto = st.number_input("Total ($)", value=0.0)
                if st.button("COBRAR", use_container_width=True):
                    # Guardar y generar PDF
                    id_solo = paciente_sel.split("(")[1].replace(")", "")
                    nombre_solo = paciente_sel.split(" (")[0]
                    fila = [int(datetime.now().timestamp()), str(fecha_cita), str(hora_cita), id_solo, nombre_solo, cat, trat, "Gral", doctor, monto, monto, "0", "NO", 0, monto, "Efec", "Pagado", "NO", ""]
                    guardar_fila(sheet, "citas", fila)
                    
                    st.success("Guardado")
                    pdf_c = crear_pdf_consentimiento(nombre_solo, trat, doctor)
                    st.download_button("📄 Consentimiento PDF", data=pdf_c, file_name="Consentimiento.pdf", mime="application/pdf")

    elif opcion == "Buscador":
        st.title("🔍 Directorio")
        df = cargar_datos(sheet, "pacientes")
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
