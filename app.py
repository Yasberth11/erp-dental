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

# --- 1. CONFIGURACIÓN VISUAL (DISEÑO ROYAL) ---
st.set_page_config(page_title="ROYAL Dental ERP", layout="wide", page_icon="🦷")

# Colores Corporativos
ROYAL_BLUE = "#002B5B"
GOLD = "#D4AF37"
BG_COLOR = "#F4F6F9"

st.markdown(f"""
    <style>
    /* Ocultar elementos default */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Fondo */
    .stApp {{background-color: {BG_COLOR};}}
    
    /* Títulos */
    h1, h2, h3 {{color: {ROYAL_BLUE} !important; font-family: 'Arial', sans-serif;}}
    
    /* Botones */
    div.stButton > button {{
        background-color: {ROYAL_BLUE};
        color: white;
        border: 1px solid {GOLD};
        border-radius: 6px;
        font-weight: bold;
    }}
    div.stButton > button:hover {{
        background-color: {GOLD};
        color: {ROYAL_BLUE};
        border-color: {ROYAL_BLUE};
    }}
    
    /* Tarjetas Personalizadas */
    .card-success {{
        padding: 15px; background-color: #d4edda; color: #155724; 
        border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 10px;
    }}
    .card-warning {{
        padding: 15px; background-color: #fff3cd; color: #856404; 
        border-radius: 8px; border-left: 5px solid #ffc107; margin-bottom: 10px;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # Intenta abrir con mayúsculas o minúsculas por seguridad
    try: return client.open("ERP_DENTAL_DB")
    except: return client.open("ERP_Dental_DB")

# --- 3. FUNCIONES DE LÓGICA ---
def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        df = pd.DataFrame(worksheet.get_all_records())
        # Normalizar nombres de columnas para evitar errores
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

def generar_link_calendar(titulo, fecha, hora, detalles=""):
    fecha_dt = datetime.combine(fecha, hora)
    inicio = fecha_dt.strftime("%Y%m%dT%H%M00")
    fin = (fecha_dt).strftime("%Y%m%dT%H%M00") # Duración default 1h
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    params = f"&text={urllib.parse.quote(titulo)}&dates={inicio}/{fin}&details={urllib.parse.quote(detalles)}"
    return base + params

# --- 4. GENERADOR DE PDF PROFESIONAL ---
class PDF(FPDF):
    def header(self):
        # Intentar cargar logo si existe en GitHub/Local
        if os.path.exists("logo.png"):
            try:
                self.image("logo.png", 10, 8, 30)
            except: pass
        
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 43, 91) # Azul Royal
        self.cell(80)
        self.cell(30, 10, 'ROYAL DENTAL', 0, 0, 'C')
        self.ln(6)
        
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(80)
        self.cell(30, 10, 'Odontología Especializada | San Mateo Xoloc, EdoMex', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def crear_pdf_expediente(datos):
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0,0,0)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "EXPEDIENTE CLÍNICO DIGITAL", ln=1, align="C")
    pdf.ln(5)
    
    # Sección Datos
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 1. DATOS GENERALES Y FISCALES", 1, 1, 'L', True)
    
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.cell(0, 6, f"Paciente: {datos['nombre']}", ln=1)
    pdf.cell(0, 6, f"ID: {datos['id']} | Fecha Registro: {datos['fecha']}", ln=1)
    pdf.cell(0, 6, f"RFC: {datos['rfc']} | Régimen: {datos['regimen']}", ln=1)
    pdf.cell(0, 6, f"Uso CFDI: {datos['uso']} | CP: {datos['cp']}", ln=1)
    pdf.cell(0, 6, f"Teléfono: {datos['tel']} | Email: {datos['email']}", ln=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ANTECEDENTES MÉDICOS (ANAMNESIS)", 1, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, f"\n{datos['alertas']}\n")
    
    return pdf.output(dest='S').encode('latin-1')

def crear_pdf_consentimiento(paciente, tratamiento, doctor):
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0,0,0)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "CONSENTIMIENTO INFORMADO", ln=1, align="C")
    
    texto_legal = (
        f"Yo, {paciente}, en pleno uso de mis facultades, autorizo al C.D. {doctor} "
        f"a realizar el tratamiento odontológico de: {tratamiento.upper()}.\n\n"
        "DECLARO QUE:\n"
        "1. Se me han explicado los objetivos, beneficios y posibles riesgos del procedimiento.\n"
        "2. Entiendo que la odontología no es una ciencia exacta y los resultados biológicos pueden variar.\n"
        "3. He tenido la oportunidad de hacer preguntas y han sido respondidas a mi satisfacción.\n"
        "4. Me comprometo a seguir las indicaciones post-operatorias para el éxito del tratamiento.\n"
    )
    
    pdf.set_font("Arial", size=11)
    pdf.ln(10)
    pdf.multi_cell(0, 7, texto_legal)
    
    pdf.ln(30)
    pdf.cell(0, 10, "__________________________", ln=1, align="C")
    pdf.cell(0, 10, "Firma de Conformidad del Paciente", ln=1, align="C")
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="C")
    
    return pdf.output(dest='S').encode('latin-1')


# --- 5. PROGRAMA PRINCIPAL ---
def main():
    try: sheet = conectar_google_sheets()
    except: st.error("⚠️ Error conectando a Google Sheets."); st.stop()

    # SIDEBAR
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=180)
        else:
            st.header("ROYAL DENTAL")
            st.caption("Sube 'logo.png' a GitHub")
        
        st.markdown("---")
        rol = "Operativo"
        
        # Menú de Navegación
        opcion = st.radio("Navegación", ["Agenda & Caja", "Nuevo Paciente", "Buscador", "Finanzas"])
        
        st.markdown("---")
        if st.checkbox("Acceso Director"):
            pwd = st.text_input("Contraseña", type="password")
            if pwd == "ROYALADMIN":
                rol = "Admin"
                st.success("Modo Director Activado")

    # --- MÓDULO: NUEVO PACIENTE ---
    if opcion == "Nuevo Paciente":
        st.title("👤 Alta de Paciente")
        st.markdown("Registro clínico y fiscal completo.")
        
        with st.form("form_alta"):
            st.subheader("Datos Personales")
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre(s) *")
            ap_pat = c2.text_input("Apellido Paterno *")
            ap_mat = c3.text_input("Apellido Materno")
            tel = c1.text_input("Teléfono Móvil *")
            email = c2.text_input("Email")
            
            st.subheader("Historia Clínica (Alertas)")
            alertas = st.text_area("Enfermedades / Alergias / Medicamentos", placeholder="Ej. Hipertenso, Alérgico a Penicilina...")
            
            st.subheader("Datos Fiscales (2026)")
            fc1, fc2, fc3 = st.columns(3)
            rfc = fc1.text_input("RFC")
            regimen = fc2.selectbox("Régimen", ["605 - Sueldos y Salarios", "612 - Act. Empresarial", "626 - RESICO", "616 - Sin Obligaciones", "601 - Morales"])
            uso = fc3.selectbox("Uso CFDI", ["D01 - Honorarios médicos", "G03 - Gastos general", "S01 - Sin efectos"])
            cp = st.text_input("Código Postal")
            
            btn_guardar = st.form_submit_button("💾 Guardar Expediente")
            
            if btn_guardar:
                if nombre and ap_pat and tel:
                    # Validar Duplicados
                    df_check = cargar_datos(sheet, "pacientes")
                    nuevo_nombre = f"{nombre} {ap_pat} {ap_mat}".strip().upper()
                    
                    duplicado = False
                    if not df_check.empty and 'nombre' in df_check.columns and 'apellido_paterno' in df_check.columns:
                        # Construir nombres existentes para comparar
                        nombres_ex = (df_check['nombre'] + " " + df_check['apellido_paterno']).str.upper()
                        if f"{nombre.upper()} {ap_pat.upper()}" in nombres_ex.values:
                            duplicado = True
                    
                    if duplicado:
                        st.error(f"⛔ El paciente {nuevo_nombre} ya existe en la base de datos.")
                    else:
                        # Guardar
                        id_p = generar_id(nombre, ap_pat)
                        fecha = datetime.now().strftime("%Y-%m-%d")
                        
                        # MAPEO EXACTO A TUS 15 COLUMNAS DE GOOGLE SHEETS
                        fila = [
                            id_p, fecha, nombre, ap_pat, ap_mat, tel, email,
                            rfc, regimen, uso, cp, alertas, "", "Activo", fecha
                        ]
                        guardar_fila(sheet, "pacientes", fila)
                        
                        # Generar PDF
                        datos_pdf = {
                            'id': id_p, 'nombre': nuevo_nombre, 'fecha': fecha,
                            'rfc': rfc, 'regimen': regimen, 'uso': uso, 'cp': cp,
                            'tel': tel, 'email': email, 'alertas': alertas
                        }
                        pdf_bytes = crear_pdf_expediente(datos_pdf)
                        
                        st.markdown(f"""<div class="card-success"><h3>✅ Paciente Registrado</h3>ID: {id_p}<br>Nombre: {nuevo_nombre}</div>""", unsafe_allow_html=True)
                        st.download_button("📥 Descargar Expediente PDF", data=pdf_bytes, file_name=f"EXP_{id_p}.pdf", mime="application/pdf")
                else:
                    st.error("Nombre, Apellido Paterno y Teléfono son obligatorios.")

    # --- MÓDULO: AGENDA Y CAJA ---
    elif opcion == "Agenda & Caja":
        st.title("📅 Agenda y Cobros")
        
        df_p = cargar_datos(sheet, "pacientes")
        df_s = cargar_datos(sheet, "servicios")
        
        if df_p.empty:
            st.info("Base de datos de pacientes vacía.")
        else:
            # Construir lista de selección
            # Manejo de errores si faltan columnas
            try:
                df_p['display'] = df_p['nombre'] + " " + df_p['apellido_paterno'] + " (" + df_p['id_paciente'] + ")"
                lista_pacientes = df_p['display'].tolist()
            except:
                st.error("Error leyendo columnas de nombre/apellido en Excel.")
                st.stop()
            
            c1, c2 = st.columns(2)
            paciente_sel = c1.selectbox("Buscar Paciente", lista_pacientes)
            doctor = c2.radio("Doctor Tratante", ["Dra. Mónica Rodríguez", "Dr. Emmanuel López"], horizontal=True)
            
            # Alerta Médica (Si existe en BD)
            try:
                id_sel = paciente_sel.split("(")[1].replace(")", "")
                paciente_data = df_p[df_p['id_paciente'] == id_sel].iloc[0]
                if paciente_data.get('alertas_medicas'):
                    st.markdown(f"""<div class="card-warning">⚠️ <b>ALERTA MÉDICA:</b> {paciente_data['alertas_medicas']}</div>""", unsafe_allow_html=True)
            except: pass
            
            st.markdown("---")
            
            col_izq, col_der = st.columns([2, 1])
            with col_izq:
                st.subheader("Tratamiento")
                if not df_s.empty:
                    cat = st.selectbox("Categoría", df_s['categoria'].unique())
                    trat = st.selectbox("Procedimiento", df_s[df_s['categoria']==cat]['nombre_tratamiento'])
                else:
                    trat = "Consulta"
                
                fecha_cita = st.date_input("Fecha Cita")
                hora_cita = st.time_input("Hora")
                
            with col_der:
                st.subheader("Caja")
                monto = st.number_input("Total a Cobrar ($)", value=0.0)
                metodo = st.selectbox("Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                if st.button("💰 COBRAR Y AGENDAR", use_container_width=True):
                    # Guardar Cita
                    nombre_p = paciente_sel.split(" (")[0]
                    fila_cita = [
                        int(datetime.now().timestamp()), str(fecha_cita), str(hora_cita),
                        id_sel, nombre_p, cat, trat, "General", doctor,
                        monto, monto, "0%", "NO", 0, monto, metodo, "Pagado", "NO", ""
                    ]
                    guardar_fila(sheet, "citas", fila_cita)
                    st.balloons()
                    st.success("¡Movimiento registrado!")
                    
                    # Generar Consentimiento
                    pdf_c = crear_pdf_consentimiento(nombre_p, trat, doctor)
                    st.download_button("📄 Bajar Consentimiento", data=pdf_c, file_name="Consentimiento.pdf", mime="application/pdf")
                    
                    # Link Calendar
                    link = generar_link_calendar(f"Cita Dental: {nombre_p}", fecha_cita, hora_cita, f"Tratamiento: {trat}\nDr: {doctor}")
                    st.markdown(f"[📅 **Click aquí para agregar a Google Calendar**]({link})", unsafe_allow_html=True)

    # --- MÓDULO: BUSCADOR ---
    elif opcion == "Buscador":
        st.header("🔍 Directorio de Pacientes")
        df_p = cargar_datos(sheet, "pacientes")
        if not df_p.empty:
            busqueda = st.text_input("Buscar por nombre o ID:")
            if busqueda:
                mask = df_p.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                st.dataframe(df_p[mask], use_container_width=True)
            else:
                st.dataframe(df_p, use_container_width=True)

    # --- MÓDULO: FINANZAS ---
    elif opcion == "Finanzas":
        if rol == "Admin":
            st.title("📊 Panel Financiero (Solo Director)")
            st.info("Módulo en desarrollo para reportes gráficos.")
        else:
            st.error("⛔ Acceso Denegado. Ingresa la contraseña de Director en la barra lateral.")

if __name__ == "__main__":
    main()
