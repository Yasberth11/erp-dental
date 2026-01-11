import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time, timedelta
import random
import string
from fpdf import FPDF
import io
import base64
import urllib.parse

# --- 0. LOGO EN BASE64 ---
LOGO_B64 = """
iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAMAAACahl6sAAADAFBMVEUAAAA/Pz9AQEBBQUFCQkJDQ0NERERF
RUVGRkZHR0dISEhJSUlKSkpLS0tMTExNTU1OTk5PT09QUFBRUVFSUlJTU1NUVFRVVVVWVlZXV1dYWFhZWVla
WlpbW1tcXFxdXV1eXl5fX19gYGBhYWFiYmJjY2NkY2NlZWVmZmZnZ2doaGhpaWlqampra2tsbGxtbW1ubm5v
b29wcHBxcXFycnJzc3N0dHR1dXV2dnZ3d3d4eHh5eXl6enp7e3t8fHx9fX1+fn5/f3+AgICBgYGCgoKDg4OE
hISFhYWGhoaHh4eIiIiJiYmKioqLi4uMjIyNjY2Ojo6Pj4+QkJCRkZGSkpKTk5OUlJSVlZWWlpaXl5eYmJiZ
mZmampqbm5ucnJydnZ2enp6fn5+goKChoaGioqKjo6OkpKSlpaWmpqanp6eoqKipqamqqqqrq6usrKytra2u
rq6vr6+wsLCxsbGysrKzs7O0tLS1tbW2tra3t7e4uLi5ubm6urq7u7u8vLy9vb2+vr6/v7/AwMDBwcHCwsLD
w8PExMTFxcXGxsbHx8fIyMjJycnKysrLy8vMzMzNzc3Ozs7Pz8/Q0NDR0dHS0tLT09PU1NTV1dXW1tbX19fY
2NjZ2dna2trb29vc3Nzd3d3e3t7f39/g4ODh4eHi4uLj4+Pk5OTl5eXm5ubn5+fo6Ojp6enq6urr6+vs7Ozt
7e3u7u7v7+/w8PDx8fHy8vLz8/P09PT19fX29vb39/f4+Pj5+fn6+vr7+/v8/Hz9/f3+/v7////+/v79/f38
/Hz7+/v6+vr5+fn4+Pj39/f29vb19fX09PTz8/Py8vLx8fHw8PDv7+/u7u7t7e3s7Ozr6+vq6unp6efn5+bm
5uXl5eTk5OPj4+Li4uHh4eDg4N/f397e3t3d3dzc3Nvb29ra2tnZ2djY2NfX19bW1tTU1NPT09LS0tHR0dDQ
0M/Pz87Ozs3NzcZQW18AAACXSURBVHic7cEBDQAAAMKg909tDjegAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPgDYxcAAX8xkuAAAAAASUVORK5CYII=
"""

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="ROYAL Dental ERP", layout="wide", page_icon="🦷")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #f4f6f9;}
    h1, h2, h3 {color: #0c347d !important;}
    div.stButton > button:first-child {background-color: #0c347d; color: white; border-radius: 8px;}
    .success-box {padding: 20px; background-color: #d4edda; color: #155724; border-radius: 10px; border-left: 5px solid #28a745; text-align: center;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    try: return client.open("ERP_DENTAL_DB")
    except: return client.open("ERP_Dental_DB")

# --- 3. LÓGICA ---
def generar_id_paciente(nombre, paterno, materno):
    iniciales = (nombre[0] + paterno[0] + (materno[0] if materno else "X")).upper()
    anio = datetime.now().strftime("%y")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{iniciales}-{anio}-{random_str}"

def verificar_disponibilidad(hoja, fecha, hora_str, doctor):
    try:
        worksheet = hoja.worksheet("citas")
        df = pd.DataFrame(worksheet.get_all_records())
        if df.empty: return True
        citas_doc = df[(df['fecha'] == str(fecha)) & (df['doctor_atendio'] == doctor)]
        if hora_str in citas_doc['hora'].astype(str).values: return False
        return True
    except: return True

def generar_link_calendar(titulo, fecha, hora, duracion_minutos=60, detalles=""):
    # Genera un link para agregar a Google Calendar con un clic
    fecha_dt = datetime.combine(fecha, hora)
    inicio = fecha_dt.strftime("%Y%m%dT%H%M00")
    fin = (fecha_dt + timedelta(minutes=duracion_minutos)).strftime("%Y%m%dT%H%M00")
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    params = f"&text={urllib.parse.quote(titulo)}&dates={inicio}/{fin}&details={urllib.parse.quote(detalles)}"
    return base_url + params

# --- 4. GENERACIÓN DE DOCUMENTOS LEGALES (PDF) ---
class PDF(FPDF):
    def header(self):
        # Logo decodificado
        img_data = base64.b64decode(LOGO_B64)
        with io.BytesIO(img_data) as f:
            self.image(f, 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'ROYAL DENTAL', 0, 0, 'C')
        self.ln(5)
        self.set_font('Arial', '', 9)
        self.cell(80)
        self.cell(30, 10, 'Calle el Chila S/N, San Mateo Xoloc, Tepotzotlán, EdoMex.', 0, 0, 'C')
        self.ln(20)

def generar_historia_clinica(datos):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "HISTORIA CLÍNICA Y ANAMNESIS", ln=1, align="C")
    
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Paciente: {datos['nombre']} | ID: {datos['id']}", ln=1)
    pdf.cell(0, 10, f"Fecha: {datos['fecha']} | Edad: {datos['edad']} años", ln=1)
    
    pdf.ln(5)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, "1. ANTECEDENTES PATOLÓGICOS", 1, 1, 'L', True)
    
    pdf.multi_cell(0, 6, txt=f"Enfermedades Sistémicas: {datos['enfermedades']}\nAlergias: {datos['alergias']}\nMedicamentos actuales: {datos['medicamentos']}\nHospitalizaciones previas: {datos['hospitalizaciones']}")
    
    pdf.ln(5)
    pdf.cell(0, 8, "2. EXAMEN ODONTOLÓGICO INICIAL", 1, 1, 'L', True)
    pdf.multi_cell(0, 6, txt=f"Motivo de consulta: {datos['motivo']}\nObservaciones: {datos['observaciones']}")
    
    pdf.ln(20)
    pdf.cell(0, 10, "__________________________", ln=1, align="C")
    pdf.cell(0, 10, "Firma del Paciente / Tutor", ln=1, align="C")
    return pdf.output(dest='S').encode('latin-1')

def generar_consentimiento_legal(paciente, tratamiento, doctor):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "CONSENTIMIENTO INFORMADO LEGAL", ln=1, align="C")
    
    texto_legal = (
        f"Yo, {paciente}, por mi propia voluntad, autorizo al C.D. {doctor} y a sus auxiliares "
        f"a realizar el tratamiento de: {tratamiento}.\n\n"
        "DECLARACIONES Y RIESGOS:\n"
        "1. Se me ha explicado que la Odontología no es una ciencia exacta y que, a pesar de la "
        "excelencia en el servicio, existen riesgos biológicos inherentes (infección, inflamación, "
        "sensibilidad, rechazo de materiales, parestesia, fractura) que pueden requerir tratamientos adicionales.\n"
        "2. Entiendo que ocultar información sobre mi estado de salud (alergias, diabetes, hipertensión) "
        "puede tener consecuencias graves, eximiendo de responsabilidad al consultorio.\n"
        "3. Me comprometo a seguir las indicaciones post-operatorias. El consultorio no se hace responsable "
        "por fallas derivadas de mi negligencia o falta de higiene.\n"
        "4. Costos: Estoy de acuerdo con el presupuesto y entiendo que el pago debe cubrirse según lo acordado.\n\n"
        "Habiendo leído y comprendido lo anterior, firmo de conformidad."
    )
    
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, texto_legal)
    
    pdf.ln(30)
    c1, c2 = pdf.get_x(), pdf.get_y()
    pdf.cell(90, 10, "_______________________", ln=0, align="C")
    pdf.cell(90, 10, "_______________________", ln=1, align="C")
    pdf.cell(90, 10, "Firma del Paciente", ln=0, align="C")
    pdf.cell(90, 10, f"Firma {doctor}", ln=1, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        return pd.DataFrame(worksheet.get_all_records())
    except: return pd.DataFrame()

def guardar_fila(hoja, pestaña, datos):
    worksheet = hoja.worksheet(pestaña)
    worksheet.append_row(datos)

# --- PROGRAMA PRINCIPAL ---
def main():
    if 'paciente_nuevo_id' not in st.session_state:
        st.session_state.paciente_nuevo_id = None

    try: sheet = conectar_google_sheets()
    except: st.error("Error de conexión."); st.stop()

    # Sidebar
    st.sidebar.image(f"data:image/png;base64,{LOGO_B64}", width=100)
    st.sidebar.title("ROYAL DENTAL v5.1")
    
    rol = "Operativo"
    pwd = st.sidebar.text_input("🔐 Director", type="password")
    if pwd == "ROYALADMIN":
        rol = "Admin"
        menu = st.sidebar.radio("Menú", ["Agenda & Caja", "Alta Pacientes", "Finanzas"])
    else:
        menu = st.sidebar.radio("Menú", ["Agenda & Caja", "Alta Pacientes"])

    # --- MÓDULO ALTA PACIENTES ---
    if menu == "Alta Pacientes":
        st.header("👤 Alta de Paciente y Anamnesis")
        
        # Paso 1: Datos Generales
        with st.form("form_alta"):
            st.subheader("1. Identificación")
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre(s)")
            ap_p = c2.text_input("Apellido Paterno")
            ap_m = c3.text_input("Apellido Materno")
            f_nac = st.date_input("Fecha Nacimiento", value=date(1990,1,1), min_value=date(1920,1,1))
            tel = st.text_input("Teléfono")
            email = st.text_input("Email")
            
            st.subheader("2. Anamnesis (Historia Clínica)")
            ac1, ac2 = st.columns(2)
            enfermedades = ac1.text_area("Enfermedades (Diabetes, HTA, etc.)", "Niega")
            alergias = ac2.text_area("Alergias (Penicilina, Latex, AINES)", "Niega")
            medicamentos = ac1.text_input("¿Toma medicamentos actualmente?", "Ninguno")
            hospital = ac2.text_input("Cirugías u Hospitalizaciones previas", "Ninguna")
            
            st.subheader("3. Datos Fiscales")
            rfc = st.text_input("RFC")
            regimen = st.selectbox("Régimen", ["605 - Sueldos y Salarios", "612 - P. Físicas", "626 - RESICO", "Sin Obligaciones"])
            
            submitted = st.form_submit_button("💾 Guardar y Generar Expediente")
            
            if submitted:
                # 1. Validación de Duplicados
                df_exist = cargar_datos(sheet, "pacientes")
                nombre_comp = f"{nombre} {ap_p} {ap_m}".strip().upper()
                
                duplicado = False
                if not df_exist.empty:
                    if nombre_comp in df_exist['nombre_completo'].str.upper().values:
                        duplicado = True
                
                if duplicado:
                    st.error(f"⛔ ¡ERROR! El paciente {nombre_comp} YA EXISTE. No se puede duplicar.")
                elif nombre and ap_p and tel:
                    # Generar ID
                    nuevo_id = generar_id_paciente(nombre, ap_p, ap_m)
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    edad = datetime.now().year - f_nac.year
                    
                    # Guardar en Sheets
                    fila = [nuevo_id, fecha_hoy, nombre_comp, tel, email, rfc, "", "", regimen, "", f"Alergias: {alergias}. Enf: {enfermedades}", "Pendiente", "Activo", fecha_hoy]
                    guardar_fila(sheet, "pacientes", fila)
                    
                    # Guardar estado para mostrar opciones
                    st.session_state.paciente_nuevo_id = nuevo_id
                    st.session_state.paciente_nuevo_nombre = nombre_comp
                    st.session_state.datos_hc = {
                        'nombre': nombre_comp, 'id': nuevo_id, 'fecha': fecha_hoy,
                        'edad': edad, 'enfermedades': enfermedades, 'alergias': alergias,
                        'medicamentos': medicamentos, 'hospitalizaciones': hospital,
                        'motivo': "Primera Vez", 'observaciones': "Paciente ingresado."
                    }
                    st.rerun()
                else:
                    st.warning("Faltan datos obligatorios.")

        # PANTALLA DE ÉXITO Y OPCIONES (Aparece después de guardar)
        if st.session_state.paciente_nuevo_id:
            st.markdown(f"""
            <div class="success-box">
                <h3>✅ Expediente Creado: {st.session_state.paciente_nuevo_nombre}</h3>
                <p>ID: {st.session_state.paciente_nuevo_id}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            
            # Botón Descargar Historia Clínica
            datos_hc = st.session_state.datos_hc
            pdf_hc = generar_historia_clinica(datos_hc)
            c1.download_button("📥 Descargar Historia Clínica (PDF)", data=pdf_hc, file_name=f"HC_{datos_hc['id']}.pdf", mime="application/pdf")
            
            # Botón Agendar Cita Inmediata
            if c2.button("📅 Agendar Primera Cita"):
                st.session_state.paciente_nuevo_id = None # Limpiar estado
                # Aquí podrías redirigir, por ahora indicamos manual
                st.info("Ve a la pestaña 'Agenda & Caja' y busca al paciente recién creado.")

    # --- MÓDULO AGENDA ---
    elif menu == "Agenda & Caja":
        st.header("📅 Agenda, Consentimiento y Cobranza")
        
        df_p = cargar_datos(sheet, "pacientes")
        df_s = cargar_datos(sheet, "servicios")
        
        if df_p.empty: st.info("No hay pacientes."); st.stop()
        
        # Buscador
        lista_pacientes = [f"{row['nombre_completo']} ({row['id_paciente']})" for i, row in df_p.iterrows()]
        paciente_sel = st.selectbox("Buscar Paciente", lista_pacientes)
        
        c1, c2 = st.columns(2)
        doctor = c1.radio("Doctor", ["Dra. Mónica Rodríguez", "Dr. Emmanuel López"], horizontal=True)
        fecha = c2.date_input("Fecha Cita")
        hora = c2.time_input("Hora Cita")
        
        st.subheader("Tratamiento")
        cat = st.selectbox("Categoría", df_s['categoria'].unique())
        trat = st.selectbox("Procedimiento", df_s[df_s['categoria']==cat]['nombre_tratamiento'])
        
        # Botones de Acción
        bc1, bc2 = st.columns(2)
        
        # 1. Generar Consentimiento PREVIO (Para imprimir y firmar antes de atender)
        pdf_consent = generar_consentimiento_legal(paciente_sel.split("(")[0], trat, doctor)
        bc1.download_button("📄 Descargar Consentimiento Informado (Legal)", data=pdf_consent, file_name="Consentimiento.pdf", mime="application/pdf")
        
        # 2. Link a Calendar
        nombre_paciente = paciente_sel.split(" (")[0]
        link_cal = generar_link_calendar(f"Cita: {nombre_paciente}", fecha, hora, detalles=f"Tratamiento: {trat}\nDr: {doctor}")
        bc2.markdown(f"[📅 **Agregar a Google Calendar**]({link_cal})", unsafe_allow_html=True)
        
        # 3. Guardar Cita (Caja)
        with st.expander("💸 Registrar Cobro y Guardar Cita"):
            precio = st.number_input("Monto", value=0.0)
            if st.button("Confirmar Cita y Cobro"):
                # ... (Lógica de guardado igual que antes) ...
                fila = [str(datetime.now()), str(fecha), str(hora), "ID", nombre_paciente, cat, trat, "General", doctor, precio, precio, "0", "NO", 0, 0, "Efec", "Pagado", "NO", ""]
                guardar_fila(sheet, "citas", fila)
                st.success("Cita Guardada")

    elif menu == "Finanzas" and rol == "Admin":
        st.write("Módulo Financiero")

if __name__ == "__main__":
    main()
