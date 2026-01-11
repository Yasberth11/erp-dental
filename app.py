import streamlit as st
import pandas as pd
from datetime import datetime, date
import re

# --- 1. FUNCIONES AUXILIARES DE VALIDACIÓN Y CÁLCULO ---

def validar_email(email):
    """Verifica que el email tenga formato válido."""
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(patron, email):
        return True
    return False

def formatear_telefono(telefono):
    """
    Limpia el teléfono y lo formatea a xx-xxxx-xxxx.
    Si no tiene 10 dígitos, devuelve el original para que el usuario corrija.
    """
    # Eliminar todo lo que no sea número
    nums = re.sub(r'\D', '', str(telefono))
    
    if len(nums) == 10:
        return f"{nums[:2]}-{nums[2:6]}-{nums[6:]}"
    return telefono # Devuelve tal cual si no cumple longitud para que salte error manual

def calcular_edad(fecha_nacimiento_str):
    """Calcula edad soportando formatos DD/MM/YYYY y YYYY-MM-DD."""
    if not fecha_nacimiento_str or str(fecha_nacimiento_str).lower() == 'nan':
        return "Sin Dato"
    
    fecha_dt = None
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    
    for fmt in formatos:
        try:
            fecha_dt = datetime.strptime(str(fecha_nacimiento_str), fmt).date()
            break
        except ValueError:
            continue
            
    if fecha_dt:
        hoy = date.today()
        edad = hoy.year - fecha_dt.year - ((hoy.month, hoy.day) < (fecha_dt.month, fecha_dt.day))
        return f"{edad} Años"
    else:
        return "Error Formato"

# --- 2. INTERFAZ PRINCIPAL (Reemplaza tu lógica actual con esto) ---

# Título Principal y Estilos
st.title("🦷 Royal Dental - Sistema de Gestión")

# Menú Lateral
opcion = st.sidebar.radio("Menú", ["Agenda & Citas", "Gestión Pacientes", "Alta de Paciente", "Control Asistencia"])

# -----------------------------------------------------------------------------
# SECCIÓN: ALTA DE PACIENTE (Orden y Validaciones solicitadas)
# -----------------------------------------------------------------------------
if opcion == "Alta de Paciente":
    st.header("Alta de Nuevo Paciente")
    
    with st.form("form_alta_paciente"):
        # 1. Nombre Completo (Primer campo solicitado)
        nombre_completo = st.text_input("Nombre Completo (con Apellidos):")
        
        col_datos_1, col_datos_2 = st.columns(2)
        
        with col_datos_1:
            # 2. Teléfono (Segundo campo - salta aquí con Tab)
            telefono_input = st.text_input("Teléfono Móvil (10 dígitos):", placeholder="Ej: 5512345678")
            
            # 4. Fecha Nacimiento (Necesario para la Edad)
            fecha_nacimiento = st.date_input("Fecha de Nacimiento:", min_value=date(1920, 1, 1))

        with col_datos_2:
            # 3. Email (Tercer campo)
            email_input = st.text_input("Correo Electrónico:", placeholder="ejemplo@gmail.com")
            
            # Otros datos básicos
            sexo = st.selectbox("Sexo:", ["Masculino", "Femenino"])
        
        st.caption("Nota: Los datos fiscales se pueden agregar posteriormente en 'Gestión Pacientes'.")
        
        btn_guardar_paciente = st.form_submit_button("Registrar Paciente")
        
        if btn_guardar_paciente:
            errores = []
            
            # Validaciones
            if not nombre_completo:
                errores.append("El Nombre Completo es obligatorio.")
            
            # Validar y Formatear Teléfono
            tel_formateado = formatear_telefono(telefono_input)
            if len(re.sub(r'\D', '', tel_formateado)) != 10:
                errores.append("El teléfono debe tener 10 dígitos.")
                
            # Validar Email
            if not validar_email(email_input):
                errores.append("Por favor ingrese un correo electrónico válido (gmail, hotmail, outlook, etc.).")
                
            if errores:
                for error in errores:
                    st.error(error)
            else:
                # Preparar datos para Google Sheets
                # Asegúrate que tu función add_data soporte este diccionario
                nuevo_paciente = {
                    "Nombre Completo": nombre_completo,
                    "Teléfono": tel_formateado,
                    "Email": email_input,
                    "Fecha Nacimiento": str(fecha_nacimiento),
                    "Sexo": sexo,
                    "Deuda": 0.0, # Inicializamos deuda en 0
                    "Fecha Alta": str(date.today())
                }
                
                # AQUÍ LLAMAS A TU FUNCIÓN EXISTENTE DE GUARDADO
                # add_data("Pacientes", nuevo_paciente) 
                
                st.success(f"Paciente {nombre_completo} registrado correctamente.")
                st.info(f"Teléfono guardado con formato: {tel_formateado}")

