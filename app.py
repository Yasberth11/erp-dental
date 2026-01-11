import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="ERP Dental", layout="wide")

# --- CONEXIÓN SEGURA A GOOGLE SHEETS ---
def conectar_google_sheets():
    # Definimos el alcance de los permisos
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Usamos los secretos de Streamlit (esto lo configuraremos en el siguiente paso)
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Abre la hoja de cálculo por su nombre exacto
    sheet = client.open("ERP_Dental_DB")
    return sheet

# --- FUNCIONES DE LECTURA/ESCRITURA ---
def cargar_datos(hoja, pestaña):
    worksheet = hoja.worksheet(pestaña)
    datos = worksheet.get_all_records()
    return pd.DataFrame(datos)

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
        st.success("Conexión con Base de Datos: EXITOSA")
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
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
                    # ID simple basado en el tiempo
                    id_p = int(datetime.now().timestamp())
                    
                    guardar_paciente(sheet, [id_p, nombre, telefono, email, historial, fecha])
                    st.success(f"Paciente {nombre} guardado correctamente.")
                    st.rerun() # Recargar para ver el cambio

        # Mostrar tabla de pacientes
        try:
            df_pacientes = cargar_datos(sheet, "pacientes")
            if not df_pacientes.empty:
                st.dataframe(df_pacientes, use_container_width=True)
            else:
                st.info("Aún no hay pacientes registrados.")
        except:
            st.warning("No se pudo leer la pestaña 'pacientes'. Revisa que exista en Google Sheets.")

    elif menu == "Nueva Cita":
        st.header("Agendar Cita")
        st.info("Módulo en construcción... (Primero probemos que guarde pacientes)")

if __name__ == "__main__":
    main()
