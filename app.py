import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import pytz
import re
import time
import random
import string

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO ROYAL
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
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius: 8px; background-color: #FFFFFF; border: 1px solid #D1D1D1; }
        
        /* Semáforos Financieros */
        .semaforo-verde { background-color: #D4EDDA; color: #155724; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8em; }
        .semaforo-amarillo { background-color: #FFF3CD; color: #856404; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8em; }
        .semaforo-rojo { background-color: #F8D7DA; color: #721c24; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8em; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilo_royal()

# ==========================================
# 2. CONEXIÓN DB (CACHE INTELIGENTE)
# ==========================================
# Aumentamos el TTL a 10s para evitar recargas constantes que "sacan" al usuario
@st.cache_resource(ttl=10)
def get_database_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client.open("ERP_DENTAL_DB")

try:
    db = get_database_connection()
    sheet_pacientes = db.worksheet("pacientes")
    sheet_citas = db.worksheet("citas")
    sheet_asistencia = db.worksheet("asistencia")
    sheet_servicios = db.worksheet("servicios")
except Exception as e:
    st.error(f"❌ Error Crítico de Conexión: {e}")
    st.stop()

# ==========================================
# 3. HELPERS & LÓGICA FINANCIERA
# ==========================================
def get_fecha_mx(): return datetime.now(TZ_MX).strftime("%Y-%m-%d")
def get_hora_mx(): return datetime.now(TZ_MX).strftime("%H:%M:%S")

def calcular_edad_completa(nacimiento):
    hoy = datetime.now().date()
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    tipo = "MENOR DE EDAD" if edad < 18 else "ADULTO"
    return edad, tipo

def generar_id_unico(nombre, paterno, nacimiento):
    try:
        part1 = paterno[:3].upper() if len(paterno) >=3 else paterno.upper() + "X"
        part2 = nombre[0].upper()
        part3 = str(nacimiento.year)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"{part1}{part2}-{part3}-{random_chars}"
    except:
        return f"P-{int(time.time())}"

def formatear_telefono(numero):
    # Elimina todo lo que no sea dígito
    return re.sub(r'\D', '', str(numero))

def generar_slots_tiempo():
    slots = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("18:30", "%H:%M")
    while hora_actual <= hora_fin:
        slots.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return slots

def get_regimenes_fiscales():
    return [
        "605 - Sueldos y Salarios", 
        "612 - Personas Físicas con Actividades Empresariales", 
        "626 - RESICO", 
        "616 - Sin obligaciones fiscales", 
        "601 - General de Ley Personas Morales"
    ]

def get_usos_cfdi():
    return ["D01 - Honorarios médicos, dentales", "S01 - Sin efectos fiscales", "G03 - Gastos en general", "CP01 - Pagos"]

# ==========================================
# 4. LOGICA ASISTENCIA
# ==========================================
def registrar_movimiento(doctor, tipo):
    try:
        data = sheet_asistencia.get_all_records()
        df = pd.DataFrame(data)
        hoy = get_fecha_mx()
        hora_actual = get_hora_mx()
        
        # Normalizar columnas
        if not df.empty:
            df['fecha'] = df['fecha'].astype(str)
            df['doctor'] = df['doctor'].astype(str)
            df['hora_salida'] = df['hora_salida'].astype(str)

        if tipo == "Entrada":
            if not df.empty:
                check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
                if not check.empty: return False, "Ya tienes una sesión abierta."
            
            nuevo_id = int(time.time())
            row = [nuevo_id, hoy, doctor, hora_actual, "", "", "Pendiente"]
            sheet_asistencia.append_row(row)
            return True, f"Entrada: {hora_actual}"
            
        elif tipo == "Salida":
            if df.empty: return False, "No hay registros."
            check = df[(df['fecha'] == hoy) & (df['doctor'] == doctor) & (df['hora_salida'] == "")]
            if check.empty: return False, "No encontré entrada abierta hoy."
            
            id_reg = check.iloc[-1]['id_registro']
            entrada = check.iloc[-1]['hora_entrada']
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(hora_actual, fmt) - datetime.strptime(entrada, fmt)
            horas = round(tdelta.total_seconds() / 3600, 2)
            
            cell = sheet_asistencia.find(str(id_reg))
            sheet_asistencia.update_cell(cell.row, 5, hora_actual)
            sheet_asistencia.update_cell(cell.row, 6, horas)
            return True, f"Salida: {hora_actual} ({horas}h)"
            
    except Exception as e: return False, str(e)

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
    
    menu = st.sidebar.radio("Menú", 
        ["1. Agenda & Citas", "2. Gestión Pacientes", "3. Planes de Tratamiento", "4. Control Asistencia"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.perfil = None; st.rerun()

    # ------------------------------------
    # MÓDULO 1: AGENDA (CON CITA PROSPECTO)
    # ------------------------------------
    if menu == "1. Agenda & Citas":
        st.title("📅 Agenda del Consultorio")
        col_cal1, col_cal2 = st.columns([1, 2.5])
        
        with col_cal1:
            st.markdown("### 📆 Calendario")
            fecha_ver = st.date_input("Seleccionar Fecha", datetime.now(TZ_MX))
            st.markdown("---")
            
            tab_reg, tab_new = st.tabs(["Paciente Registrado", "Prospecto/Nuevo"])
            
            with tab_reg:
                # Usamos form para evitar recargas constantes
                with st.form("cita_registrada"):
                    # Optimización: Cargar pacientes solo una vez
                    pacientes_raw = sheet_pacientes.get_all_records()
                    lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw] if pacientes_raw else []
                    
                    p_sel = st.selectbox("Paciente", ["Seleccionar..."] + lista_pac)
                    h_sel = st.selectbox("Hora", generar_slots_tiempo())
                    m_sel = st.text_input("Motivo", "Revisión / Continuación")
                    d_sel = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Agendar Paciente"):
                        if p_sel != "Seleccionar...":
                            id_p = p_sel.split(" - ")[0]
                            nom_p = p_sel.split(" - ")[1]
                            # Columnas Base + 3 Nuevas Financieras (Pagado, Saldo, FechaPago)
                            row = [int(time.time()), str(fecha_ver), h_sel, id_p, nom_p, "General", m_sel, "", d_sel, 0, 0, 0, "No", 0, 0, "N/A", "Pendiente", "No", "", 0, 0, ""]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita Agendada")
                            time.sleep(1); st.rerun()
                        else: st.error("Seleccione un paciente")

            with tab_new:
                st.caption("Pacientes sin expediente (Solo revisión).")
                with st.form("cita_prospecto"):
                    nombre_pros = st.text_input("Nombre Completo")
                    # Restricción de caracteres visual (aunque validamos abajo)
                    tel_pros = st.text_input("Teléfono", max_chars=10, help="Solo 10 números")
                    hora_pros = st.selectbox("Hora", generar_slots_tiempo())
                    motivo_pros = st.text_input("Motivo", "Revisión (Primera Vez)")
                    precio_pros = st.number_input("Costo Estimado", value=100.0)
                    doc_pros = st.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                    
                    if st.form_submit_button("Agendar Prospecto"):
                        if nombre_pros and len(tel_pros) == 10:
                            id_temp = f"PROSPECTO-{int(time.time())}"
                            # Agregamos 0, precio_pros, fecha_hoy a las nuevas columnas financieras
                            row = [
                                int(time.time()), str(fecha_ver), hora_pros, id_temp, nombre_pros, 
                                "Primera Vez", motivo_pros, "", doc_pros, 
                                precio_pros, precio_pros, 0, "No", 0, precio_pros, "Efectivo", "Pendiente", "No", f"Tel: {tel_pros}",
                                0, precio_pros, "" # Nuevas columnas: Pagado=0, Saldo=Total, Fecha=""
                            ]
                            sheet_citas.append_row(row)
                            st.success("✅ Cita de Prospecto Agendada")
                            time.sleep(1); st.rerun()
                        else:
                            st.error("Nombre obligatorio y Teléfono debe ser de 10 dígitos")

        with col_cal2:
            st.markdown(f"#### 📋 Programación: {fecha_ver}")
            try:
                citas_data = sheet_citas.get_all_records()
                df_c = pd.DataFrame(citas_data)
                
                if not df_c.empty:
                    df_c['fecha'] = df_c['fecha'].astype(str)
                    df_dia = df_c[df_c['fecha'] == str(fecha_ver)]
                    
                    slots = generar_slots_tiempo()
                    for slot in slots:
                        ocupado = df_dia[df_dia['hora'].astype(str).str.contains(slot)]
                        if ocupado.empty:
                            st.markdown(f"""<div style="padding:8px; border-bottom:1px solid #eee; display:flex; align-items:center;"><span style="font-weight:bold; color:#aaa; width:60px;">{slot}</span><span style="color:#ddd; font-size:0.9em;">Disponible</span></div>""", unsafe_allow_html=True)
                        else:
                            for _, r in ocupado.iterrows():
                                es_prospecto = "PROSPECTO" in str(r['id_paciente'])
                                color = "#FF5722" if es_prospecto else "#002B5B"
                                st.markdown(f"""
                                <div style="padding:10px; margin-bottom:5px; background-color:#fff; border-left:5px solid {color}; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:4px;">
                                    <b>{slot} | {r['nombre_paciente']}</b><br>
                                    <span style="color:#666; font-size:0.9em;">{r['tratamiento']} - {r['doctor_atendio']}</span>
                                </div>
                                """, unsafe_allow_html=True)
            except: st.warning("Error leyendo agenda.")

    # ------------------------------------
    # MÓDULO 2: PACIENTES (ESTABILIDAD TOTAL)
    # ------------------------------------
    elif menu == "2. Gestión Pacientes":
        st.title("🦷 Expediente Clínico")
        
        tab_b, tab_n = st.tabs(["🔍 BUSCAR", "➕ NUEVO (ALTA)"])
        
        with tab_b:
            pacientes_raw = sheet_pacientes.get_all_records()
            if not pacientes_raw: st.warning("Sin pacientes")
            else:
                lista_busqueda = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes_raw]
                seleccion = st.selectbox("Seleccionar:", ["Buscar..."] + lista_busqueda)
                
                if seleccion != "Buscar...":
                    id_sel_str = seleccion.split(" - ")[0]
                    p_data = next((p for p in pacientes_raw if str(p['id_paciente']) == id_sel_str), None)
                    if p_data:
                        try:
                            f_obj = datetime.strptime(p_data['fecha_nacimiento'], "%Y-%m-%d").date()
                            edad, tipo_pac = calcular_edad_completa(f_obj)
                        except: edad, tipo_pac = "N/A", ""

                        st.markdown(f"""
                        <div class="royal-card">
                            <h3>👤 {p_data['nombre']} {p_data['apellido_paterno']}</h3>
                            <span style="background-color:#002B5B; color:white; padding:4px 8px; border-radius:4px;">{edad} Años - {tipo_pac}</span>
                            <br><br><b>Tel:</b> {p_data['telefono']} | <b>Email:</b> {p_data['email']}
                            <br><b>RFC:</b> {p_data['rfc']}
                        </div>
                        """, unsafe_allow_html=True)
        
        with tab_n:
            st.markdown("#### Formulario de Alta")
            
            # BLOQUEO DE RECARGA: Todo dentro de un form estático
            with st.form("alta_paciente_static", clear_on_submit=True):
                c_nom, c_pat, c_mat = st.columns(3)
                nombre = c_nom.text_input("Nombre(s)")
                paterno = c_pat.text_input("Apellido Paterno")
                materno = c_mat.text_input("Apellido Materno")
                
                c_nac, c_tel, c_mail = st.columns(3)
                nacimiento = c_nac.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1), max_value=datetime.now())
                # RESTRICCIÓN FÍSICA DE 10 DIGITOS
                tel = c_tel.text_input("Teléfono (10 dígitos)", max_chars=10, help="Solo números. Máximo 10.")
                email = c_mail.text_input("Email")
                
                st.markdown("---")
                requiere_factura = st.checkbox("¿Requiere Factura? (Activar para llenar datos)")
                
                # Nota: Dentro de un form, la interactividad es limitada. 
                # Si activan el checkbox, los campos se mostrarán vacíos o se llenarán al enviar.
                # Para mejor UX en forms estáticos, mostramos los campos siempre pero indicamos opcionalidad.
                st.caption("Datos Fiscales (Llenar solo si requiere factura)")
                c_f1, c_f2 = st.columns(2)
                rfc = c_f1.text_input("RFC")
                cp = c_f2.text_input("C.P.")
                regimen = st.selectbox("Régimen Fiscal", get_regimenes_fiscales())
                uso = st.selectbox("Uso CFDI", get_usos_cfdi())
                
                if st.form_submit_button("💾 GUARDAR PACIENTE"):
                    errores = []
                    
                    # Validación Estricta
                    if not tel.isdigit() or len(tel) != 10:
                        errores.append("❌ El teléfono debe contener EXACTAMENTE 10 números.")
                    if not nombre or not paterno:
                        errores.append("❌ Nombre y Apellido son obligatorios.")
                        
                    if errores:
                        for e in errores: st.error(e)
                    else:
                        # Lógica Fiscal
                        rfc_final = rfc if requiere_factura and rfc else "XAXX010101000"
                        cp_final = cp if requiere_factura else "N/A"
                        reg_final = regimen if requiere_factura else "616 - Sin obligaciones fiscales"
                        uso_final = uso if requiere_factura else "S01 - Sin efectos fiscales"
                        
                        nuevo_id = generar_id_unico(nombre, paterno, nacimiento)
                        fecha_reg = get_fecha_mx()
                        tel_fmt = f"{tel[:2]}-{tel[2:6]}-{tel[6:]}"
                        
                        row = [
                            nuevo_id, fecha_reg, nombre, paterno, materno, tel_fmt, email, 
                            rfc_final, reg_final.split(" - ")[0], uso_final.split(" - ")[0], cp_final, 
                            f"Nac: {nacimiento}", "", "Activo", ""
                        ]
                        sheet_pacientes.append_row(row)
                        st.success(f"✅ Paciente guardado con éxito. ID: {nuevo_id}")
                        time.sleep(1.5); st.rerun()

    # ------------------------------------
    # MÓDULO 3: FINANZAS Y TRATAMIENTOS (SEMÁFORO)
    # ------------------------------------
    elif menu == "3. Planes de Tratamiento":
        st.title("💰 Planes de Tratamiento & Finanzas")
        
        # Cargar Datos
        try:
            pacientes = sheet_pacientes.get_all_records()
            servicios = pd.DataFrame(sheet_servicios.get_all_records())
            # Cargamos Citas para ver deudas anteriores
            citas_raw = sheet_citas.get_all_records()
            df_finanzas = pd.DataFrame(citas_raw)
        except: 
            st.error("Error cargando base de datos.")
            st.stop()
            
        lista_pac = [f"{str(p['id_paciente'])} - {p['nombre']} {p['apellido_paterno']}" for p in pacientes]
        seleccion_pac = st.selectbox("Seleccionar Paciente:", ["Buscar..."] + lista_pac)
        
        if seleccion_pac != "Buscar...":
            id_p = seleccion_pac.split(" - ")[0]
            nom_p = seleccion_pac.split(" - ")[1]
            
            # --- SEMÁFORO DE PAGOS DEL PACIENTE ---
            st.markdown(f"### 🚦 Estado de Cuenta: {nom_p}")
            if not df_finanzas.empty:
                # Filtrar historial del paciente
                historial = df_finanzas[df_finanzas['id_paciente'].astype(str) == id_p]
                
                if not historial.empty:
                    # Asegurar columnas numéricas nuevas
                    # Si las columnas no existen en el DF (porque acabas de crearlas en Sheets), rellenar con 0
                    if 'saldo_pendiente' not in historial.columns: historial['saldo_pendiente'] = 0
                    
                    deuda_total = pd.to_numeric(historial['saldo_pendiente'], errors='coerce').fillna(0).sum()
                    
                    col_sem1, col_sem2, col_sem3 = st.columns(3)
                    col_sem1.metric("Deuda Total", f"${deuda_total:,.2f}")
                    
                    if deuda_total == 0:
                        col_sem2.success("✅ CLIENTE AL CORRIENTE")
                    else:
                        # Calcular días de morosidad del cargo más antiguo con saldo
                        pendientes = historial[pd.to_numeric(historial['saldo_pendiente'], errors='coerce') > 0]
                        if not pendientes.empty:
                            fecha_cargo = pd.to_datetime(pendientes.iloc[0]['fecha'], errors='coerce')
                            dias_retraso = (datetime.now() - fecha_cargo).days
                            
                            if dias_retraso < 7:
                                col_sem2.warning(f"⚠️ PAGO PENDIENTE ({dias_retraso} días)")
                            else:
                                col_sem2.error(f"🚨 MOROSO ({dias_retraso} días de retraso)")
                        else:
                            col_sem2.success("✅ AL CORRIENTE")
                            
            st.markdown("---")
            
            # --- COTIZADOR ---
            st.subheader("Nuevo Tratamiento")
            
            # Selectores fuera de form para dinamismo
            c1, c2, c3 = st.columns(3)
            
            cat_sel = "General"
            trat_sel = ""
            precio_lista = 0.0
            
            if not servicios.empty and 'categoria' in servicios.columns:
                cats = servicios['categoria'].unique()
                cat_sel = c1.selectbox("Categoría", cats)
                filt = servicios[servicios['categoria'] == cat_sel]
                trat_sel = c2.selectbox("Tratamiento", filt['nombre_tratamiento'].unique())
                item = filt[filt['nombre_tratamiento'] == trat_sel].iloc[0]
                precio_lista = float(item.get('precio_lista', 0))
            else:
                trat_sel = c2.text_input("Tratamiento Manual")
                precio_lista = c3.number_input("Precio Lista", 0.0)
                
            c3.metric("Precio de Lista", f"${precio_lista:,.2f}")
            
            with st.form("form_finanzas"):
                col_f1, col_f2 = st.columns(2)
                precio_final = col_f1.number_input("Precio Final a Cobrar", value=precio_lista)
                
                # LÓGICA SOBRECOSTO
                nota_sobrecosto = ""
                descuento = 0.0
                pct = 0.0
                
                if precio_final > precio_lista:
                    st.warning("⚠️ El precio final es mayor al de lista. El descuento será 0 y se anotará el sobrecosto.")
                    nota_sobrecosto = " (SOBRECOSTO APLICADO)"
                    descuento = 0.0
                else:
                    descuento = precio_lista - precio_final
                    pct = (descuento / precio_lista * 100) if precio_lista > 0 else 0
                    st.caption(f"Descuento: ${descuento:,.2f} ({pct:.1f}%)")
                
                abono = col_f2.number_input("Abono Inicial", min_value=0.0, max_value=precio_final)
                
                saldo = precio_final - abono
                estatus = "Pagado" if saldo <= 0 else "Pendiente"
                
                st.info(f"💵 Saldo Pendiente: ${saldo:,.2f}")
                
                c_d1, c_d2 = st.columns(2)
                doctor = c_d1.selectbox("Doctor", ["Dr. Emmanuel", "Dra. Mónica"])
                diente = c_d2.number_input("Diente (ISO)", 0, help="Sistema FDI (Ej. 11, 48). 0 para General.")
                st.caption("Nota: Diente (ISO) es el estándar internacional usado por dentistas.")
                
                metodo = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                
                if st.form_submit_button("💾 REGISTRAR"):
                    # Columnas nuevas: 20, 21, 22
                    fecha_pago = get_fecha_mx() if abono > 0 else ""
                    
                    row = [
                        int(time.time()), str(get_fecha_mx()), get_hora_mx(), id_p, nom_p,
                        cat_sel, trat_sel, diente, doctor,
                        precio_lista, precio_final, pct, "No", 0, (precio_final*0.4),
                        metodo, estatus, "No", f"Nota: {nota_sobrecosto}",
                        abono, saldo, fecha_pago
                    ]
                    sheet_citas.append_row(row)
                    st.success("Tratamiento registrado con control financiero.")
                    time.sleep(1.5); st.rerun()

    # ------------------------------------
    # MÓDULO 4: ASISTENCIA
    # ------------------------------------
    elif menu == "4. Control Asistencia":
        st.title("⏱️ Reloj Checador")
        col1, col2 = st.columns([1,3])
        with col1:
            st.markdown("### 👨‍⚕️ Dr. Emmanuel")
            c_a, c_b = st.columns(2)
            if c_a.button("🟢 ENTRADA"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Entrada")
                if ok: st.success(m)
                else: st.warning(m)
            if c_b.button("🔴 SALIDA"):
                ok, m = registrar_movimiento("Dr. Emmanuel", "Salida")
                if ok: st.success(m)
                else: st.warning(m)

if __name__ == "__main__":
    if st.session_state.perfil is None:
        pantalla_login()
    elif st.session_state.perfil == "Consultorio":
        vista_consultorio()
    elif st.session_state.perfil == "Administracion":
        st.title("Panel Director")
        if st.button("Salir"): st.session_state.perfil=None; st.rerun()