# -----------------------------------------------------------------------------
# SECCIÓN: GESTIÓN PACIENTES (Búsqueda, Corrección Edad, Fiscales y Pagos)
# -----------------------------------------------------------------------------
elif opcion == "Gestión Pacientes":
    st.header("Expediente y Gestión")
    
    # Cargar datos
    try:
        df_pacientes = get_data("Pacientes") # Tu función
        lista_nombres = df_pacientes['Nombre Completo'].tolist()
        lista_busqueda = [f"{row['Nombre Completo']} - {row['Teléfono']}" for i, row in df_pacientes.iterrows()]
    except:
        st.error("No se pudo conectar con la base de datos de Pacientes.")
        lista_busqueda = []

    seleccion = st.selectbox("Buscar Paciente:", ["Seleccionar..."] + lista_busqueda)
    
    if seleccion != "Seleccionar...":
        # Extraer el nombre real del string de búsqueda
        nombre_real = seleccion.split(" - ")[0]
        datos = df_pacientes[df_pacientes['Nombre Completo'] == nombre_real].iloc[0]
        
        # --- TARJETA VISUAL DEL PACIENTE ---
        st.markdown("---")
        col_foto, col_info = st.columns([1, 3])
        
        with col_foto:
            # Icono genérico dependiendo del sexo si existe la columna, si no, genérico
            icono = "👤"
            if 'Sexo' in datos and datos['Sexo'] == 'Femenino':
                icono = "👩"
            st.markdown(f"<h1 style='text-align: center;'>{icono}</h1>", unsafe_allow_html=True)
            
        with col_info:
            st.subheader(datos['Nombre Completo'])
            
            # --- CORRECCIÓN DEL ERROR DE LA EDAD ---
            fecha_nac = datos.get('Fecha Nacimiento', '')
            edad_str = calcular_edad(fecha_nac)
            st.metric("Edad", value=edad_str) # Aquí ya no saldrá "N/A" feo
            
            st.write(f"**Tel:** {datos.get('Teléfono', 'S/D')} | **Email:** {datos.get('Email', 'S/D')}")
            
            rfc_val = datos.get('RFC', 'Sin RFC')
            st.write(f"**RFC:** {rfc_val}")

        # --- PESTAÑAS DE ACCIÓN ---
        tab1, tab2, tab3 = st.tabs(["📝 Modificar / Fiscal", "💰 Pagos y Deudas", "🦷 Tratamientos"])
        
        # 1. MODIFICAR DATOS + DATOS FISCALES
        with tab1:
            with st.form("form_update"):
                c1, c2 = st.columns(2)
                with c1:
                    new_tel = st.text_input("Teléfono:", value=datos.get('Teléfono',''))
                    new_email = st.text_input("Email:", value=datos.get('Email',''))
                with c2:
                    new_nac = st.text_input("Fecha Nac (YYYY-MM-DD):", value=datos.get('Fecha Nacimiento',''))
                
                st.markdown("### Datos Fiscales")
                cf1, cf2 = st.columns(2)
                with cf1:
                    new_rfc = st.text_input("RFC:", value=datos.get('RFC',''))
                    new_razon = st.text_input("Razón Social:", value=datos.get('Razón Social',''))
                with cf2:
                    new_cp = st.text_input("CP Fiscal:", value=datos.get('CP Fiscal',''))
                    new_regimen = st.selectbox("Régimen Fiscal:", ["Sueldos y Salarios", "Persona Física Actividad Empresarial", "RESICO", "Gastos General"], index=0)

                btn_update = st.form_submit_button("Guardar Cambios")
                if btn_update:
                    # Lógica de actualización (Agrega columnas RFC, Razón Social, etc. a tu sheet si no existen)
                    # update_patient_data(...)
                    st.success("Datos actualizados correctamente.")

        # 2. PAGOS Y DEUDAS (Lo que pediste sobre abonos)
        with tab2:
            deuda_act = float(str(datos.get('Deuda', 0)).replace(',','')) if datos.get('Deuda') else 0.0
            
            col_deuda, col_abono = st.columns(2)
            with col_deuda:
                st.metric(label="Deuda Total Pendiente", value=f"${deuda_act:,.2f}", delta_color="inverse")
            
            with col_abono:
                st.write("**Registrar Abono / Pago**")
                monto_abono = st.number_input("Monto a Pagar:", min_value=0.0, step=50.0)
                if st.button("Registrar Pago"):
                    if monto_abono > 0:
                        nueva_deuda = deuda_act - monto_abono
                        if nueva_deuda < 0:
                            st.warning("El abono excede la deuda. Revise el monto.")
                        else:
                            # update_field("Pacientes", nombre_real, "Deuda", nueva_deuda)
                            st.success(f"Pago de ${monto_abono} registrado. Restante: ${nueva_deuda}")
                            st.rerun() # Recarga la página para ver cambios
                    else:
                        st.warning("Ingrese un monto mayor a 0")

        with tab3:
            st.write("Historial clínico del paciente...")
            # Aquí tu lógica de historial

