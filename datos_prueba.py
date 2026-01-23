import sqlite3
import random
import time
from datetime import datetime, timedelta

# CONFIGURACIÓN
DB_NAME = "dental.db"
NUM_PACIENTES = 12
DIAS_HISTORIA = 60  # Generar datos de hace 2 meses para acá

# Nombres ficticios para generar variedad
NOMBRES = ["Ana", "Carlos", "Beatriz", "David", "Elena", "Fernando", "Gabriela", "Hugo", "Isabel", "Juan", "Karla", "Luis"]
APELLIDOS = ["García", "López", "Martínez", "Rodríguez", "Pérez", "Sánchez", "Ramírez", "Flores", "Gómez", "Díaz"]
TRATAMIENTOS_BASE = [
    # (Categoria, Nombre, Precio, CostoLab, Riesgo, Duracion)
    ("Preventivo", "Limpieza Dental (Profilaxis)", 800, 0, "LOW_RISK", 30),
    ("Preventivo", "Aplicación de Flúor", 400, 0, "LOW_RISK", 15),
    ("Operatoria", "Resina Simple", 1200, 50, "LOW_RISK", 45),
    ("Operatoria", "Resina Compuesta", 1800, 80, "LOW_RISK", 60),
    ("Cirugía", "Extracción Simple", 1500, 100, "HIGH_RISK", 45),
    ("Cirugía", "Cirugía Tercer Molar", 3500, 200, "HIGH_RISK", 90),
    ("Endodoncia", "Endodoncia Unirradicular", 2800, 150, "HIGH_RISK", 60),
    ("Protesis", "Corona Zirconia", 4500, 1200, "LOW_RISK", 60),
    ("Protesis", "Prótesis Total Acrílico", 6000, 1500, "LOW_RISK", 60),
    ("Ortodoncia", "Pago Mensualidad Brackets", 1000, 0, "LOW_RISK", 30)
]

DOCTORES = ["Dr. Emmanuel", "Dra. Mónica"]

def conectar():
    return sqlite3.connect(DB_NAME)

def inicializar_catalogos(c):
    # Inyectar servicios si está vacío
    c.execute("SELECT count(*) FROM servicios")
    if c.fetchone()[0] == 0:
        print("🛠️ Creando catálogo de servicios...")
        for cat, nom, prec, cost, risk, dur in TRATAMIENTOS_BASE:
            c.execute("INSERT INTO servicios (categoria, nombre_tratamiento, precio_lista, costo_laboratorio_base, consent_level, duracion) VALUES (?,?,?,?,?,?)",
                      (cat, nom, prec, cost, risk, dur))

