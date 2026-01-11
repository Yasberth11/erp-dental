import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="ERP Dental", layout="wide")

# --- CONEXIÓN SEGURA A GOOGLE SHEETS (VERSIÓN MODERNA) ---
def conectar_google_sheets():
    # Definimos los permisos
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Cargamos las credenciales desde los secretos de Streamlit
    creds_dict = st.secrets["gcp_service_account"]
    
    # Usamos la librería moderna google-auth
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Intentamos abrir la hoja (Probamos con mayúsculas y normal por si acaso)
    try:
        sheet = client.open("ERP_DENTAL_DB") # Nombre como en tu captura
    except:
        sheet = client.open("ERP_Dental_DB") # Intento alternativo
        
    return sheet

# --- FUNCIONES DE LECTURA/ESCRITURA ---
def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        datos = worksheet.get_all_records()
        return pd.DataFrame(datos)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame() # Devuelve vacío si no existe la pestaña

def guardar_paciente(hoja, datos_paciente):
    worksheet = hoja.worksheet("pacientes")
    worksheet.append_row(datos_paciente)

# --- INTERFAZ GRÁFICA ---
def main():
    st.title("🦷 ERP Consultorio Dental")
    st.markdown("---")

    # Intentamos conectar
    try:
        sheet = conectar_google_sheets()
        st.success("✅ Conexión Exitosa con la Base de Datos")
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        st.info("Verifica que el nombre de tu Hoja en Google sea 'ERP_DENTAL_DB' y que hayas compartido el acceso con el email del robot.")
        st.stop()

    # Menú lateral
    menu = st.sidebar.selectbox("Menú", ["Pacientes", "Nueva Cita", "Finanzas"])

    if menu == "Pacientes":
        st.header("Directorio de Pacientes")
        
        # Formulario para nuevo paciente
        with st.expander("➕ Agregar Nuevo Paciente"):
            with st.form("form_paciente"):
                col1, col2 = st.columns(2)
                nombre = col1.text_input("Nombre Completo")
                telefono = col2.text_input("Teléfono")
                email = col1.text_input("Email")
                historial = col2.text_area("Antecedentes Médicos")
                
                submitted = st.form_submit_button("Guardar Paciente")
                
                if submitted and nombre:
                    fecha = datetime.now().strftime("%Y-%m-%d")
                    id_p = int(datetime.now().timestamp())
                    
                    try:
                        guardar_paciente(sheet, [id_p, nombre, telefono, email, historial, fecha])
                        st.success(f"Paciente {nombre} guardado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

        # Mostrar tabla de pacientes
        st.subheader("Lista de Pacientes")
        df_pacientes = cargar_datos(sheet, "pacientes")
        
        if not df_pacientes.empty:
            st.dataframe(df_pacientes, use_container_width=True)
        else:
            st.info("Aún no hay pacientes registrados o no se encuentra la pestaña 'pacientes'.")

    elif menu == "Nueva Cita":
        st.header("Agendar Cita")
        st.warning("🚧 Módulo en construcción")

if __name__ == "__main__":
    main()