# -----------------------------------------------------------------------------
# SECCIÓN: AGENDA Y CITAS (Corrección del Selectbox)
# -----------------------------------------------------------------------------
elif opcion == "Agenda & Citas":
    st.header("Control de Agenda")
    
    tab_ag1, tab_ag2 = st.tabs(["Ver Agenda", "Modificar Cita"])
    
    with tab_ag1:
        st.write("Vista de calendario (Tu código actual de calendario)")
        # show_calendar() ...
    
    with tab_ag2:
        st.subheader("Reagendar Cita")
        df_citas = get_data("Agenda")
        
        if not df_citas.empty:
            # CREAMOS UNA LISTA LEGIBLE: FECHA | HORA | PACIENTE
            opciones_citas = [
                f"{row['Fecha']} | {row['Hora']} | {row['Paciente']}" 
                for index, row in df_citas.iterrows()
            ]
            
            cita_str = st.selectbox("Seleccione la cita a mover:", opciones_citas)
            
            if cita_str:
                # Recuperar datos para el formulario
                parts = cita_str.split(" | ")
                fecha_ref = parts[0]
                hora_ref = parts[1]
                
                with st.form("form_reagendar"):
                    st.write(f"Modificando cita de: **{parts[2]}** actual el {fecha_ref} a las {hora_ref}")
                    
                    c_f, c_h = st.columns(2)
                    with c_f:
                        n_fecha = st.date_input("Nueva Fecha")
                    with c_h:
                        n_hora = st.selectbox("Nueva Hora", ["09:00", "09:30", "10:00", "10:30", "11:00", "16:00", "17:00"])
                        
                    btn_cambio_cita = st.form_submit_button("Confirmar Cambio")
                    
                    if btn_cambio_cita:
                        # lógica de update
                        st.success(f"Cita movida al {n_fecha} a las {n_hora}")
