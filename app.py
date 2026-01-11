import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import random
import string

# --- CONFIGURACIÓN DE PÁGINA E IDENTIDAD ---
st.set_page_config(page_title="ROYAL Dental ERP", layout="wide", page_icon="🦷")

# Estilos CSS para ocultar menú de desarrollador y dar look profesional
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #f7f9fc;}
    h1 {color: #0c347d;} 
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # Intento doble de nombre por seguridad
    try:
        return client.open("ERP_DENTAL_DB")
    except:
        return client.open("ERP_Dental_DB")

# --- FUNCIONES AUXILIARES ---
def generar_id_paciente(nombre):
    # Ejemplo: Juan Perez -> JP-24-X9Z
    iniciales = "".join([n[0] for n in nombre.split()[:2]]).upper()
    anio = datetime.now().strftime("%y")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{iniciales}-{anio}-{random_str}"

def cargar_datos(hoja, pestaña):
    try:
        worksheet = hoja.worksheet(pestaña)
        return pd.DataFrame(worksheet.get_all_records())
    except:
        return pd.DataFrame()

def guardar_fila(hoja, pestaña, datos):
    worksheet = hoja.worksheet(pestaña)
    worksheet.append_row(datos)

# --- LISTA DE DIENTES (FDI) ---
DIENTES_ADULTO = [str(x) for x in range(11, 19)] + [str(x) for x in range(21, 29)] + \
                 [str(x) for x in range(31, 39)] + [str(x) for x in range(41, 49)]
DIENTES_NINO = [str(x) for x in range(51, 56)] + [str(x) for x in range(61, 66)] + \
               [str(x) for x in range(71, 76)] + [str(x) for x in range(81, 86)]
LISTA_DIENTES = ["General / No Aplica"] + [f"Adulto - {d}" for d in DIENTES_ADULTO] + [f"Niño - {d}" for d in DIENTES_NINO]

# --- PROGRAMA PRINCIPAL ---
def main():
    # Cabecera Institucional
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        st.write("🦷") # Aquí iría tu logo real con st.image
    with col_titulo:
        st.title("ROYAL DENTAL | Sistema de Gestión")
        st.caption("Dra. Mónica Rodríguez | Dr. Emmanuel López")

    # Conexión
    try:
        sheet = conectar_google_sheets()
    except Exception as e:
        st.error("Error de conexión. Verifica secretos y nombre de la hoja.")
        st.stop()

    # --- SISTEMA DE LOGIN (SEGURIDAD) ---
    # Por defecto, todos son "Operativos" (Consultorio)
    rol = "Operativo"
    
    # Sidebar de Navegación
    st.sidebar.header("Menú Principal")
    
    # Candado de Seguridad
    password = st.sidebar.text_input("🔐 Acceso Administrativo", type="password")
    if password == "ROYALADMIN": # <--- TU CONTRASEÑA MAESTRA
        rol = "Admin"
        st.sidebar.success("Modo Director Activo")
        opciones_menu = ["Recepción / Agenda", "Alta Pacientes", "Caja (Cobros)", "Finanzas & Nómina", "Configuración"]
    else:
        st.sidebar.info("Modo Consultorio")
        opciones_menu = ["Recepción / Agenda", "Alta Pacientes", "Caja (Cobros)"]

    menu = st.sidebar.radio("Ir a:", opciones_menu)
    st.sidebar.markdown("---")

    # --- MÓDULO 1: RECEPCIÓN / AGENDA ---
    if menu == "Recepción / Agenda":
        st.header("📅 Agenda del Día y Pacientes")
        df_pacientes = cargar_datos(sheet, "pacientes")
        
        if not df_pacientes.empty:
            busqueda = st.text_input("🔍 Buscar Paciente (Nombre o Teléfono):")
            if busqueda:
                df_filtrado = df_pacientes[df_pacientes.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
                if not df_filtrado.empty:
                    st.dataframe(df_filtrado[['id_paciente', 'nombre_completo', 'telefono', 'estado_paciente', 'ultima_visita']], use_container_width=True)
                else:
                    st.warning("No se encontró al paciente.")
            else:
                st.info("Escribe arriba para buscar un expediente.")
        else:
            st.warning("Base de datos de pacientes vacía.")

    # --- MÓDULO 2: ALTA PACIENTES ---
    elif menu == "Alta Pacientes":
        st.header("👤 Nuevo Expediente")
        with st.form("form_alta"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre Completo *")
            telefono = c2.text_input("Teléfono *")
            email = c1.text_input("Email")
            f_nac = c2.date_input("Fecha de Nacimiento")
            
            st.markdown("### 📝 Datos Fiscales (Facturación)")
            fc1, fc2, fc3 = st.columns(3)
            rfc = fc1.text_input("RFC")
            razon_social = fc2.text_input("Razón Social")
            uso_cfdi = fc3.selectbox("Uso CFDI", ["G03 - Gastos General", "D01 - Honorarios Médicos", "S01 - Sin Efectos"])
            
            historial = st.text_area("Link Carpeta Drive (Expediente Digital)")
            
            if st.form_submit_button("Crear Expediente"):
                if nombre and telefono:
                    nuevo_id = generar_id_paciente(nombre)
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    # Guardar ordenado según tu Excel
                    datos = [
                        nuevo_id, fecha_hoy, nombre, telefono, email,
                        rfc, razon_social, "N/A", "N/A", uso_cfdi, # CP y Regimen simplificados
                        "Ver en Drive", historial, "Activo", fecha_hoy
                    ]
                    guardar_fila(sheet, "pacientes", datos)
                    st.success(f"Paciente registrado con ID: {nuevo_id}")
                    st.balloons()
                else:
                    st.error("Nombre y Teléfono son obligatorios.")

    # --- MÓDULO 3: CAJA Y COBROS (EL NÚCLEO) ---
    elif menu == "Caja (Cobros)":
        st.header("💰 Registrar Tratamiento y Cobro")
        
        # Cargar catálogos
        df_p = cargar_datos(sheet, "pacientes")
        df_s = cargar_datos(sheet, "servicios")
        
        if df_p.empty or df_s.empty:
            st.error("Faltan datos en Pacientes o Servicios.")
            st.stop()
            
        # Selectores Inteligentes
        lista_pacientes = [f"{row['nombre_completo']} ({row['id_paciente']})" for i, row in df_p.iterrows()]
        lista_categorias = df_s['categoria'].unique().tolist()
        
        col_pac, col_doc = st.columns(2)
        paciente_sel = col_pac.selectbox("Seleccionar Paciente", lista_pacientes)
        doctor_sel = col_doc.radio("Médico Tratante (Para Nómina)", ["Dra. Mónica Rodríguez", "Dr. Emmanuel López"], horizontal=True)
        
        st.markdown("---")
        
        # Lógica de Tratamiento en Cascada
        c_cat, c_trat, c_diente = st.columns([1, 2, 1])
        cat_sel = c_cat.selectbox("Especialidad", lista_categorias)
        
        # Filtrar tratamientos por categoría
        tratamientos_disp = df_s[df_s['categoria'] == cat_sel]['nombre_tratamiento'].tolist()
        trat_sel = c_trat.selectbox("Tratamiento", tratamientos_disp)
        
        diente_sel = c_diente.selectbox("Diente / Zona", LISTA_DIENTES)
        
        # Obtener precios base
        fila_trat = df_s[(df_s['categoria'] == cat_sel) & (df_s['nombre_tratamiento'] == trat_sel)].iloc[0]
        precio_base = float(fila_trat['precio_lista'])
        costo_lab_base = float(fila_trat['costo_laboratorio_base'])
        
        st.markdown(f"**Precio de Lista:** ${precio_base:,.2f}")
        
        # Datos Financieros Editables
        with st.form("form_cobro"):
            f1, f2, f3 = st.columns(3)
            precio_final = f1.number_input("Precio Final Cobrado ($)", value=precio_base)
            
            # Switch de Laboratorio
            lleva_lab = f2.checkbox("¿Requiere Laboratorio?", value=(costo_lab_base > 0))
            costo_lab_real = f3.number_input("Costo Laboratorio ($)", value=costo_lab_base if lleva_lab else 0.0)
            
            # Detalles de Pago
            p1, p2, p3 = st.columns(3)
            metodo = p1.selectbox("Forma de Pago", ["Efectivo", "Tarjeta Crédito/Débito", "Transferencia"])
            estado_pago = p2.selectbox("Estado del Pago", ["Pagado Completo", "A cuenta (Deuda)", "No Pagado"])
            req_factura = p3.checkbox("¿Requiere Factura?")
            
            notas = st.text_area("Notas Clínicas / Garantía")
            
            if st.form_submit_button("💾 Registrar Movimiento"):
                # Cálculos automáticos
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                hora = datetime.now().strftime("%H:%M")
                id_cita = int(datetime.now().timestamp())
                
                # Descuento
                descuento_pct = 0
                if precio_final < precio_base:
                    descuento_pct = ((precio_base - precio_final) / precio_base) * 100
                
                # Utilidad Remanente
                utilidad = precio_final - costo_lab_real
                
                # --- REGLA DE ORO DE NÓMINA ---
                # Solo si el Dr. Emmanuel fue seleccionado Y NO es garantía (precio > 0)
                comision = 0
                if "Emmanuel" in doctor_sel and precio_final > 0:
                    comision = utilidad * 0.25
                
                # Preparar fila
                # Extraemos solo el nombre del paciente del string "Nombre (ID)"
                nombre_solo = paciente_sel.split(" (")[0]
                id_solo = paciente_sel.split("(")[1].replace(")", "")
                
                fila_guardar = [
                    id_cita, fecha_hoy, hora, id_solo, nombre_solo,
                    cat_sel, trat_sel, diente_sel, doctor_sel,
                    precio_base, precio_final, f"{descuento_pct:.1f}%",
                    "SÍ" if lleva_lab else "NO", costo_lab_real, utilidad,
                    metodo, estado_pago, "SÍ" if req_factura else "NO", notas
                ]
                
                guardar_fila(sheet, "citas", fila_guardar)
                
                # Feedback visual
                st.success("✅ Movimiento registrado correctamente")
                if comision > 0:
                    st.info(f"💰 Comisión generada para Dr. Emmanuel: ${comision:,.2f}")
                else:
                    st.warning("ℹ️ Este movimiento NO generó comisión (Dra. Mónica o Garantía).")
                st.balloons()

    # --- MÓDULO 4: FINANZAS Y NÓMINA (SOLO ADMIN) ---
    elif menu == "Finanzas & Nómina":
        if rol != "Admin":
            st.error("⛔ Acceso Denegado. Se requiere contraseña de Director.")
        else:
            st.header("📊 Tablero de Control Financiero")
            df_citas = cargar_datos(sheet, "citas")
            
            if df_citas.empty:
                st.info("No hay datos financieros aún.")
            else:
                # Conversión numérica segura
                for col in ['precio_final', 'costo_lab', 'utilidad_estimada']:
                     # Limpieza de datos por si hay texto
                     pass 
                
                # Resumen Global
                total_ingreso = pd.to_numeric(df_citas['precio_final'], errors='coerce').sum()
                total_lab = pd.to_numeric(df_citas['costo_lab'], errors='coerce').sum()
                utilidad_bruta = total_ingreso - total_lab
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Ventas Totales", f"${total_ingreso:,.2f}")
                k2.metric("Pagos a Laboratorios", f"-${total_lab:,.2f}")
                k3.metric("Utilidad Operativa", f"${utilidad_bruta:,.2f}", delta="Antes de Nómina")
                
                st.markdown("---")
                
                # --- NÓMINA DR. EMMANUEL ---
                st.subheader("👨‍⚕️ Nómina: Dr. Emmanuel López")
                
                # Filtramos solo sus trabajos
                df_emmanuel = df_citas[df_citas['doctor_atendio'].str.contains("Emmanuel", na=False)]
                
                if not df_emmanuel.empty:
                    # Recalculamos comisiones en vivo para exactitud
                    # (Precio Final - Costo Lab) * 0.25
                    df_emmanuel['Base Comisionable'] = pd.to_numeric(df_emmanuel['precio_final']) - pd.to_numeric(df_emmanuel['costo_lab'])
                    df_emmanuel['Comision'] = df_emmanuel['Base Comisionable'] * 0.25
                    
                    comision_total = df_emmanuel['Comision'].sum()
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Comisiones Acumuladas (Variable)", f"${comision_total:,.2f}")
                    
                    st.markdown("**Detalle de Tratamientos Dr. Emmanuel:**")
                    st.dataframe(df_emmanuel[['fecha', 'paciente', 'tratamiento', 'precio_final', 'costo_lab', 'Comision']])
                    
                    # Calculadora de Pago Final (Sumando días fijos)
                    st.markdown("#### 🧮 Calculadora de Cierre")
                    dias_trabajados = st.number_input("Días asistidos en el periodo:", min_value=0, value=6)
                    sueldo_fijo = dias_trabajados * 400
                    pago_total = sueldo_fijo + comision_total
                    
                    st.success(f"### TOTAL A PAGAR AL DR. EMMANUEL: ${pago_total:,.2f}")
                    st.caption(f"(Base ${sueldo_fijo} + Comisiones ${comision_total})")
                    
                else:
                    st.info("El Dr. Emmanuel no tiene tratamientos registrados en este periodo.")

    elif menu == "Configuración":
        st.info("Módulo de configuración de sistema.")

if __name__ == "__main__":
    main()