def generar_pacientes(c):
    print(f"👥 Generando {NUM_PACIENTES} pacientes...")
    ids_generados = []
    for _ in range(NUM_PACIENTES):
        nom = random.choice(NOMBRES)
        ape1 = random.choice(APELLIDOS)
        ape2 = random.choice(APELLIDOS)
        nombre_completo = f"{nom} {ape1}"
        
        # ID Paciente estilo: ANA-GAR-123
        id_p = f"{nom[:3].upper()}-{ape1[:3].upper()}-{random.randint(100,999)}"
        ids_generados.append((id_p, nombre_completo))
        
        # Fecha nacimiento random (entre 18 y 60 años)
        dias_vividos = random.randint(18*365, 60*365)
        f_nac = (datetime.now() - timedelta(days=dias_vividos)).strftime("%Y-%m-%d")
        
        try:
            c.execute("""INSERT INTO pacientes (id_paciente, nombre, apellido_paterno, apellido_materno, fecha_nacimiento, telefono, antecedentes, alergias, nota_administrativa) 
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (id_p, nom, ape1, ape2, f_nac, "5512345678", "Ninguno", "Penicilina" if random.random() > 0.8 else "Negadas", ""))
        except sqlite3.IntegrityError:
            pass # Si ya existe el ID (muy raro), lo saltamos
            
    return ids_generados

def generar_historial_financiero(c, pacientes):
    print("💰 Generando historial financiero y citas pasadas...")
    
    # Vamos día por día desde hace 60 días hasta ayer
    fecha_cursor = datetime.now() - timedelta(days=DIAS_HISTORIA)
    
    while fecha_cursor < datetime.now():
        # 40% de probabilidad de tener citas en un día cualquiera
        if random.random() < 0.6: 
            # 1 a 4 citas por día
            num_citas = random.randint(1, 4)
            for _ in range(num_citas):
                paciente = random.choice(pacientes)
                servicio = random.choice(TRATAMIENTOS_BASE) # (Cat, Nom, Prec, Cost, Risk, Dur)
                doctor = random.choice(DOCTORES)
                
                # Desempaquetar servicio
                cat, trat, precio, costo_lab, _, dur = servicio
                
                # Lógica de Pago (80% pagan todo, 20% dejan deuda)
                es_pagado = random.random() < 0.8
                monto_pagado = precio if es_pagado else precio / 2
                saldo = precio - monto_pagado
                estado_pago = "Pagado" if saldo == 0 else "Pendiente"
                
                fecha_str = fecha_cursor.strftime("%d/%m/%Y")
                hora_str = f"{random.randint(9,19)}:00"
                ts = int(fecha_cursor.timestamp())
                
                # INSERTAR CITA/TRANSACCIÓN
                c.execute('''INSERT INTO citas 
                (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, 
                 precio_lista, precio_final, porcentaje, metodo_pago, estado_pago, notas, observaciones, 
                 monto_pagado, saldo_pendiente, fecha_pago, costo_laboratorio, estatus_asistencia, tipo) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ts, fecha_str, hora_str, paciente[0], paciente[1], cat, trat, doctor,
                 precio, precio, 0, random.choice(["Efectivo", "Tarjeta", "Transferencia"]), estado_pago,
                 "Nota clínica generada automáticamente por seed.", "", monto_pagado, saldo, fecha_str, costo_lab, "Asistió", "Tratamiento"))
                
        fecha_cursor += timedelta(days=1)

def generar_agenda_futura(c, pacientes):
    print("📅 Agendando citas futuras...")
    fecha_cursor = datetime.now() + timedelta(days=1) # Mañana
    fin_agenda = datetime.now() + timedelta(days=7)   # Una semana
    
    while fecha_cursor < fin_agenda:
        # 3 citas por día futuro
        for _ in range(3):
            paciente = random.choice(pacientes)
            servicio = random.choice(TRATAMIENTOS_BASE)
            doctor = random.choice(DOCTORES)
            
            fecha_str = fecha_cursor.strftime("%d/%m/%Y")
            hora_str = f"{random.randint(10,18)}:00"
            ts = int(fecha_cursor.timestamp())
            
            # Cita Programada (Sin cobro aún)
            c.execute('''INSERT INTO citas 
            (timestamp, fecha, hora, id_paciente, nombre_paciente, categoria, tratamiento, doctor_atendio, 
             estado_pago, estatus_asistencia, notas, tipo, duracion) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (ts, fecha_str, hora_str, paciente[0], paciente[1], servicio[0], servicio[1], doctor, 
             "Pendiente", "Programada", "Cita futura generada.", "Tratamiento", servicio[5]))
            
        fecha_cursor += timedelta(days=1)

def main():
    conn = conectar()
    c = conn.cursor()
    
    try:
        inicializar_catalogos(c)
        pacientes = generar_pacientes(c)
        if pacientes:
            generar_historial_financiero(c, pacientes)
            generar_agenda_futura(c, pacientes)
            conn.commit()
            print("\n✅ ¡Base de datos poblada con éxito!")
            print(f"   - {len(pacientes)} Pacientes nuevos")
            print("   - Historial de 60 días generado")
            print("   - Agenda próxima semana llena")
            print("   - Ahora puedes probar el Módulo Financiero con datos reales.")
        else:
            print("❌ Error generando pacientes.")
            
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
