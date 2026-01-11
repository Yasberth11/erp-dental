import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time
import random
import string
from fpdf import FPDF
import io
import base64

# --- 0. LOGO EN BASE64 (TU IMAGEN CODIFICADA) ---
# Esto permite que el logo viva dentro del código sin archivos externos
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

# --- 1. CONFIGURACIÓN VISUAL Y DE PÁGINA ---
st.set_page_config(page_title="ROYAL Dental ERP", layout="wide", page_icon="🦷")

# Inyección de CSS (Estilos Personalizados Royal Blue)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #f4f6f9;}
    h1, h2, h3, h4 {color: #0c347d !important; font-family: 'Helvetica', sans-serif;}
    
    /* Botones Estilo Royal */
    div.stButton > button:first-child {
        background-color: #0c347d; color: white; border-radius: 8px; border: none; font-weight: bold; padding: 10px 24px;
    }
    div.stButton > button:hover {
        background-color: #1a4d9e; color: white; border: 1px solid #white;
    }
    /* Inputs */
    .stTextInput > div > div > input {border-radius: 5px;}
    /* Mensajes de Éxito Personalizados */
    .success-box {
        padding: 20px; background-color: #d4edda; color: #155724; border-radius: 10px;
        border-left: 5px solid #28a745; text-align: center; font-size: 18px; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A BASE DE DATOS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    try: return client.open("ERP_DENTAL_DB")
    except: return client.open("ERP_Dental_DB")

# --- 3. FUNCIONES DE LÓGICA DE NEGOCIO Y PDF ---

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

# Función auxiliar para poner el logo en el PDF
def header_logo(pdf):
    # Decodificar la imagen base64 a bytes
    img_data = base64.b64decode(LOGO_B64)
    # Crear un archivo temporal en memoria
    with io.BytesIO(img_data) as f:
        # Insertar imagen (x, y, ancho)
        pdf.image(f, x=10, y=8, w=30)
    pdf.set_font('Arial', 'B', 15)
    pdf.cell(80) # Mover a la derecha
    pdf.cell(30, 10, 'ROYAL DENTAL', 0, 0, 'C')
    pdf.ln(20) # Salto de línea después del header

def generar_pdf_expediente_inicial(datos_paciente):
    # datos_paciente es un diccionario con nombre, id, fecha, etc.
    pdf = FPDF()
    pdf.add_page()
    header_logo(pdf) # Agregar logo
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="CARÁTULA DE EXPEDIENTE CLÍNICO", ln=1, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"ID Paciente: {datos_paciente['id']}", ln=1)
    pdf.cell(0, 10, txt=f"Fecha de Registro: {datos_paciente['fecha']}", ln=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="DATOS GENERALES:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Nombre Completo: {datos_paciente['nombre']}", ln=1)
    pdf.cell(0, 10, txt=f"Fecha de Nacimiento: {datos_paciente['f_nac']}", ln=1)
    pdf.cell(0, 10, txt=f"Teléfono: {datos_paciente['tel']}", ln=1)
    pdf.cell(0, 10, txt=f"Email: {datos_paciente['email']}", ln=1)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="ANTECEDENTES MÉDICOS REPORTADOS:", ln=1)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 10, txt=datos_paciente['historial'])
    
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_consentimiento(nombre_paciente, tratamiento, doctor):
    pdf = FPDF()
    pdf.add_page()
    header_logo(pdf) # Agregar logo
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="CONSENTIMIENTO INFORMADO", ln=1, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    texto = f"Yo, {nombre_paciente}, estando en pleno uso de mis facultades mentales, otorgo mi consentimiento libre e informado al C.D. {doctor} y al personal de ROYAL DENTAL para que se me realice el procedimiento odontológico denominado:\n\n"
    pdf.multi_cell(0, 8, txt=texto)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"*** {tratamiento.upper()} ***", ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    texto_cierre = "Se me han explicado en lenguaje claro los objetivos, beneficios, riesgos y alternativas de dicho tratamiento. He tenido la oportunidad de hacer preguntas y han sido resueltas a mi satisfacción. Entiendo que la odontología no es una ciencia exacta y no se pueden garantizar resultados al 100%.\n\n"
    pdf.multi_cell(0, 8, txt=texto_cierre)
    pdf.ln(20)
    
    pdf.cell(0, 10, txt="__________________________", ln=1, align="C")
    pdf.cell(0, 10, txt="Firma del Paciente", ln=1, align="C")
    pdf.cell(0, 10, txt=f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        return pd.DataFrame(worksheet.get_all_records())
    except: return pd.DataFrame()

def guardar_fila(hoja, pestaña, datos):
    worksheet = hoja.worksheet(pestaña)
    worksheet.append_row(datos)

# --- CATALOGOS ---
REGIMENES_FISCALES = ["605 - Sueldos y Salarios", "626 - RESICO", "612 - Actividades Empresariales y Profesionales", "616 - Sin obligaciones fiscales", "601 - General Personas Morales"]
USO_CFDI = ["D01 - Honorarios médicos", "S01 - Sin efectos fiscales", "G03 - Gastos en general"]
DIENTES_ADULTO = [str(x) for x in range(11, 19)] + [str(x) for x in range(21, 29)] + [str(x) for x in range(31, 39)] + [str(x) for x in range(41, 49)]
DIENTES_NINO = [str(x) for x in range(51, 56)] + [str(x) for x in range(61, 66)] + [str(x) for x in range(71, 76)] + [str(x) for x in range(81, 86)]
LISTA_DIENTES = ["General / No Aplica"] + [f"Adulto - {d}" for d in DIENTES_ADULTO] + [f"Niño - {d}" for d in DIENTES_NINO]

# --- PROGRAMA PRINCIPAL ---
def main():
    try:
        sheet = conectar_google_sheets()
    except:
        st.error("Error de conexión. Revisa credenciales.")
        st.stop()

    # SIDEBAR CON LOGO
    # Usamos el logo base64 en el sidebar
    st.sidebar.markdown(
        f'<img src="data:image/png;base64,{LOGO_B64}" width="120">',
        unsafe_allow_html=True
    )
    st.sidebar.title("ROYAL DENTAL")
    st.sidebar.caption("ERP v5.0 Platinum")
    
    rol = "Operativo"
    password = st.sidebar.text_input("🔐 Acceso Director", type="password")
    if password == "ROYALADMIN":
        rol = "Admin"
        st.sidebar.success("Modo Director")
        menu = st.sidebar.radio("Menú", ["Recepción (Buscar)", "Alta Pacientes", "Agenda & Caja", "Finanzas Globales"])
    else:
        st.sidebar.info("Modo Consultorio")
        menu = st.sidebar.radio("Menú", ["Recepción (Buscar)", "Alta Pacientes", "Agenda & Caja"])
    st.sidebar.markdown("---")

    # --- MÓDULOS ---
    if menu == "Recepción (Buscar)":
        st.header("🔍 Buscador de Pacientes")
        st.info("💡 Siempre busca al paciente antes de crear uno nuevo.")
        df_pacientes = cargar_datos(sheet, "pacientes")
        if not df_pacientes.empty:
            busqueda = st.text_input("Escribe nombre o apellidos:", placeholder="Ej. Lopez")
            if busqueda:
                mask = df_pacientes.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                resultados = df_pacientes[mask]
                if not resultados.empty:
                    st.success(f"Se encontraron {len(resultados)} expedientes.")
                    st.dataframe(resultados[['id_paciente', 'nombre_completo', 'telefono', 'ultima_visita']], use_container_width=True)
                else:
                    st.warning("No se encontró paciente. Ve a 'Alta Pacientes'.")

    elif menu == "Alta Pacientes":
        st.header("👤 Nuevo Expediente Clínico")
        with st.form("form_alta"):
            st.subheader("Datos Personales")
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre(s) *")
            ap_paterno = c2.text_input("Apellido Paterno *")
            ap_materno = c3.text_input("Apellido Materno")
            c4, c5, c6 = st.columns(3)
            f_nac = c4.date_input("Fecha de Nacimiento", min_value=date(1920, 1, 1), max_value=datetime.now(), value=date(1990, 1, 1))
            telefono = c5.text_input("Teléfono Móvil *")
            email = c6.text_input("Email")
            st.subheader("Datos Fiscales (2026)")
            fc1, fc2, fc3 = st.columns(3)
            rfc = fc1.text_input("RFC")
            regimen = fc2.selectbox("Régimen Fiscal", REGIMENES_FISCALES)
            cp = fc3.text_input("C.P.")
            uso = st.selectbox("Uso CFDI", USO_CFDI)
            st.subheader("Expediente Digital")
            historial = st.text_area("Enfermedades / Alergias / Antecedentes")
            submitted = st.form_submit_button("💾 Crear Expediente")
            
            if submitted:
                if nombre and ap_paterno and telefono:
                    nombre_comp = f"{nombre} {ap_paterno} {ap_materno}".strip()
                    nuevo_id = generar_id_paciente(nombre, ap_paterno, ap_materno)
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    fila = [nuevo_id, fecha_hoy, nombre_comp, telefono, email, rfc, "", cp, regimen, uso, historial, "Pendiente Link", "Activo", fecha_hoy]
                    guardar_fila(sheet, "pacientes", fila)
                    
                    # Feedback Visual
                    st.markdown(f"""<div class="success-box"><h1>🦷 ✅</h1><p><strong>¡Expediente Creado!</strong></p><p>{nombre_comp} | ID: {nuevo_id}</p></div>""", unsafe_allow_html=True)
                    
                    # --- GENERAR PDF EXPEDIENTE INICIAL ---
                    datos_pdf = {
                        'id': nuevo_id, 'nombre': nombre_comp, 'fecha': fecha_hoy,
                        'f_nac': f_nac.strftime("%d/%m/%Y"), 'tel': telefono, 'email': email, 'historial': historial
                    }
                    pdf_bytes = generar_pdf_expediente_inicial(datos_pdf)
                    st.download_button(label="📥 Descargar Carátula de Expediente (PDF)", data=pdf_bytes, file_name=f"Expediente_{nuevo_id}.pdf", mime='application/pdf')
                    st.info("Descarga este PDF como el documento inicial del historial electrónico del paciente.")
                else:
                    st.error("Faltan datos obligatorios.")

    elif menu == "Agenda & Caja":
        st.header("📅 Agenda y Cobranza")
        df_p = cargar_datos(sheet, "pacientes")
        df_s = cargar_datos(sheet, "servicios")
        if df_p.empty: st.stop()
        lista_pacientes = [f"{row['nombre_completo']} ({row['id_paciente']})" for i, row in df_p.iterrows()]
        c_pac, c_doc = st.columns(2)
        paciente_sel = c_pac.selectbox("Paciente", lista_pacientes)
        doctor_sel = c_doc.radio("Doctor Tratante", ["Dra. Mónica Rodríguez", "Dr. Emmanuel López"], horizontal=True)
        st.markdown("---")
        # Agenda Visual
        st.subheader("📆 Verificar Disponibilidad")
        col_ag1, col_ag2 = st.columns([1, 2])
        fecha_cita = col_ag1.date_input("Fecha", value=datetime.now())
        df_citas = cargar_datos(sheet, "citas")
        if not df_citas.empty:
            df_hoy = df_citas[df_citas['fecha'] == str(fecha_cita)]
            if not df_hoy.empty:
                 col_ag2.dataframe(df_hoy[['hora', 'doctor_atendio', 'nombre_paciente']], use_container_width=True)
            else: col_ag2.info("Agenda libre.")
        
        st.subheader("📝 Registrar Tratamiento")
        c_t1, c_t2, c_t3 = st.columns(3)
        cat_sel = c_t1.selectbox("Categoría", df_s['categoria'].unique())
        trat_disp = df_s[df_s['categoria'] == cat_sel]['nombre_tratamiento'].tolist()
        trat_sel = c_t2.selectbox("Tratamiento", trat_disp)
        diente_sel = c_t3.selectbox("Diente", LISTA_DIENTES)
        fila_trat = df_s[(df_s['categoria'] == cat_sel) & (df_s['nombre_tratamiento'] == trat_sel)].iloc[0]
        precio_base = float(fila_trat['precio_lista'])
        
        with st.form("form_caja"):
            c_hora, c_precio = st.columns(2)
            hora_cita = c_hora.time_input("Hora Cita", value=time(10, 0), step=1800)
            precio_final = c_precio.number_input("Precio Cobrado ($)", value=precio_base)
            generar_pdf = st.checkbox("Generar Consentimiento Informado (PDF)")
            c_pago, c_est = st.columns(2)
            metodo = c_pago.selectbox("Pago", ["Efectivo", "Tarjeta", "Transferencia"])
            estado = c_est.selectbox("Estatus", ["Pagado", "Pendiente"])
            notas = st.text_area("Notas")
            btn_guardar = st.form_submit_button("Agendar y Cobrar")
            
            if btn_guardar:
                hora_str = hora_cita.strftime("%H:%M:00")
                if verificar_disponibilidad(sheet, fecha_cita, hora_str, doctor_sel):
                    nombre_solo = paciente_sel.split(" (")[0]
                    id_solo = paciente_sel.split("(")[1].replace(")", "")
                    fila = [int(datetime.now().timestamp()), str(fecha_cita), str(hora_cita), id_solo, nombre_solo, cat_sel, trat_sel, diente_sel, doctor_sel, precio_base, precio_final, "0%", "NO", 0, precio_final, metodo, estado, "NO", notas]
                    guardar_fila(sheet, "citas", fila)
                    st.markdown(f"""<div class="success-box"><h3>✅ Cita Agendada</h3><p>{trat_sel} con {doctor_sel} a las {hora_cita}</p></div>""", unsafe_allow_html=True)
                    if generar_pdf:
                        # --- GENERAR PDF CONSENTIMIENTO CON LOGO ---
                        pdf_bytes = generar_pdf_consentimiento(nombre_solo, trat_sel, doctor_sel)
                        st.download_button(label="📥 Descargar Consentimiento PDF", data=pdf_bytes, file_name=f"Consentimiento_{id_solo}.pdf", mime='application/pdf')
                        st.info("Firma el PDF en la tablet/laptop y súbelo al expediente.")
                else:
                    st.error(f"⛔ ALERTA: El {doctor_sel} ya está ocupado a las {hora_cita}.")

    elif menu == "Finanzas Globales" and rol == "Admin":
        st.header("📊 Finanzas ROYAL Dental")
        st.write("Módulo financiero (visible solo para el Director).")

if __name__ == "__main__":
    main()
