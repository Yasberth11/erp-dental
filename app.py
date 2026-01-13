"""
ROYAL DENTAL ERP - MÓDULO CONSULTORIO (V4.0)
==========================================================
CONTROL DE CAMBIOS:
[v4.0] - 12/01/2026:
         - Carga masiva del Catálogo de Tratamientos (29 items).
         - NUEVA LÓGICA FINANCIERA: Comisión sobre UTILIDAD (Precio - Lab).
         - Interfaz de Caja muestra desglose de Costo Lab.
         - Auditoría y Edición de Pacientes 100% funcionales.
==========================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time

# ==========================================
# 1. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="Royal Dental ERP", page_icon="🦷", layout="wide", initial_sidebar_state="collapsed")

def cargar_estilos():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .stApp { background-color: #f4f6f8; }
        .css-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 6px solid #004e92; margin-bottom: 20px; }
        .stButton>button { background-color: #004e92; color: white; border-radius: 8px; font-weight: bold; border: none; }
        .stButton>button:hover { background-color: #003366; color: #d4af37; }
        div[data-testid="stMetricValue"] { color: #004e92; }
        /* Inputs numéricos alineados */
        input[type=number] { text-align: right; }
        </style>
    """, unsafe_allow_html=True)

cargar_estilos()

# ==========================================
# 2. BASE DE DATOS Y SEEDING (CARGA INICIAL)
# ==========================================
DB_NAME = 'royal_dental_v4.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tablas Principales
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente TEXT PRIMARY KEY,
        fecha_registro TEXT,
        nombre TEXT,
        apellido_paterno TEXT,
        apellido_materno TEXT,
        telefono TEXT,
        email TEXT,
        rfc TEXT,
        regimen TEXT,
        fecha_nacimiento TEXT
    )''')
    
    # Tabla Pagos con soporte para Costo de Laboratorio
    c.execute('''CREATE TABLE IF NOT EXISTS pagos (
        id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_pago TEXT,
        id_paciente TEXT,
        concepto TEXT,
        monto_cobrado REAL,
        costo_laboratorio REAL,
        utilidad_real REAL,
        metodo_pago TEXT,
        doctor_realizo TEXT,
        comision_doctor REAL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bitacora_seguridad (
        id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_evento TEXT,
        usuario_responsable TEXT,
        accion TEXT,
        detalle TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tratamientos (
        id_tratamiento INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        nombre_tratamiento TEXT,
        precio_lista REAL,
        costo_laboratorio_base REAL
    )''')
    
    conn.commit()
    conn.close()

def seed_data():
    """Carga el catálogo de tratamientos proporcionado por el usuario."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM tratamientos")
    if c.fetchone()[0] == 0:
        # LISTA PROPORCIONADA (Categoria, Nombre, Precio, CostoLab)
        tratamientos_data = [
            ("Preventiva", "Profilaxis (Limpieza Ultrasónica)", 600.0, 0.0),
            ("Preventiva", "Aplicación de Flúor (Niños)", 350.0, 0.0),
            ("Preventiva", "Sellador de Fosetas y Fisuras", 400.0, 0.0),
            ("Operatoria", "Resina Simple (1 cara)", 800.0, 0.0),
            ("Operatoria", "Resina Compuesta (2 o más caras)", 1200.0, 0.0),
            ("Operatoria", "Reconstrucción de Muñón", 1500.0, 0.0),
            ("Operatoria", "Curación Temporal (Cavit)", 300.0, 0.0),
            ("Cirugía", "Extracción Simple", 900.0, 0.0),
            ("Cirugía", "Cirugía de Tercer Molar (Muela del Juicio)", 3500.0, 0.0),
            ("Cirugía", "Drenaje de Absceso", 800.0, 0.0),
            ("Endodoncia", "Endodoncia Anterior (1 conducto)", 2800.0, 0.0),
            ("Endodoncia", "Endodoncia Premolar (2 conductos)", 3200.0, 0.0),
            ("Endodoncia", "Endodoncia Molar (3+ conductos)", 4200.0, 0.0),
            ("Prótesis Fija", "Corona Zirconia", 4800.0, 900.0),
            ("Prótesis Fija", "Corona Metal-Porcelana", 3500.0, 600.0),
            ("Prótesis Fija", "Incrustación Estética", 3800.0, 700.0),
            ("Prótesis Fija", "Carilla de Porcelana", 5500.0, 1100.0),
            ("Prótesis Fija", "Poste de Fibra de Vidrio", 1200.0, 0.0),
            ("Prótesis Removible", "Placa Total (Acrílico) - Una arcada", 6000.0, 1200.0),
            ("Prótesis Removible", "Prótesis Flexible (Valplast) - Unilateral", 4500.0, 900.0),
            ("Estética", "Blanqueamiento (Consultorio 2 sesiones)", 3500.0, 300.0),
            ("Estética", "Blanqueamiento (Guardas en casa)", 2500.0, 500.0),
            ("Ortodoncia", "Pago Inicial (Brackets Metálicos)", 4000.0, 1500.0),
            ("Ortodoncia", "Mensualidad Ortodoncia", 700.0, 0.0),
            ("Ortodoncia", "Recolocación de Bracket (Reposición)", 200.0, 0.0),
            ("Pediatría", "Pulpotomía", 1500.0, 0.0),
            ("Pediatría", "Corona Acero-Cromo", 1800.0, 0.0),
            ("Garantía", "Garantía (Retoque/Reparación)", 0.0, 0.0)
        ]
        c.executemany("INSERT INTO tratamientos (categoria, nombre_tratamiento, precio_lista, costo_laboratorio_base) VALUES (?,?,?,?)", tratamientos_data)
        conn.commit()
    conn.close()

# Ejecutar inicialización
init_db()
seed_data()

# ==========================================
# 3. LÓGICA DE NEGOCIO Y AUDITORÍA
# ==========================================

def registrar_auditoria(usuario, accion, detalle):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO bitacora_seguridad (fecha_evento, usuario_responsable, accion, detalle) VALUES (?,?,?,?)",
                  (fecha, usuario, accion, detalle))
        conn.commit()
        conn.close()
    except: pass

def registrar_pago_inteligente(id_p, concepto, monto_cobrado, costo_lab, metodo, doc, usuario_actual):
    conn = get_db_connection()
    c = conn.cursor()
    
    # --- FORMULA MAESTRA DE UTILIDAD ---
    # Utilidad = Lo que paga el paciente - Lo que nos cobra el laboratorio
    utilidad = monto_cobrado - costo_lab
    
    # Si la utilidad es negativa (pérdida), la comisión es 0 (no se cobra comisión sobre pérdidas)
    if utilidad < 0: utilidad = 0
    
    # Comisión del 25% sobre la UTILIDAD, no sobre el total
    comision = utilidad * 0.25
    
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''INSERT INTO pagos (fecha_pago, id_paciente, concepto, monto_cobrado, costo_laboratorio, utilidad_real, metodo_pago, doctor_realizo, comision_doctor)
                 VALUES (?,?,?,?,?,?,?,?,?)''', 
                 (fecha, id_p, concepto, monto_cobrado, costo_lab, utilidad, metodo, doc, comision))
    conn.commit()
    conn.close()
    
    # Auditoría
    registrar_auditoria(usuario_actual, "COBRO CAJA", f"Cobro: ${monto_cobrado}. Lab: ${costo_lab}. Comision {doc}: ${comision}")
    return comision, utilidad

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================

def login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login"):
            st.markdown("<h2 style='text-align: center; color: #004e92;'>🔐 Royal Dental</h2>", unsafe_allow_html=True)
            user = st.selectbox("Usuario", ["Seleccionar...", "Dr. Emmanuel", "Dra. Mónica", "Administrador"])
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ENTRAR"):
                if pwd == "1234": 
                    st.session_state.logged_in = True
                    st.session_state.usuario = user
                    st.rerun()
                else: st.error("Acceso denegado")

def main_app():
    with st.sidebar:
        st.title(f"👤 {st.session_state.usuario}")
        menu = st.radio("Menú", ["👥 Pacientes", "💰 Caja", "📊 Reportes", "🛡️ Auditoría"])
        st.markdown("---")
        if st.button("Salir"):
            st.session_state.logged_in = False
            st.rerun()

    # --- MÓDULO PACIENTES ---
    if menu == "👥 Pacientes":
        st.title("Gestión de Expedientes")
        tab1, tab2, tab3 = st.tabs(["🔍 Directorio", "➕ Alta Nueva", "✏️ Editar"])
        
        conn = get_db_connection()
        
        with tab1:
            q = st.text_input("Buscar paciente:")
            query = f"SELECT id_paciente, nombre, apellido_paterno, telefono FROM pacientes WHERE nombre LIKE '%{q}%' OR apellido_paterno LIKE '%{q}%'"
            df = pd.read_sql(query, conn)
            st.dataframe(df, use_container_width=True)
            
        with tab2:
            with st.form("alta"):
                c1, c2 = st.columns(2)
                nom = c1.text_input("Nombre")
                pat = c2.text_input("Apellido Paterno")
                tel = c1.text_input("Teléfono (10 dígitos)", max_chars=10)
                mail = c2.text_input("Email")
                fnac = st.date_input("Nacimiento")
                
                if st.form_submit_button("Guardar"):
                    if len(tel)==10 and nom:
                        id_p = f"{nom[:2].upper()}{pat[:2].upper()}-{int(time.time())}"
                        c = conn.cursor()
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                  (id_p, str(datetime.now().date()), nom.upper(), pat.upper(), "", tel, mail, "", "616", str(fnac)))
                        conn.commit()
                        registrar_auditoria(st.session_state.usuario, "ALTA PACIENTE", f"Nuevo: {nom} {pat}")
                        st.success("Guardado"); time.sleep(1); st.rerun()
                    else: st.error("Datos incompletos")

        with tab3: # EDICION
            pacientes = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
            if not pacientes.empty:
                opciones = pacientes.apply(lambda x: f"{x['id_paciente']} | {x['nombre']} {x['apellido_paterno']}", axis=1)
                sel = st.selectbox("Editar a:", opciones)
                id_edit = sel.split(" | ")[0]
                
                # Cargar datos actuales
                actual = pd.read_sql(f"SELECT * FROM pacientes WHERE id_paciente='{id_edit}'", conn).iloc[0]
                
                with st.form("edit_pac"):
                    e_tel = st.text_input("Teléfono", value=actual['telefono'])
                    e_mail = st.text_input("Email", value=actual['email'])
                    if st.form_submit_button("Actualizar"):
                        c = conn.cursor()
                        c.execute("UPDATE pacientes SET telefono=?, email=? WHERE id_paciente=?", (e_tel, e_mail, id_edit))
                        conn.commit()
                        registrar_auditoria(st.session_state.usuario, "EDICION", f"Paciente {id_edit} modificado.")
                        st.success("Actualizado"); time.sleep(1); st.rerun()
            conn.close()

    # --- MÓDULO CAJA (CON LÓGICA DE LABORATORIO) ---
    elif menu == "💰 Caja":
        st.title("Caja y Cobranza")
        
        conn = get_db_connection()
        df_p = pd.read_sql("SELECT id_paciente, nombre, apellido_paterno FROM pacientes", conn)
        df_t = pd.read_sql("SELECT * FROM tratamientos ORDER BY categoria, nombre_tratamiento", conn)
        conn.close()
        
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            opc_p = df_p.apply(lambda x: f"{x['id_paciente']} | {x['nombre']} {x['apellido_paterno']}", axis=1)
            sel_p = st.selectbox("Paciente:", opc_p)
            id_pac = sel_p.split(" | ")[0]

        with c_sel2:
            # Lista enriquecida con precio para referencia
            opc_t = ["Manual"] + df_t.apply(lambda x: f"{x['nombre_tratamiento']} (${x['precio_lista']:,.0f})", axis=1).tolist()
            sel_t_str = st.selectbox("Tratamiento:", opc_t)

        # Determinar valores sugeridos
        sug_precio = 0.0
        sug_lab = 0.0
        
        if sel_t_str != "Manual":
            # Extraer nombre puro para buscar en DF
            nombre_puro = sel_t_str.split(" ($")[0] 
            row_t = df_t[df_t['nombre_tratamiento'] == nombre_puro].iloc[0]
            sug_precio = float(row_t['precio_lista'])
            sug_lab = float(row_t['costo_laboratorio_base'])

        st.markdown("---")
        with st.form("caja_form"):
            st.subheader("Detalle del Cobro")
            
            fc1, fc2, fc3 = st.columns(3)
            # Concepto
            con = fc1.text_input("Concepto", value=nombre_puro if sel_t_str != "Manual" else "")
            
            # PRECIOS Y COSTOS (EDITABLES)
            monto = fc2.number_input("Precio a Cobrar ($)", value=sug_precio, step=50.0)
            
            # Campo de Laboratorio (Crucial para la utilidad)
            # Lo mostramos para que la Dra sepa cuánto se descuenta
            lab_cost = fc3.number_input("Costo Laboratorio ($)", value=sug_lab, step=50.0, help="Este monto se resta antes de calcular la comisión")
            
            # Datos de pago
            dc1, dc2 = st.columns(2)
            doc = dc1.selectbox("Doctor Realizó", ["Dr. Emmanuel", "Dra. Mónica", "Asistente"])
            met = dc2.radio("Método", ["Efectivo", "Tarjeta", "Transferencia"], horizontal=True)
            
            # CÁLCULOS EN TIEMPO REAL (VISUALES)
            utilidad_proy = monto - lab_cost
            if utilidad_proy < 0: utilidad_proy = 0
            comision_proy = utilidad_proy * 0.25
            
            st.info(f"📊 **Análisis Financiero:** Cobro ${monto:,.2f} - Lab ${lab_cost:,.2f} = **Utilidad ${utilidad_proy:,.2f}** │ 💼 Comisión Dr: **${comision_proy:,.2f}**")
            
            if st.form_submit_button("💳 PROCESAR PAGO"):
                if monto > 0:
                    c_real, u_real = registrar_pago_inteligente(id_pac, con, monto, lab_cost, met, doc, st.session_state.usuario)
                    st.balloons()
                    st.success(f"Pago Registrado. Comisión asignada: ${c_real:,.2f}")
                    time.sleep(2); st.rerun()

    # --- MÓDULO REPORTES ---
    elif menu == "📊 Reportes":
        st.title("Reportes de Utilidad")
        conn = get_db_connection()
        df = pd.read_sql("SELECT * FROM pagos", conn)
        conn.close()
        
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas Totales (Bruto)", f"${df['monto_cobrado'].sum():,.2f}")
            m2.metric("Gastos Laboratorio", f"${df['costo_laboratorio'].sum():,.2f}", delta_color="inverse")
            m3.metric("Utilidad Real Clínica", f"${df['utilidad_real'].sum():,.2f}")
            
            st.markdown("### Comisiones por Pagar")
            st.bar_chart(df.groupby("doctor_realizo")["comision_doctor"].sum())
            
            with st.expander("Ver Detalle de Movimientos"):
                st.dataframe(df)
        else: st.info("Sin movimientos.")

    # --- AUDITORÍA ---
    elif menu == "🛡️ Auditoría":
        if st.session_state.usuario == "Administrador":
            st.title("Bitácora de Seguridad")
            conn = get_db_connection()
            st.dataframe(pd.read_sql("SELECT * FROM bitacora_seguridad ORDER BY id_evento DESC", conn), use_container_width=True)
            conn.close()
        else: st.error("Acceso restringido")

if __name__ == "__main__":
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if st.session_state.logged_in: main_app()
    else: login()
