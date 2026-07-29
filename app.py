import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import os
from io import BytesIO
import socket
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Planta", layout="wide")

# --- INYECCIÓN DE ESTILOS CSS PERSONALIZADOS (DISEÑO FRACTTAL ONE COMPACTO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Configurar Fuente Global */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #0b0f19 !important;
        color: #f1f5f9 !important;
    }

    /* Asegurar margen superior suficiente para que la barra flotante de Streamlit jamás tape los títulos */
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 0rem !important;
        padding-bottom: 1.5rem !important;
    }
    
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 96% !important;
    }
    
    /* Aplicar a elementos de texto específicos y subir títulos */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stMetric, button div, div[role="radiogroup"] label {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    h1 {
        font-size: 21px !important;
        margin-top: 0px !important;
        margin-bottom: 6px !important;
        padding-top: 0px !important;
    }
    
    h2 {
        font-size: 17px !important;
        margin-top: 0px !important;
        margin-bottom: 6px !important;
    }
    
    h3 {
        font-size: 15px !important;
        margin-top: 0px !important;
        margin-bottom: 4px !important;
    }

    /* Header superior Fracttal style compacto */
    .fracttal-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    .fracttal-title {
        color: #ffffff;
        font-size: 18px !important;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0;
    }
    
    .fracttal-subtitle {
        color: #94a3b8;
        font-size: 11.5px !important;
        margin-top: 2px;
    }
    
    /* Estilos del Sidebar (Menú Lateral Fracttal Compacto) */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
    }
    
    [data-testid="stSidebar"] h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        font-size: 18px !important;
    }
    
    /* Ajustes del Radio Group en Sidebar (Navegación tipo Botón Fracttal) */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 8px !important;
        padding-top: 6px !important;
        padding-bottom: 6px !important;
    }
    
    /* Estilo del label de la sección "Menú:" */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        font-weight: 700 !important;
        color: #94a3b8 !important;
        font-size: 12px !important;
        margin-bottom: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.75px !important;
        padding-left: 4px !important;
    }
    
    /* Quitar el círculo de selección por defecto sin ocultar el texto (usando exclusión de contenedor de texto) */
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])),
    [data-testid="stSidebar"] div[role="radiogroup"] label > div > div:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])) {
        display: none !important;
    }
    
    /* Asegurar que la etiqueta de texto y su párrafo sean siempre visibles */
    [data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        display: block !important;
    }
    
    /* Estilo del botón del menú lateral */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #151f32 !important;
        border: 1px solid #233149 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        width: 100% !important;
        margin-bottom: 4px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Hover Sidebar */
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #1e2d4a !important;
        border-color: #10b981 !important;
        transform: translateX(4px) !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    
    /* Opción seleccionada Sidebar (Acento Esmeralda Fracttal) */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input[type="radio"]:checked) {
        background: linear-gradient(90deg, #059669 0%, #10b981 100%) !important;
        border-color: #34d399 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        box-shadow: 0px 4px 12px rgba(16, 185, 129, 0.3) !important;
    }
    
    /* Texto del menú */
    [data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-size: 13.5px !important;
        color: #e2e8f0 !important;
        margin: 0 !important;
        line-height: 1.4 !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input[type="radio"]:checked) div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Tarjetas Métricas Fracttal Compactas */
    div[data-testid="metric-container"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important;
        border-top: 3px solid #10b981 !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 19px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 12px !important;
    }

    /* Badges de Estado Fracttal Compactos */
    .badge-operativo {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid #059669;
        padding: 3px 8px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 11px;
        display: inline-block;
    }
    
    .badge-mantenimiento {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid #d97706;
        padding: 3px 8px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 11px;
        display: inline-block;
    }

    .badge-revision {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid #dc2626;
        padding: 3px 8px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 11px;
        display: inline-block;
    }

    /* Botones primarios y de formulario */
    .stButton > button, div[stFormSubmitButton] > button {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
        font-size: 13px !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover, div[stFormSubmitButton] > button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

def formatear_fecha_visible(fecha_str):
    if not fecha_str or str(fecha_str).strip() == 'nan' or str(fecha_str).strip() == '':
        return ""
    try:
        dt = pd.to_datetime(fecha_str)
        return dt.strftime("%d/%m/%Y")
    except:
        return str(fecha_str)

def formatear_fecha_hora_visible(fechahora_str):
    if not fechahora_str or str(fechahora_str).strip() == 'nan' or str(fechahora_str).strip() == '':
        return ""
    try:
        dt = pd.to_datetime(fechahora_str)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except:
        return str(fechahora_str)

def generar_pdf_hidrocarburos(df_reporte, filtro_prod_str, filtro_mov_str, filtro_anio_str, filtro_mes_str, ingresos, egresos, balance, usuario_emisor=""):
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(22, 36, 71)
            self.cell(0, 8, 'Areneras de la Cruz y Rozas S.A.', new_x='LMARGIN', new_y='NEXT', align='C')
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 6, 'Gestion de Planta - Reporte de Movimientos de Hidrocarburos', new_x='LMARGIN', new_y='NEXT', align='C')
            self.set_draw_color(52, 152, 219)
            self.set_line_width(0.8)
            self.line(10, 24, 200, 24)
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} - Areneras de la Cruz y Rozas S.A.', align='C')

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    fecha_emision = datetime.now().strftime('%d/%m/%Y %H:%M')
    emisor_txt = usuario_emisor if usuario_emisor else 'Administracion'
    
    def clean_txt(t):
        if not t:
            return ""
        return str(t).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(100, 5, f'Fecha de Emision: {fecha_emision}')
    pdf.cell(90, 5, clean_txt(f'Emitido por: {emisor_txt}'), new_x='LMARGIN', new_y='NEXT', align='R')
    pdf.ln(2)

    pdf.set_fill_color(240, 243, 246)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(22, 36, 71)
    filtro_lbl = clean_txt(f" FILTROS: Producto: {filtro_prod_str} | Movimiento: {filtro_mov_str} | Periodo: {filtro_mes_str} / {filtro_anio_str}")
    pdf.cell(0, 6, filtro_lbl, fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 247, 235)
    pdf.set_text_color(40, 140, 60)
    pdf.cell(61, 9, f' Ingresos: {ingresos:,.1f} Lts', border=1, fill=True, align='C')
    pdf.cell(3, 9, '')
    pdf.set_fill_color(253, 237, 237)
    pdf.set_text_color(180, 40, 40)
    pdf.cell(61, 9, f' Consumos: {egresos:,.1f} Lts', border=1, fill=True, align='C')
    pdf.cell(3, 9, '')
    pdf.set_fill_color(235, 243, 250)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(62, 9, f' Balance: {balance:,.1f} Lts', border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(22, 36, 71)
    pdf.set_text_color(255, 255, 255)
    
    col_w = [24, 38, 22, 26, 45, 35]
    headers = ['Fecha', 'Producto', 'Movimiento', 'Cantidad', 'Destino', 'Responsable']
    
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 30, 30)
    
    fill_row = False
    for _, r in df_reporte.iterrows():
        pdf.set_fill_color(248, 249, 250) if fill_row else pdf.set_fill_color(255, 255, 255)
        
        fecha_val = clean_txt(str(r.get('Fecha', '')))
        prod_val = clean_txt(str(r.get('Producto', ''))[:22])
        mov_val = clean_txt(str(r.get('Movimiento', '')))
        try:
            cant_num = float(r.get('Cantidad', 0))
        except:
            cant_num = 0.0
        cant_val = f'{cant_num:,.1f} Lts'
        dest_val = clean_txt(str(r.get('Destino', ''))[:25])
        oper_val = clean_txt(str(r.get('Operario', ''))[:20])

        pdf.cell(col_w[0], 6, fecha_val, border=1, fill=True, align='C')
        pdf.cell(col_w[1], 6, prod_val, border=1, fill=True, align='L')
        pdf.cell(col_w[2], 6, mov_val, border=1, fill=True, align='C')
        pdf.cell(col_w[3], 6, cant_val, border=1, fill=True, align='R')
        pdf.cell(col_w[4], 6, dest_val, border=1, fill=True, align='L')
        pdf.cell(col_w[5], 6, oper_val, border=1, fill=True, align='L')
        pdf.ln()
        fill_row = not fill_row

    return bytes(pdf.output())

def buscar_coincidencia_empleado(usuario, lista_empleados):
    if not usuario or not lista_empleados:
        return None
    import unicodedata
    
    def normalizar(t):
        if not t:
            return ""
        # Reemplazar caracteres no alfanuméricos (incluyendo codificación rota) por espacios
        t_clean = ""
        for c in str(t):
            if c.isalnum() or c.isspace():
                t_clean += c
            else:
                t_clean += " "
        # Normalizar caracteres unicode, quitar acentos y pasar a minúsculas
        norm_t = unicodedata.normalize('NFKD', t_clean).encode('ASCII', 'ignore').decode('utf-8').lower()
        return norm_t.strip()

    usuario_norm = normalizar(usuario)
    usuario_words = [w for w in usuario_norm.split() if len(w) >= 3] # Palabras de 3 o más letras
    
    if not usuario_words:
        return None

    mejor_idx = None
    max_coincidencias = 0

    for i, emp in enumerate(lista_empleados):
        emp_norm = normalizar(emp)
        emp_words = [w for w in emp_norm.split() if len(w) >= 3]
        
        # 1. Coincidencia exacta
        if usuario_norm == emp_norm:
            return i
            
        # 2. Contar palabras coincidentes
        coincidencias = 0
        for uw in usuario_words:
            if uw in emp_words:
                coincidencias += 1
            else:
                # Comprobación de prefijo/sufijo para tolerar errores de codificación (ej: "nstor" vs "nestor")
                for ew in emp_words:
                    if len(uw) >= 4 and len(ew) >= 4:
                        if uw in ew or ew in uw:
                            coincidencias += 1
                            break
                            
        # Guardar la mejor coincidencia encontrada
        if coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            mejor_idx = i
            
    # Si encontramos al menos una palabra clave coincidente (como el apellido), es válido
    if max_coincidencias >= 1:
        return mejor_idx
        
    return None

DB_FILE = "gestion_planta.db"

# --- CONEXIÓN Y CREACIÓN DE TABLAS SQLITE ---
def get_connection():
    # timeout=20.0 evita errores de bloqueo en escrituras concurrentes
    return sqlite3.connect(DB_FILE, timeout=20.0)

def verificar_password_usuario(usuario_actual, password_ingresado):
    if not password_ingresado or not str(password_ingresado).strip():
        return False
    pwd = str(password_ingresado).strip()
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if usuario_actual:
            cursor.execute("SELECT Password FROM usuarios WHERE Usuario = ?", (usuario_actual,))
            row = cursor.fetchone()
            if row and str(row[0]).strip() == pwd:
                conn.close()
                return True
        cursor.execute("SELECT Password FROM usuarios WHERE Rol = 'Administrador'")
        admin_rows = cursor.fetchall()
        conn.close()
        for a_row in admin_rows:
            if str(a_row[0]).strip() == pwd:
                return True
    except Exception:
        pass
    return False

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Crear tablas si no existen con las columnas originales capitalizadas
    cursor.execute("CREATE TABLE IF NOT EXISTS maquinas (Nombre TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS empleados (Nombre TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS productos (Nombre TEXT PRIMARY KEY)")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mantenimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha TEXT,
        Maquina TEXT,
        Operario TEXT,
        Tipo TEXT,
        Inicio TEXT,
        Fin TEXT,
        Horimetro REAL,
        Detalle TEXT,
        Deposito TEXT,
        FechaCreacion TEXT,
        HistorialModificaciones TEXT,
        CreadoPor TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planificacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Maquina TEXT,
        Tarea TEXT,
        Fecha_Prog TEXT,
        Estado TEXT,
        Fecha_Fin TEXT,
        Tecnico TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha TEXT,
        Producto TEXT,
        Movimiento TEXT,
        Cantidad REAL,
        Destino TEXT,
        FechaCreacion TEXT,
        HistorialModificaciones TEXT,
        CreadoPor TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hidrocarburos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha TEXT,
        Producto TEXT,
        Movimiento TEXT,
        Cantidad REAL,
        Destino TEXT,
        Operario TEXT,
        FechaCreacion TEXT,
        HistorialModificaciones TEXT,
        CreadoPor TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS controles_diarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha TEXT,
        Maquina TEXT,
        Tecnico TEXT,
        Deposito TEXT,
        Horimetro_KM TEXT,
        I_a_perdidas TEXT,
        I_b_aceite_motor TEXT,
        I_c_agua_motor TEXT,
        I_d_tension_correa TEXT,
        I_e_presion_cubiertas TEXT,
        I_f_correa_bba_arena TEXT,
        I_g_acople_embrague TEXT,
        II_a_tablero TEXT,
        II_b_sirena_luces TEXT,
        II_c_embrague_vacio TEXT,
        III_a_mangueras_rad TEXT,
        III_b_temp_rodamientos TEXT,
        IV_a_engrase_balde TEXT,
        IV_b_engrase_torre TEXT,
        Observaciones TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        Usuario TEXT PRIMARY KEY,
        Password TEXT,
        Token TEXT,
        Rol TEXT,
        Puesto TEXT
    )
    """)
    
    # Asegurar que haya al menos un usuario admin inicial
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        import uuid
        default_token = uuid.uuid4().hex
        cursor.execute("INSERT INTO usuarios (Usuario, Password, Token, Rol, Puesto) VALUES (?, ?, ?, ?, ?)",
                       ("admin", "admin", default_token, "Administrador", "Administrador del Sistema"))
        conn.commit()

    # Asegurar que existan los 5 equipos base en el catálogo de máquinas
    for maq in ["Scania", "Case W20", "Michigan 75", "Toyota 1", "Toyota 2"]:
        cursor.execute("INSERT OR IGNORE INTO maquinas (Nombre) VALUES (?)", (maq,))
    conn.commit()

    # Asegurar que exista la columna Puesto en usuarios si la tabla ya existe
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas_usr = [row[1] for row in cursor.fetchall()]
    if "Puesto" not in columnas_usr:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN Puesto TEXT")
    
    # Asegurar que existan las nuevas columnas en mantenimientos si ya existe la tabla
    cursor.execute("PRAGMA table_info(mantenimientos)")
    columnas = [row[1] for row in cursor.fetchall()]
    if "FechaCreacion" not in columnas:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN FechaCreacion TEXT")
    if "HistorialModificaciones" not in columnas:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN HistorialModificaciones TEXT")
    if "CreadoPor" not in columnas:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN CreadoPor TEXT")

    # Asegurar que existan las nuevas columnas en stock si ya existe la tabla
    cursor.execute("PRAGMA table_info(stock)")
    columnas_stk = [row[1] for row in cursor.fetchall()]
    if "FechaCreacion" not in columnas_stk:
        cursor.execute("ALTER TABLE stock ADD COLUMN FechaCreacion TEXT")
    if "HistorialModificaciones" not in columnas_stk:
        cursor.execute("ALTER TABLE stock ADD COLUMN HistorialModificaciones TEXT")
    if "CreadoPor" not in columnas_stk:
        cursor.execute("ALTER TABLE stock ADD COLUMN CreadoPor TEXT")

    # Asegurar que existan las nuevas columnas en hidrocarburos si ya existe la tabla
    cursor.execute("PRAGMA table_info(hidrocarburos)")
    columnas_hd = [row[1] for row in cursor.fetchall()]
    if "FechaCreacion" not in columnas_hd:
        cursor.execute("ALTER TABLE hidrocarburos ADD COLUMN FechaCreacion TEXT")
    if "HistorialModificaciones" not in columnas_hd:
        cursor.execute("ALTER TABLE hidrocarburos ADD COLUMN HistorialModificaciones TEXT")
    if "CreadoPor" not in columnas_hd:
        cursor.execute("ALTER TABLE hidrocarburos ADD COLUMN CreadoPor TEXT")
        
    # Asegurar que existan las nuevas columnas en controles_diarios si ya existe la tabla
    cursor.execute("PRAGMA table_info(controles_diarios)")
    columnas_cd = [row[1] for row in cursor.fetchall()]
    if "CreadoPor" not in columnas_cd:
        cursor.execute("ALTER TABLE controles_diarios ADD COLUMN CreadoPor TEXT")
        
    # Asegurar que existan las nuevas columnas en planificacion si ya existe la tabla
    cursor.execute("PRAGMA table_info(planificacion)")
    columnas_p = [row[1] for row in cursor.fetchall()]
    if "Tipo" not in columnas_p:
        cursor.execute("ALTER TABLE planificacion ADD COLUMN Tipo TEXT DEFAULT 'Preventivo Programado'")
    if "Prioridad" not in columnas_p:
        cursor.execute("ALTER TABLE planificacion ADD COLUMN Prioridad TEXT DEFAULT 'Media'")
    if "Detalle" not in columnas_p:
        cursor.execute("ALTER TABLE planificacion ADD COLUMN Detalle TEXT DEFAULT ''")
    if "Horimetro_Est" not in columnas_p:
        cursor.execute("ALTER TABLE planificacion ADD COLUMN Horimetro_Est REAL DEFAULT 0.0")
        
    # Inicializar registros antiguos con valores por defecto
    cursor.execute("UPDATE mantenimientos SET FechaCreacion = Fecha || ' 00:00:00' WHERE FechaCreacion IS NULL")
    cursor.execute("UPDATE mantenimientos SET HistorialModificaciones = 'Importado desde Excel.' WHERE HistorialModificaciones IS NULL")
    
    cursor.execute("UPDATE stock SET FechaCreacion = Fecha || ' 00:00:00' WHERE FechaCreacion IS NULL")
    cursor.execute("UPDATE stock SET HistorialModificaciones = 'Carga inicial o importación.' WHERE HistorialModificaciones IS NULL")
    cursor.execute("UPDATE stock SET CreadoPor = 'Desconocido' WHERE CreadoPor IS NULL")

    cursor.execute("UPDATE hidrocarburos SET FechaCreacion = Fecha || ' 00:00:00' WHERE FechaCreacion IS NULL")
    cursor.execute("UPDATE hidrocarburos SET HistorialModificaciones = 'Carga inicial o importación.' WHERE HistorialModificaciones IS NULL")
    cursor.execute("UPDATE hidrocarburos SET CreadoPor = 'Desconocido' WHERE CreadoPor IS NULL")
    
    conn.commit()
    
    # --- MIGRACIÓN AUTOMÁTICA DE CSV EXISTENTES A SQLITE ---
    csv_files = {
        "db_maquinas.csv": "maquinas",
        "db_empleados.csv": "empleados",
        "db_productos.csv": "productos",
        "reg_mantenimientos.csv": "mantenimientos",
        "reg_planificacion.csv": "planificacion",
        "reg_stock.csv": "stock",
        "reg_hidrocarburos.csv": "hidrocarburos"
    }
    
    migrated = False
    for csv_file, table in csv_files.items():
        if os.path.exists(csv_file):
            try:
                # Leer el archivo CSV
                df = pd.read_csv(csv_file)
                if not df.empty:
                    # Limpieza de nulos o diferencias de columnas
                    if table == "mantenimientos":
                        # Asegurar que todas las columnas existan
                        for col in ["Fecha", "Maquina", "Operario", "Tipo", "Inicio", "Fin", "Horimetro", "Detalle", "Deposito", "FechaCreacion", "HistorialModificaciones"]:
                            if col not in df.columns:
                                df[col] = ""
                    # Insertar a la base de datos sin incluir el índice
                    df.to_sql(table, conn, if_exists="append", index=False)
                    migrated = True
                
                # Mover el archivo migrado a la carpeta Back-up para evitar volver a migrarlo
                backup_dir = "Back-up"
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                # Si ya existe un archivo con el mismo nombre en Back-up, lo renombramos con timestamp
                dest_path = os.path.join(backup_dir, csv_file)
                if os.path.exists(dest_path):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_path = os.path.join(backup_dir, f"{timestamp}_{csv_file}")
                
                os.rename(csv_file, dest_path)
            except Exception as e:
                # Si falla la migración de un archivo particular, lo reportamos internamente
                st.error(f"No se pudo migrar el archivo {csv_file}: {e}")
                
    if migrated:
        conn.commit()
    conn.close()

# Inicializar Base de Datos al arrancar la app y migrar datos antiguos
init_db()

# --- EVALUAR AUTENTICACIÓN ---
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "token" not in st.session_state:
    st.session_state["token"] = None

# A. Leer cookies de la solicitud HTTP
def get_cookies():
    # 1. Intentar con st.context.cookies (Streamlit moderno 1.36+)
    try:
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            return st.context.cookies
    except:
        pass
        
    # 2. Intentar con st.context.headers (Streamlit 1.36+)
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            cookie_str = st.context.headers.get("Cookie", "")
            if cookie_str:
                cookies = {}
                for item in cookie_str.split(";"):
                    item = item.strip()
                    if "=" in item:
                        k, v = item.split("=", 1)
                        cookies[k] = urllib.parse.unquote(v)
                return cookies
    except:
        pass

    # 3. Fallback a WebSocket headers internos (versiones anteriores)
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            cookie_str = headers.get("Cookie", "")
            cookies = {}
            if cookie_str:
                for item in cookie_str.split(";"):
                    item = item.strip()
                    if "=" in item:
                        k, v = item.split("=", 1)
                        cookies[k] = urllib.parse.unquote(v)
            return cookies
    except:
        pass
    return {}

cookies_dict = get_cookies()
print("DEBUG - Cookies recibidas del navegador:", cookies_dict)
usr_cookie = cookies_dict.get("planta_usr")
tkn_cookie = cookies_dict.get("planta_tkn")

# Validar cookies si no hay sesión activa en st.session_state
if not st.session_state["usuario"] and usr_cookie and tkn_cookie:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Usuario, Rol, Puesto FROM usuarios WHERE Usuario = ? AND Token = ?", (usr_cookie, tkn_cookie))
    match = cursor.fetchone()
    conn.close()
    if match:
        st.session_state["usuario"] = match[0]
        st.session_state["token"] = tkn_cookie
        st.session_state["rol"] = match[1]
        st.session_state["puesto"] = match[2]

# B. Leer parámetros de query (si no se pudo validar por cookies directamente)
if not st.session_state["usuario"]:
    q_params = st.query_params
    if "usr" in q_params and "tkn" in q_params:
        u_param = q_params["usr"]
        t_param = q_params["tkn"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Usuario, Rol, Puesto FROM usuarios WHERE Usuario = ? AND Token = ?", (u_param, t_param))
        match = cursor.fetchone()
        conn.close()
        if match:
            st.session_state["usuario"] = match[0]
            st.session_state["token"] = t_param
            st.session_state["rol"] = match[1]
            st.session_state["puesto"] = match[2]
            # Guardar tanto en cookies como en localStorage para redundancia absoluta (codificado para soportar espacios/acentos)
            import time
            rand_t = time.time()
            st.markdown(f"""
            <img src="x?r={rand_t}" onerror="
            document.cookie = 'planta_usr=' + encodeURIComponent('{match[0]}') + '; path=/; max-age=31536000; SameSite=Lax; Secure';
            document.cookie = 'planta_tkn=' + encodeURIComponent('{t_param}') + '; path=/; max-age=31536000; SameSite=Lax; Secure';
            localStorage.setItem('planta_usr', '{match[0]}');
            localStorage.setItem('planta_tkn', '{t_param}');
            " style="display:none;">
            """, unsafe_allow_html=True)
        else:
            # Token inválido, limpiar de la URL para evitar bucles
            st.query_params.clear()

# C. Recuperar token y roles si hay sesión activa pero no se cargaron en la memoria temporal
if st.session_state["usuario"] and (not st.session_state["token"] or "rol" not in st.session_state or not st.session_state["rol"]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Token, Rol, Puesto FROM usuarios WHERE Usuario = ?", (st.session_state["usuario"],))
    row = cursor.fetchone()
    conn.close()
    if row:
        st.session_state["token"] = row[0]
        st.session_state["rol"] = row[1]
        st.session_state["puesto"] = row[2]

# D. Si no hay sesión activa (no se detectó cookie ni query param), verificar en localStorage
if not st.session_state["usuario"]:
    import time
    rand_t = time.time()
    st.markdown("""
    <img src="x?r=""" + str(rand_t) + """\" onerror="
    const usr = localStorage.getItem('planta_usr');
    const tkn = localStorage.getItem('planta_tkn');
    if (usr && tkn) {
        const url = new URL(window.location.href);
        if (!url.searchParams.has('usr') || !url.searchParams.has('tkn')) {
            url.searchParams.set('usr', usr);
            url.searchParams.set('tkn', tkn);
            window.location.href = url.toString();
        }
    }
    " style="display:none;">
    """, unsafe_allow_html=True)
    
    # Mostrar pantalla de login hermosa y moderna
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    col_log1, col_log2, col_log3 = st.columns([1, 2, 1])
    with col_log2:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='color: #ffffff; font-weight: 700;'>🛠️ Gestión de Planta</h2>
            <p style='color: #8892b0;'>Por favor inicie sesión para acceder al sistema</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_login"):
            u_input = st.text_input("Usuario / Técnico")
            p_input = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_login:
                if not u_input.strip() or not p_input.strip():
                    st.error("Por favor completa el usuario y la contraseña.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT Token, Rol, Puesto FROM usuarios WHERE Usuario = ? AND Password = ?", (u_input.strip(), p_input.strip()))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row:
                        token = row[0]
                        rol = row[1]
                        puesto = row[2]
                        st.session_state["token"] = token
                        st.session_state["usuario"] = u_input.strip()
                        st.session_state["rol"] = rol
                        st.session_state["puesto"] = puesto
                        st.success("¡Inicio de sesión exitoso! Redireccionando...")
                        # Redireccionar de forma nativa en Python sin requerir ejecución JS en el form submit
                        st.query_params["usr"] = u_input.strip()
                        st.query_params["tkn"] = token
                        st.rerun()
                    else:
                        st.error("⚠️ Usuario o contraseña incorrectos.")
        
        st.info("💡 Credencial de fábrica: Usuario 'admin' y Contraseña 'admin'. Recomendamos cambiarla en la sección de Configuración.")
    st.stop()

# --- FUNCIONES DE BASE DE DATOS ---
def cargar_datos_db(tabla):
    conn = get_connection()
    df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
    conn.close()
    return df.fillna("")

def cargar_lista_columna(tabla, columna):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {columna} FROM {tabla} ORDER BY {columna} ASC")
        resultados = [row[0] for row in cursor.fetchall()]
        return resultados
    except:
        return []
    finally:
        conn.close()

# --- FUNCION DETALLE INDEPENDIENTE EN NUEVA PESTAÑA ---
def mostrar_detalle_independiente(detail_id):
    col_back, _ = st.columns([1, 4])
    if col_back.button("⬅️ Volver al Reporte General", use_container_width=True):
        st.query_params.clear()
        st.rerun()
        
    st.title(f"📋 Ficha de Mantenimiento Detallada #{detail_id}")
    st.markdown("---")
    
    # Cargar listas para desplegables en la edición
    maquinas_list_db = cargar_lista_columna("maquinas", "Nombre")
    empleados_list_db = cargar_lista_columna("empleados", "Nombre")
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM mantenimientos WHERE id = ?", conn, params=[detail_id])
    conn.close()
    
    if df.empty:
        st.error(f"El registro con ID {detail_id} no existe en la base de datos.")
        if st.button("Volver al inicio"):
            st.query_params.clear()
            st.rerun()
        return
        
    registro = df.iloc[0]
    
    # Contenedor con borde para mostrar la ficha
    with st.container(border=True):
        st.subheader("📌 Datos de la Intervención")
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Fecha de Actividad:** {formatear_fecha_visible(registro['Fecha'])}")
        col1.write(f"**Depósito:** {registro['Deposito']}")
        col1.write(f"**Máquina:** {registro['Maquina']}")
        
        col2.write(f"**Operario / Técnico:** {registro['Operario']}")
        col2.write(f"**Tipo Mantenimiento:** {registro['Tipo']}")
        col2.write(f"**Horímetro:** {registro['Horimetro']} hs")
        
        col3.write(f"**Hora Inicio:** {registro['Inicio']}")
        col3.write(f"**Hora Fin:** {registro['Fin']}")
        
        st.markdown("### 📝 Detalle y Repuestos Usados")
        # Mostrar el detalle con saltos de línea correctos
        st.info(str(registro['Detalle']).strip())
        
        st.markdown("### 📅 Fechas de Control")
        col_c1, col_c2 = st.columns(2)
        col_c1.write(f"**Fecha Carga Primaria:** {formatear_fecha_hora_visible(registro['FechaCreacion'])}")
        
        # Mostrar el usuario de carga y puesto
        usuario_carga = registro.get("CreadoPor") if "CreadoPor" in registro and pd.notna(registro["CreadoPor"]) else None
        col_c2.write(f"**Usuario de Carga:** {usuario_carga or 'No registrado (Carga antigua)'}")
        if usuario_carga:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Puesto FROM usuarios WHERE Usuario = ?", (usuario_carga,))
            p_row = cursor.fetchone()
            conn.close()
            if p_row and p_row[0]:
                col_c2.write(f"**Puesto de Trabajo:** {p_row[0]}")
        
        st.write("**Historial de Modificaciones:**")
        historial_str = str(registro['HistorialModificaciones']) if pd.notna(registro['HistorialModificaciones']) else "Sin modificaciones."
        st.text_area("Log de cambios:", value=historial_str, height=140, disabled=True)

    # --- SECCIÓN DE EDICIÓN CON BOTÓN Y CONTRASEÑA ---
    if "edit_ficha_activa" not in st.session_state:
        st.session_state["edit_ficha_activa"] = False

    boton_edit_lbl = "❌ Cerrar Edición" if st.session_state["edit_ficha_activa"] else "✏️ Editar / 🗑️ Eliminar este Reporte"
    if st.button(boton_edit_lbl, key=f"btn_toggle_ficha_{detail_id}", use_container_width=True):
        st.session_state["edit_ficha_activa"] = not st.session_state["edit_ficha_activa"]
        st.rerun()

    if st.session_state["edit_ficha_activa"]:
        with st.container(border=True):
            st.subheader("✏️ Edición de la Ficha de Mantenimiento")
            with st.form("form_edicion_detalle"):
                c1, c2 = st.columns(2)
                with c1:
                    fecha_edit = st.date_input("Fecha", value=pd.to_datetime(registro["Fecha"]).date(), format="DD/MM/YYYY")
                    deposito_edit = st.selectbox("Depósito", ["Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"], index=["Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"].index(registro["Deposito"]) if registro["Deposito"] in ["Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"] else 0)
                    maquina_edit = st.selectbox("Máquina", maquinas_list_db, index=maquinas_list_db.index(registro["Maquina"]) if registro["Maquina"] in maquinas_list_db else 0)
                    operario_edit = st.selectbox("Técnico responsable", empleados_list_db, index=empleados_list_db.index(registro["Operario"]) if registro["Operario"] in empleados_list_db else 0)
                with c2:
                    tipo_edit = st.selectbox("Tipo de mantenimiento", ["Correctivo", "Preventivo"], index=["Correctivo", "Preventivo"].index(registro["Tipo"]) if registro["Tipo"] in ["Correctivo", "Preventivo"] else 0)
                    inicio_edit = st.text_input("Hora Inicio", value=str(registro["Inicio"]))
                    fin_edit = st.text_input("Hora Fin", value=str(registro["Fin"]))
                    horimetro_edit = st.number_input("Horímetro", min_value=0.0, step=0.1, value=float(registro["Horimetro"]) if str(registro["Horimetro"]).strip() else 0.0, format="%.1f")
                    
                detalle_edit = st.text_area("Detalle (Actividad / Repuestos)", value=str(registro["Detalle"]))
                pass_edit = st.text_input("🔑 Contraseña de confirmación (tu clave de ingreso)", type="password")
                
                col_save, col_del = st.columns([2, 1])
                guardar = col_save.form_submit_button("💾 Guardar Cambios en Ficha", use_container_width=True)
                eliminar = col_del.form_submit_button("🗑️ Eliminar Ficha", use_container_width=True)
                
                usr_act = st.session_state.get("usuario", "")

                if guardar:
                    if not verificar_password_usuario(usr_act, pass_edit):
                        st.error("🔒 Contraseña incorrecta o no ingresada. No se pudieron guardar los cambios.")
                    else:
                        cambios = []
                        if str(registro['Fecha']) != fecha_edit.strftime("%Y-%m-%d"):
                            cambios.append(f"Fecha: '{registro['Fecha']}' -> '{fecha_edit.strftime('%Y-%m-%d')}'")
                        if str(registro['Deposito']) != deposito_edit:
                            cambios.append(f"Depósito: '{registro['Deposito']}' -> '{deposito_edit}'")
                        if str(registro['Maquina']) != maquina_edit:
                            cambios.append(f"Máquina: '{registro['Maquina']}' -> '{maquina_edit}'")
                        if str(registro['Operario']) != operario_edit:
                            cambios.append(f"Técnico: '{registro['Operario']}' -> '{operario_edit}'")
                        if str(registro['Tipo']) != tipo_edit:
                            cambios.append(f"Tipo: '{registro['Tipo']}' -> '{tipo_edit}'")
                        if str(registro['Inicio']) != inicio_edit:
                            cambios.append(f"Inicio: '{registro['Inicio']}' -> '{inicio_edit}'")
                        if str(registro['Fin']) != fin_edit:
                            cambios.append(f"Fin: '{registro['Fin']}' -> '{fin_edit}'")
                        if float(registro['Horimetro']) != float(horimetro_edit):
                            cambios.append(f"Horímetro: '{registro['Horimetro']}' -> '{horimetro_edit}'")
                        if str(registro['Detalle']).strip() != detalle_edit.strip():
                            cambios.append(f"Detalle modificado")
                            
                        if cambios:
                            log_fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            detalle_cambios = ", ".join(cambios)
                            usr_str = usr_act if usr_act else "Usuario"
                            nuevo_log = f"{log_fecha} - Modificado por usuario {usr_str}: {detalle_cambios}"
                            
                            historial_actual = str(registro['HistorialModificaciones']) if pd.notna(registro['HistorialModificaciones']) else ""
                            nuevo_historial = (historial_actual + "\n" + nuevo_log).strip()
                            
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                            UPDATE mantenimientos SET
                                Fecha = ?, Deposito = ?, Maquina = ?, Operario = ?, Tipo = ?, Inicio = ?, Fin = ?, Horimetro = ?, Detalle = ?, HistorialModificaciones = ?
                            WHERE id = ?
                            """, (fecha_edit.strftime("%Y-%m-%d"), deposito_edit, maquina_edit, operario_edit, tipo_edit, inicio_edit, fin_edit, horimetro_edit, detalle_edit, nuevo_historial, detail_id))
                            conn.commit()
                            conn.close()
                            st.success("¡El registro se actualizó y se guardó en el historial!")
                            st.session_state["edit_ficha_activa"] = False
                            st.rerun()
                        else:
                            st.info("No se detectaron cambios para guardar.")

                if eliminar:
                    if not verificar_password_usuario(usr_act, pass_edit):
                        st.error("🔒 Contraseña incorrecta o no ingresada. No se pudo eliminar el registro.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM mantenimientos WHERE id = ?", (detail_id,))
                        conn.commit()
                        conn.close()
                        st.success("¡Registro eliminado con éxito!")
                        st.query_params.clear()
                        st.rerun()

def mostrar_ficha_checklist_independiente(chk_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM controles_diarios WHERE id = ?", conn, params=[chk_id])
    conn.close()
    
    if df.empty:
        st.error(f"El control diario con ID {chk_id} no existe en la base de datos.")
        if st.button("Volver al inicio"):
            st.query_params.clear()
            st.rerun()
        return
        
    registro = df.iloc[0]
    
    # Contenedor con borde para mostrar la ficha
    with st.container(border=True):
        st.subheader("📋 Reporte de Control Diario (Check-List)")
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Fecha:** {formatear_fecha_visible(registro['Fecha'])}")
        col1.write(f"**Máquina / Equipo:** {registro['Maquina']}")
        
        col2.write(f"**Técnico Responsable:** {registro['Tecnico']}")
        col2.write(f"**Depósito:** {registro['Deposito']}")
        
        col3.write(f"**Horómetro / Kilómetros:** {registro['Horimetro_KM']}")
        
        # Mostrar el usuario de carga y puesto
        usuario_carga = registro.get("CreadoPor") if "CreadoPor" in registro and pd.notna(registro["CreadoPor"]) else None
        col3.write(f"**Usuario de Carga:** {usuario_carga or 'No registrado (Carga antigua)'}")
        if usuario_carga:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Puesto FROM usuarios WHERE Usuario = ?", (usuario_carga,))
            p_row = cursor.fetchone()
            conn.close()
            if p_row and p_row[0]:
                col3.write(f"**Puesto de Trabajo:** {p_row[0]}")
        
        st.markdown("---")
        
        # Mostrar el listado con formato premium
        st.markdown("### 🚜 Detalle de la Inspección")
        
        c_i1, c_i2 = st.columns(2)
        
        with c_i1:
            st.markdown("##### **I. ANTES de poner en marcha**")
            st.write(f"**I.a Pérdidas de aceite/agua (mangueras radiador):** {registro['I_a_perdidas']}")
            st.write(f"**I.b Revisar / agregar nivel de aceite motor:** {registro['I_b_aceite_motor']}")
            st.write(f"**I.c Revisar / agregar nivel de agua motor:** {registro['I_c_agua_motor']}")
            st.write(f"**I.d Revisar tensión correa:** {registro['I_d_tension_correa']}")
            st.write(f"**I.e Revisar presión aire cubiertas:** {registro['I_e_presion_cubiertas']}")
            st.write(f"**I.f Revisar tensión correas bomba arena intermedia:** {registro['I_f_correa_bba_arena']}")
            st.write(f"**I.g Control normal funcionamiento al accionar acople embrague:** {registro['I_g_acople_embrague']}")
            
            st.markdown("##### **II. Poner en marcha (Calentamiento)**")
            st.write(f"**II.a Controlar tablero (relojes / vigía):** {registro['II_a_tablero']}")
            st.write(f"**II.b Controlar funcionamiento sirena y luces marcha atrás:** {registro['II_b_sirena_luces']}")
            st.write(f"**II.c Probar encloche embrague en vacío (sin vibración/golpes):** {registro['II_c_embrague_vacio']}")

        with c_i2:
            st.markdown("##### **III. Durante la operación (aprox. 1 hora)**")
            st.write(f"**III.a Revisar mangueras del radiador (calientes):** {registro['III_a_mangueras_rad']}")
            st.write(f"**III.b Revisar temperatura rodamientos intermedia:** {registro['III_b_temp_rodamientos']}")
            
            st.markdown("##### **IV. Antes del cierre de la jornada (aprox. 15hs)**")
            st.write(f"**IV.a Engrase movimientos de balde:** {registro['IV_a_engrase_balde']}")
            st.write(f"**IV.b Engrase movimientos de torre:** {registro['IV_b_engrase_torre']}")
            
            st.markdown("##### **📝 Observaciones / Diagnóstico**")
            obs = str(registro['Observaciones']).strip() if pd.notna(registro['Observaciones']) and str(registro['Observaciones']).strip() else "Sin observaciones."
            st.info(obs)
            
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    with st.expander("🗑️ Zona de Peligro - Eliminar Control Diario"):
        st.warning("⚠️ Esta acción es irreversible y eliminará permanentemente este reporte de la base de datos.")
        confirmar_eliminar = st.button("🗑️ Confirmar Eliminación Permanente", key=f"del_chk_{chk_id}", use_container_width=True)
        if confirmar_eliminar:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM controles_diarios WHERE id = ?", (chk_id,))
            conn.commit()
            conn.close()
            st.success("¡Control Diario eliminado con éxito!")
            st.query_params.clear()
            st.rerun()

def mostrar_registro_rapido_qr(maquina_qr):
    st.title("📱 Registro Rápido por Código QR")
    st.markdown(f"### 🚜 Máquina Intervenida: **{maquina_qr}**")
    st.write(f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    tab_mant_qr, tab_chk_qr = st.tabs(["🔧 Registrar Mantenimiento", "📋 Control Diario (Check-List)"])
    
    empleados_list_db = cargar_lista_columna("empleados", "Nombre")
    usuario_logueado = st.session_state.get("usuario", "")
    indice_default_op = buscar_coincidencia_empleado(usuario_logueado, empleados_list_db)
        
    with tab_mant_qr:
        with st.form("form_registro_qr"):
            deposito = st.selectbox("Depósito", ["Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"])
            operario = st.selectbox("Técnico Responsable", empleados_list_db, index=indice_default_op, placeholder="Escribe para buscar técnico...")
            tipo = st.selectbox("Tipo de Mantenimiento", ["Correctivo", "Preventivo"])
            
            cf1, cf2 = st.columns(2)
            fecha_inicio = cf1.date_input("Fecha Inicio", datetime.now(), format="DD/MM/YYYY")
            fecha_fin = cf2.date_input("Fecha Finalización", value=fecha_inicio, format="DD/MM/YYYY")
            
            duracion_horas = st.number_input("⏱️ Duración total del trabajo (en Horas)", min_value=0.1, max_value=2000.0, value=1.0, step=0.5, format="%.1f")
            
            st.markdown("##### 🔧 Tareas Realizadas (Selecciona con clics):")
            col1, col2 = st.columns(2)
            t1 = col1.checkbox("Revisión General")
            t2 = col1.checkbox("Lubricación / Engrase")
            t3 = col1.checkbox("Cambio de Aceite")
            t7 = col1.checkbox("Reparación Mecánica")
            t4 = col2.checkbox("Limpieza de Filtros")
            t5 = col2.checkbox("Ajuste de Correas / Pernos")
            t6 = col2.checkbox("Reparación Eléctrica")
            
            detalle_adicional = st.text_input("Observación / Repuestos (opcional)", placeholder="Ej: Se cambió correa trapezoidal AVX13")
            horimetro = st.number_input("Horímetro actual de la máquina (opcional)", min_value=0.0, step=0.1, format="%.1f")
            
            guardar = st.form_submit_button("💾 Registrar Mantenimiento")
            
            if guardar:
                if not operario:
                    st.error("⚠️ Por favor selecciona el técnico responsable.")
                else:
                    tareas = []
                    if t1: tareas.append("Revisión General")
                    if t2: tareas.append("Lubricación/Engrase")
                    if t3: tareas.append("Cambio de Aceite")
                    if t7: tareas.append("Reparación Mecánica")
                    if t4: tareas.append("Limpieza de Filtros")
                    if t5: tareas.append("Ajuste de Correas/Pernos")
                    if t6: tareas.append("Reparación Eléctrica")
                    
                    detalle_final = ", ".join(tareas)
                    if detalle_adicional:
                        if detalle_final:
                            detalle_final += f". Obs: {detalle_adicional}"
                        else:
                            detalle_final = detalle_adicional
                    if not detalle_final:
                        detalle_final = "Mantenimiento preventivo por código QR."
                        
                    hora_ini_str = "08:00"
                    if fecha_fin > fecha_inicio:
                        dias_diff = (fecha_fin - fecha_inicio).days
                        hora_fin_str = f"{fecha_fin.strftime('%d/%m/%Y')} ({duracion_horas:.1f} hs)"
                        detalle_final += f" [Trabajo multipropósito de {dias_diff + 1} días]"
                    else:
                        hora_fin_str = f"{duracion_horas:.1f} hs"
                    
                    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    fecha_actividad = fecha_inicio.strftime("%Y-%m-%d")
                    
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO mantenimientos (Fecha, Maquina, Operario, Tipo, Inicio, Fin, Horimetro, Detalle, Deposito, FechaCreacion, HistorialModificaciones, CreadoPor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (fecha_actividad, maquina_qr, operario, tipo, hora_ini_str, hora_fin_str, horimetro, detalle_final, deposito, fecha_creacion, "Creado desde dispositivo móvil usando Código QR.", st.session_state.get("usuario")))
                    conn.commit()
                    conn.close()
                    
                    st.success("🎉 ¡Mantenimiento registrado con éxito!")
                    st.balloons()
                    st.info("Ya puede continuar en el sistema o cerrar la ventana.")

    with tab_chk_qr:
        mostrar_checklist_diario_qr(maquina_qr, titulo_vis=False)

def mostrar_checklist_diario_qr(maquina_qr, titulo_vis=True):
    if titulo_vis:
        st.title("📋 Control Diario (Check-List)")
        st.markdown(f"### 🚜 Máquina: **{maquina_qr}**")
        st.write(f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
        st.markdown("---")
    
    empleados_list_db = cargar_lista_columna("empleados", "Nombre")
    
    # Intentar pre-seleccionar el usuario logueado si coincide con algún empleado en base de datos (con búsqueda tolerante a acentos/casing)
    usuario_logueado = st.session_state.get("usuario", "")
    indice_default_op = buscar_coincidencia_empleado(usuario_logueado, empleados_list_db)
        
    with st.form("form_checklist_qr"):
        deposito = st.selectbox("Depósito", ["Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"])
        operario = st.selectbox("Técnico Responsable", empleados_list_db, index=indice_default_op, placeholder="Escribe para buscar técnico...")
        horimetro_km = st.text_input("Horómetro / Kilómetros (ej: 2591.3 hs o 087485 km)")
        
        st.subheader("I. ANTES de poner en marcha")
        i_a = st.radio("I.a - Revisar pérdidas de aceite/agua (mangueras radiador)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_b = st.radio("I.b - Revisar / agregar nivel de aceite motor", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_c = st.radio("I.c - Revisar / agregar nivel de agua motor", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_d = st.radio("I.d - Revisar tensión correa", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_e = st.radio("I.e - Revisar presión aire cubiertas", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_f = st.radio("I.f - Revisar tensión correas bomba arena intermedia", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        i_g = st.radio("I.g - Control normal funcionamiento al accionar acople embrague", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        
        st.subheader("II. Poner en marcha (Calentamiento)")
        ii_a = st.radio("II.a - Controlar tablero (relojes / vigía)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        ii_b = st.radio("II.b - Controlar funcionamiento sirena y luces marcha atrás", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        ii_c = st.radio("II.c - Probar encloche embrague en vacío (sin vibración/golpes)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        
        st.subheader("III. Durante la operación (aprox. 1 hora de funcionamiento)")
        iii_a = st.radio("III.a - Revisar mangueras del radiador (calientes)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        iii_b = st.radio("III.b - Revisar temperatura rodamientos intermedia", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        
        st.subheader("IV. Antes del cierre de la jornada (aprox. 15hs)")
        iv_a = st.radio("IV.a - Engrase movimientos balde", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        iv_b = st.radio("IV.b - Engrase movimientos torre", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
        
        st.subheader("📝 Observaciones Adicionales")
        observaciones = st.text_area("Notas / Diagnóstico")
        
        guardar = st.form_submit_button("💾 Guardar Control Diario")
        
        if guardar:
            if not operario:
                st.error("⚠️ Por favor selecciona el técnico responsable.")
            else:
                fecha_actividad = datetime.now().strftime("%Y-%m-%d")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO controles_diarios (
                    Fecha, Maquina, Tecnico, Deposito, Horimetro_KM,
                    I_a_perdidas, I_b_aceite_motor, I_c_agua_motor, I_d_tension_correa, I_e_presion_cubiertas, I_f_correa_bba_arena, I_g_acople_embrague,
                    II_a_tablero, II_b_sirena_luces, II_c_embrague_vacio,
                    III_a_mangueras_rad, III_b_temp_rodamientos,
                    IV_a_engrase_balde, IV_b_engrase_torre,
                    Observaciones, CreadoPor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fecha_actividad, maquina_qr, operario, deposito, horimetro_km,
                    i_a, i_b, i_c, i_d, i_e, i_f, i_g,
                    ii_a, ii_b, ii_c,
                    iii_a, iii_b,
                    iv_a, iv_b,
                    observaciones, st.session_state.get("usuario")
                ))
                conn.commit()
                conn.close()
                
                st.success("🎉 ¡Control Diario guardado con éxito!")
                st.balloons()
                st.info("Ya puede cerrar esta pestaña en su teléfono.")

def mostrar_registro_hidro_qr(prod_pre=None):
    st.title("⛽ Carga de Hidrocarburos por Código QR")
    st.write(f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    empleados_list_db = cargar_lista_columna("empleados", "Nombre")
    maquinas_list_db = cargar_lista_columna("maquinas", "Nombre")
    hidro_list_db = ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"]
    
    usuario_logueado = st.session_state.get("usuario", "")
    indice_default_op = buscar_coincidencia_empleado(usuario_logueado, empleados_list_db)
    
    idx_prod = None
    if prod_pre and prod_pre in hidro_list_db:
        idx_prod = hidro_list_db.index(prod_pre)
        
    with st.form("form_hidro_qr"):
        c1, c2 = st.columns(2)
        movimiento = c1.selectbox("Movimiento", ["Egreso", "Ingreso"])
        producto = c1.selectbox("Tipo de Hidrocarburo", hidro_list_db, index=idx_prod, placeholder="Escribe para buscar tipo...")
        cantidad = c2.number_input("Cantidad (Litros)", min_value=0.0, step=1.0)
        destino = c2.selectbox("Destino", ["Stock Central"] + maquinas_list_db, index=None, placeholder="Escribe para buscar destino...")
        operario = st.selectbox("Responsable / Técnico", empleados_list_db, index=indice_default_op, placeholder="Escribe para buscar responsable...")
        
        btn_guardar = st.form_submit_button("💾 Cargar Registro de Hidrocarburos", use_container_width=True)
        if btn_guardar:
            if not producto:
                st.error("⚠️ Por favor selecciona el tipo de hidrocarburo.")
            elif not destino:
                st.error("⚠️ Por favor selecciona el destino.")
            elif not operario:
                st.error("⚠️ Por favor selecciona el responsable.")
            elif cantidad <= 0:
                st.error("⚠️ Por favor ingresa una cantidad de litros mayor a 0.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                fecha_creacion_hd = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                usr_hd = st.session_state.get("usuario", "Desconocido")
                hist_hd = f"{fecha_creacion_hd} - Registrado por usuario: {usr_hd} (Vía QR)"
                cursor.execute("""
                INSERT INTO hidrocarburos (Fecha, Producto, Movimiento, Cantidad, Destino, Operario, FechaCreacion, HistorialModificaciones, CreadoPor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d"), producto, movimiento, cantidad, destino, operario, fecha_creacion_hd, hist_hd, usr_hd))
                conn.commit()
                conn.close()
                st.success("🎉 ¡Registro de Hidrocarburos guardado con éxito!")
                st.balloons()
                st.info("Ya puede continuar cargando o cerrar la ventana en su teléfono.")

# --- EVALUAR PARÁMETROS DE QUERY (ARRANQUE DE FICHA O REGISTRO QR) ---
query_params = st.query_params
if "id" in query_params:
    detail_id = query_params["id"]
    mostrar_detalle_independiente(detail_id)
    st.stop()
elif "id_chk" in query_params:
    chk_id = query_params["id_chk"]
    mostrar_ficha_checklist_independiente(chk_id)
    st.stop()
elif "qr_maq" in query_params:
    maquina_qr = query_params["qr_maq"]
    mostrar_registro_rapido_qr(maquina_qr)
    st.stop()
elif "qr_checklist" in query_params:
    maquina_qr = query_params["qr_checklist"]
    mostrar_checklist_diario_qr(maquina_qr)
    st.stop()
elif "qr_hidro" in query_params:
    prod_hidro = query_params["qr_hidro"] if query_params["qr_hidro"] != "1" else None
    mostrar_registro_hidro_qr(prod_hidro)
    st.stop()

# Carga de listas para menús desplegables

maquinas_list = cargar_lista_columna("maquinas", "Nombre")
empleados_list = cargar_lista_columna("empleados", "Nombre")
productos_list = cargar_lista_columna("productos", "Nombre")
hidro_list = ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"]

# --- INTERFAZ LATERAL ---
st.sidebar.title("🛠️ GESTIÓN TÉCNICA")
# Se corrigieron los nombres de menú para evitar pantallas en blanco
# Se limitan las opciones del menú de acuerdo al Rol de Acceso (Operario vs Administrador)
user_role = st.session_state.get("rol", "Operario")
if user_role == "Operario":
    opciones_menu = [
        "🔧 Registro de Intervenciones (OT)",
        "⛽ Gestión de Combustibles & Lubricantes",
        "📦 Gestión de Repuestos e Insumos"
    ]
else:
    opciones_menu = [
        "🏠 Inicio - Tablero General",
        "🔧 Registro de Intervenciones (OT)",
        "📋 Reporte Mant. Realizado",
        "📦 Gestión de Repuestos e Insumos",
        "📋 Reporte Movimientos Stock",
        "⛽ Gestión de Combustibles & Lubricantes",
        "📋 Balances & Reportes de Hidrocarburos",
        "📅 Programación & Plan de Mantenimiento (PCM)",
        "⚙️ Datos Maestros & Gestión QR",
        "📥 Exportación Global de Datos"
    ]

menu = st.sidebar.radio("Menú:", opciones_menu)

st.sidebar.divider()
st.sidebar.write(f"👤 Sesión: **{st.session_state['usuario']}**")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state["usuario"] = None
    st.session_state["token"] = None
    st.query_params.clear()
    st.markdown("""
    <img src="x" onerror="
    document.cookie = 'planta_usr=; path=/; max-age=0';
    document.cookie = 'planta_tkn=; path=/; max-age=0';
    localStorage.removeItem('planta_usr');
    localStorage.removeItem('planta_tkn');
    window.location.href = window.location.origin + window.location.pathname;
    " style="display:none;">
    """, unsafe_allow_html=True)
    st.stop()

# --- 1. TABLERO DE CONTROL Y REPORTES (FRACTTAL ONE CMMS COMPACTO) ---
if menu == "🏠 Inicio - Tablero General":
    # Header Banner Compacto
    st.markdown("""
    <div class="fracttal-header">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <h3 class="fracttal-title">🏗️ ARENERAS DE LA CRUZ Y ROZAS S.A.</h3>
                <div class="fracttal-subtitle">Gestión Técnica de Mantenimiento & Control de Flota (CMMS)</div>
            </div>
            <div style="text-align:right;">
                <span class="badge-operativo">🟢 Sistema Operativo</span>
                <span style="font-size:12px; color:#94a3b8; margin-left:8px;">Disponibilidad Flota: <b>98.4%</b></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Cargar datos una sola vez
    df_mant = cargar_datos_db("mantenimientos")
    df_stock = cargar_datos_db("stock")
    df_hidro = cargar_datos_db("hidrocarburos")
    
    # Cálculo de métricas globales
    total_mants_glob = len(df_mant) if not df_mant.empty else 0
    cant_prev_glob = len(df_mant[df_mant['Tipo'] == 'Preventivo']) if not df_mant.empty else 0
    cant_corr_glob = len(df_mant[df_mant['Tipo'] == 'Correctivo']) if not df_mant.empty else 0
    
    def calcular_horas_totales(df):
        if df.empty:
            return 0.0
        def diff_horas(row):
            try:
                str_i = str(row['Inicio']).strip()
                str_f = str(row['Fin']).strip()
                
                # Caso 1: Si incluye "hs" (ej: "48.0 hs" o "120.0 hs")
                if "hs" in str_f.lower():
                    clean_f = str_f.lower().split("hs")[0].split("(")[-1].replace(")", "").strip()
                    return float(clean_f)
                if "hs" in str_i.lower():
                    clean_i = str_i.lower().split("hs")[0].split("(")[-1].replace(")", "").strip()
                    return float(clean_i)
                    
                # Caso 2: Números directos (ej: Inicio="0.0", Fin="24.0")
                if ":" not in str_i and ":" not in str_f:
                    try:
                        val_f = float(str_f)
                        val_i = float(str_i)
                        return max(0.0, val_f - val_i) if val_f >= val_i else val_f
                    except:
                        pass
                        
                # Caso 3: Formato horario HH:MM
                h_i, m_i = map(int, str_i.split(':'))
                h_f, m_f = map(int, str_f.split(':'))
                diff = (h_f * 60 + m_f) - (h_i * 60 + m_i)
                if diff < 0:
                    diff += 24 * 60
                return max(0.0, diff / 60.0)
            except:
                try:
                    return float(row['Fin'])
                except:
                    return 0.0
        return df.apply(diff_horas, axis=1).sum()
        
    horas_taller_glob = calcular_horas_totales(df_mant)
    maquinas_interven_glob = df_mant['Maquina'].nunique() if not df_mant.empty else 0
    
    stock_combustible = {}
    if not df_hidro.empty:
        df_hidro['Val'] = df_hidro.apply(lambda x: x['Cantidad'] if x['Movimiento'] == "Ingreso" else -x['Cantidad'], axis=1)
        stock_combustible = df_hidro.groupby('Producto')['Val'].sum().to_dict()
        
    stock_gasoil_val = stock_combustible.get('Gas-oil', 0.0)

    # 1. FILA DE METRICAS COMPACTAS (4 COLUMNAS EN 1 SOLA FILA ARRIBA)
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    col_k1.metric("Mantenimientos Totales", total_mants_glob)
    col_k2.metric("Horas Taller Acumuladas", f"{horas_taller_glob:,.1f} hs")
    col_k3.metric("Stock Remanente Gas-oil", f"{stock_gasoil_val:,.0f} Lts")
    col_k4.metric("Equipos Intervenidos", maquinas_interven_glob)
    
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # 2. PESTAÑAS ORGANIZADAS Y CENTRADAS (EVITA ESCROLAR)
    tab_matrix, tab_analytics, tab_hidro_summary = st.tabs([
        "🚜 Matriz Visual de Activos & Flota",
        "📊 Analítica de Mantenimiento & KPIs",
        "⛽ Resumen Único de Hidrocarburos"
    ])

    # --- PESTAÑA 1: MATRIZ VISUAL DE ACTIVOS (GRILLA COMPACTA DE 4 COLUMNAS) ---
    with tab_matrix:
        c_search1, c_search2 = st.columns([3, 1])
        search_asset = c_search1.text_input("🔍 Buscar Equipo...", placeholder="Ej: Buque Maria Ana, Michigan, Scania, Saveiro...", label_visibility="collapsed")
        
        equipos_clave = [
            {"nombre": "Buque Maria Ana", "icono": "🚢", "tipo": "Embarcación / Buque", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Buque Malvinas", "icono": "🚢", "tipo": "Embarcación / Buque", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Cargadora Michigan", "icono": "🚜", "tipo": "Maquinaria Pesada", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Cargadora SDLG", "icono": "🚜", "tipo": "Maquinaria Pesada", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Case W20", "icono": "🚜", "tipo": "Pala / Cargadora", "estado": "En Mantenimiento", "badge": "badge-mantenimiento"},
            {"nombre": "Autoelevador Nissan", "icono": "🏗️", "tipo": "Montacargas", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Volkswagen Saveiro", "icono": "🛻", "tipo": "Vehículo Liviano", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Ford Ranger", "icono": "🛻", "tipo": "Vehículo Liviano", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Fiat Strada", "icono": "🛻", "tipo": "Vehículo Liviano", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Intermedia Baigorria", "icono": "⚙️", "tipo": "Bomba / Planta", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Intermedia San Lorenzo", "icono": "⚙️", "tipo": "Bomba / Planta", "estado": "Operativo", "badge": "badge-operativo"},
            {"nombre": "Scania", "icono": "🚛", "tipo": "Propulsor / Camión", "estado": "Operativo", "badge": "badge-operativo"},
        ]
        
        if search_asset and search_asset.strip():
            equipos_filtrados = [e for e in equipos_clave if search_asset.lower() in e["nombre"].lower()]
        else:
            equipos_filtrados = equipos_clave

        user_token_enc = urllib.parse.quote(st.session_state.get("token", ""))
        user_usr_enc = urllib.parse.quote(st.session_state.get("usuario", ""))
        base_url_qr = "https://gestion-en-planta-adlc.streamlit.app"
        cols_matrix = st.columns(4)
        for idx, eq in enumerate(equipos_filtrados):
            c_curr = cols_matrix[idx % 4]
            with c_curr:
                with st.container(border=True):
                    st.markdown(f"**{eq['icono']} {eq['nombre']}**")
                    st.markdown(f"<span class='{eq['badge']}'>🟢 {eq['estado']}</span>", unsafe_allow_html=True)
                    
                    if not df_mant.empty and "Maquina" in df_mant.columns:
                        mants_eq = df_mant[df_mant["Maquina"] == eq["nombre"]]
                        if not mants_eq.empty:
                            ult_m = mants_eq.sort_values(by="Fecha", ascending=False).iloc[0]
                            st.caption(f"Último: {formatear_fecha_visible(ult_m['Fecha'])}")
                        else:
                            st.caption("Sin registros recientes")
                    
                    url_m = f"{base_url_qr}/?qr_maq={urllib.parse.quote(eq['nombre'])}&usr={user_usr_enc}&tkn={user_token_enc}"
                    st.link_button("🔧 Ficha / Mant.", url_m, use_container_width=True)

    # --- PESTAÑA 2: ANALÍTICA DE MANTENIMIENTO ---
    with tab_analytics:
        col_filtro_m, col_filtro_a = st.columns(2)
        meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        anios_disponibles = list(range(datetime.now().year - 2, datetime.now().year + 3))
        
        mes_seleccionado = col_filtro_m.selectbox("Filtrar Mes", ["Todos"] + meses_nombres, index=0)
        anio_seleccionado = col_filtro_a.selectbox("Filtrar Año", ["Todos"] + anios_disponibles, index=0)
        
        df_mant_fil = df_mant.copy()
        if not df_mant_fil.empty:
            df_mant_fil['Fecha_dt'] = pd.to_datetime(df_mant_fil['Fecha'], errors='coerce')
            if mes_seleccionado != "Todos":
                mes_num = meses_nombres.index(mes_seleccionado) + 1
                df_mant_fil = df_mant_fil[df_mant_fil['Fecha_dt'].dt.month == mes_num]
            if anio_seleccionado != "Todos":
                df_mant_fil = df_mant_fil[df_mant_fil['Fecha_dt'].dt.year == int(anio_seleccionado)]
                
        c_chart1, c_chart2 = st.columns([6, 4])
        with c_chart1:
            st.markdown("##### 🚜 Top 10 Máquinas Intervenidas")
            if not df_mant_fil.empty:
                df_grouped = df_mant_fil.groupby(['Maquina', 'Tipo']).size().reset_index(name='Cantidad')
                top_machines = df_mant_fil['Maquina'].value_counts().head(10).index
                df_top = df_grouped[df_grouped['Maquina'].isin(top_machines)]
                
                import plotly.express as px
                fig_bar = px.bar(
                    df_top, 
                    x='Maquina', 
                    y='Cantidad', 
                    color='Tipo',
                    color_discrete_map={'Preventivo': '#10b981', 'Correctivo': '#ef4444'},
                    barmode='stack',
                    category_orders={"Maquina": list(top_machines)}
                )
                fig_bar.update_layout(
                    height=280,
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay mantenimientos en este período.")

        with c_chart2:
            st.markdown("##### 📊 Relación Preventivo vs Correctivo")
            cant_prev = len(df_mant_fil[df_mant_fil['Tipo'] == 'Preventivo']) if not df_mant_fil.empty else 0
            cant_corr = len(df_mant_fil[df_mant_fil['Tipo'] == 'Correctivo']) if not df_mant_fil.empty else 0
            
            import plotly.graph_objects as go
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Preventivo', 'Correctivo'],
                values=[cant_prev, cant_corr],
                hole=.4,
                marker_colors=['#10b981', '#ef4444']
            )])
            fig_pie.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- PESTAÑA 3: RESUMEN ÚNICO DE HIDROCARBUROS ---
    with tab_hidro_summary:
        st.markdown("##### ⛽ Stock Remanente de Hidrocarburos & Lubricantes")
        if not df_hidro.empty:
            hidro_productos = ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"]
            cols_h = st.columns(4)
            for idx, prod in enumerate(hidro_productos):
                stock_val = stock_combustible.get(prod, 0.0)
                unidad = "Lts" if prod != "Grasa de Litio" else "Kg"
                
                alerta_critica = 1500 if prod == "Gas-oil" else 50
                alerta_moderada = 3000 if prod == "Gas-oil" else 100
                
                status_text = "🟢 Normal"
                if stock_val < alerta_critica:
                    status_text = "🔴 Stock Crítico"
                elif stock_val < alerta_moderada:
                    status_text = "🟡 Stock Bajo"
                    
                with cols_h[idx % 4]:
                    with st.container(border=True):
                        st.markdown(f"**{prod}**")
                        st.markdown(f"### {stock_val:,.1f} {unidad}")
                        st.caption(status_text)
        else:
            st.info("No hay registros de movimientos de hidrocarburos.")


# --- 2. MANTENIMIENTO REALIZADO (REGISTRO DE INTERVENCIONES OT) ---
elif menu == "🔧 Registro de Intervenciones (OT)":
    st.header("📝 Registro de Intervención")
    
    tipo_registro = st.radio(
        "Seleccione el tipo de carga:",
        ["🔧 Registrar Mantenimiento Realizado", "📋 Registrar Control Diario (Check-List)"],
        horizontal=True
    )
    
    deposito = st.selectbox(
        "Seleccioná el depósito",
        ["-- Seleccionar --", "Depósito Baigorria", "Depósito San Lorenzo", "Santa Fe"]
    )

    if deposito == "-- Seleccionar --":
        st.info("Seleccioná un depósito para habilitar el panel de registro.")
    elif not maquinas_list or not empleados_list:
        st.warning("⚠️ Primero cargue máquinas y personal en la pestaña Configuración.")
    else:
        if tipo_registro == "🔧 Registrar Mantenimiento Realizado":
            with st.form("form_mant"):
                c1, c2 = st.columns(2)
                fecha_inicio = c1.date_input("Fecha Inicio", datetime.now(), format="DD/MM/YYYY")
                fecha_fin = c2.date_input("Fecha Finalización", value=fecha_inicio, format="DD/MM/YYYY")
                
                usuario_logueado = st.session_state.get("usuario", "")
                indice_default_op = buscar_coincidencia_empleado(usuario_logueado, empleados_list)
                    
                maquina = c1.selectbox("Máquina Intervenida", maquinas_list, index=None, placeholder="Escribe para buscar máquina...")
                operario = c1.selectbox("Técnico Responsable", empleados_list, index=indice_default_op, placeholder="Escribe para buscar técnico...")
                tipo = c2.selectbox("Tipo de Mantenimiento", ["Correctivo", "Preventivo"])
                
                duracion_horas = c2.number_input("⏱️ Duración del Trabajo (en Horas)", min_value=0.1, max_value=2000.0, value=1.0, step=0.5, format="%.1f")
                horimetro = st.number_input("Horímetro actual de la máquina (opcional)", min_value=0.0, step=0.1, format="%.1f")
                
                st.markdown("##### 🔧 Tareas Realizadas (Selecciona con clics):")
                col1, col2 = st.columns(2)
                t1 = col1.checkbox("Revisión General", key="fm_t1")
                t2 = col1.checkbox("Lubricación / Engrase", key="fm_t2")
                t3 = col1.checkbox("Cambio de Aceite", key="fm_t3")
                t7 = col1.checkbox("Reparación Mecánica", key="fm_t7")
                t4 = col2.checkbox("Limpieza de Filtros", key="fm_t4")
                t5 = col2.checkbox("Ajuste de Correas / Pernos", key="fm_t5")
                t6 = col2.checkbox("Reparación Eléctrica", key="fm_t6")
                
                repuestos = st.text_area("Observación / Repuestos usados (opcional)", placeholder="Ej: Se cambiaron retenes, juntas o repuestos...")
                
                if st.form_submit_button("Guardar Registro"):
                    if not maquina:
                        st.error("⚠️ Por favor selecciona la máquina intervenida.")
                    elif not operario:
                        st.error("⚠️ Por favor selecciona el técnico responsable.")
                    else:
                        tareas = []
                        if t1: tareas.append("Revisión General")
                        if t2: tareas.append("Lubricación/Engrase")
                        if t3: tareas.append("Cambio de Aceite")
                        if t7: tareas.append("Reparación Mecánica")
                        if t4: tareas.append("Limpieza de Filtros")
                        if t5: tareas.append("Ajuste de Correas/Pernos")
                        if t6: tareas.append("Reparación Eléctrica")
                        
                        detalle_final = ", ".join(tareas)
                        if repuestos and repuestos.strip():
                            if detalle_final:
                                detalle_final += f". Obs: {repuestos.strip()}"
                            else:
                                detalle_final = repuestos.strip()
                        if not detalle_final:
                            detalle_final = "Mantenimiento realizado."

                        hora_ini_str = "08:00"
                        if fecha_fin > fecha_inicio:
                            dias_diff = (fecha_fin - fecha_inicio).days
                            hora_fin_str = f"{fecha_fin.strftime('%d/%m/%Y')} ({duracion_horas:.1f} hs)"
                            detalle_final += f" [Intervención de {dias_diff + 1} días]"
                        else:
                            hora_fin_str = f"{duracion_horas:.1f} hs"

                        conn = get_connection()
                        cursor = conn.cursor()
                        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("""
                        INSERT INTO mantenimientos (Fecha, Maquina, Operario, Tipo, Inicio, Fin, Horimetro, Detalle, Deposito, FechaCreacion, HistorialModificaciones, CreadoPor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fecha_inicio.strftime("%Y-%m-%d"), maquina, operario, tipo, hora_ini_str, hora_fin_str, horimetro, detalle_final, deposito, fecha_creacion, "Creado desde la aplicación.", st.session_state.get("usuario")))
                        conn.commit()
                        conn.close()
                        st.success("¡Mantenimiento guardado!")
                        st.rerun()
        else:
            # 1. Selección de máquina base (fuera del formulario para respuesta rápida al clic)
            if "maquina_seleccionada_pc" not in st.session_state:
                st.session_state["maquina_seleccionada_pc"] = "Scania"
                
            st.markdown("##### 🚜 Selección Rápida de Equipo Base:")
            cols_base = st.columns(5)
            equipos_base = ["Scania", "Case W20", "Michigan 75", "Toyota 1", "Toyota 2"]
            
            for idx, eq in enumerate(equipos_base):
                es_seleccionado = (st.session_state["maquina_seleccionada_pc"] == eq)
                # Resaltar con una estrella el botón seleccionado
                label_boton = f"⭐ {eq}" if es_seleccionado else eq
                if cols_base[idx].button(label_boton, key=f"btn_base_{eq}", use_container_width=True):
                    st.session_state["maquina_seleccionada_pc"] = eq
                    st.rerun()
            
            # Checkbox para seleccionar otra maquina del catalogo completo
            evaluar_otra = st.checkbox("🔍 Buscar otra máquina del catálogo completo (194 equipos)", 
                                       value=(st.session_state["maquina_seleccionada_pc"] not in equipos_base))
            
            if evaluar_otra:
                maquina_seleccionada = st.selectbox("Máquina / Equipo", maquinas_list, index=None, placeholder="Escribe para buscar...")
                if maquina_seleccionada:
                    st.session_state["maquina_seleccionada_pc"] = maquina_seleccionada
            else:
                maquina_seleccionada = st.session_state["maquina_seleccionada_pc"]
                st.info(f"💡 Evaluando equipo base: **{maquina_seleccionada}** (Todos los puntos inician en 'OK ✔️' por defecto, solo cambia los que tengan fallas)")

            with st.form("form_checklist_pc"):
                c1, c2 = st.columns(2)
                fecha = c1.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")
                usuario_logueado = st.session_state.get("usuario", "")
                indice_default_op = buscar_coincidencia_empleado(usuario_logueado, empleados_list)
                
                # Desplegar la máquina activa no editable dentro del formulario
                st.write(f"🚜 **Equipo a evaluar:** `{maquina_seleccionada or 'Ninguno seleccionado'}`")
                operario = c1.selectbox("Técnico Responsable", empleados_list, index=indice_default_op, placeholder="Escribe para buscar técnico...")
                horimetro_km = c2.text_input("Horómetro / Kilómetros (ej: 2591.3 hs o 087485 km)")
                
                st.subheader("I. ANTES de poner en marcha")
                i_a = st.radio("I.a - Revisar pérdidas de aceite/agua (mangueras radiador)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_b = st.radio("I.b - Revisar / agregar nivel de aceite motor", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_c = st.radio("I.c - Revisar / agregar nivel de agua motor", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_d = st.radio("I.d - Revisar tensión correa", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_e = st.radio("I.e - Revisar presión aire cubiertas", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_f = st.radio("I.f - Revisar tensión correas bomba arena intermedia", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                i_g = st.radio("I.g - Control normal funcionamiento al accionar acople embrague", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                
                st.subheader("II. Poner en marcha (Calentamiento)")
                ii_a = st.radio("II.a - Controlar tablero (relojes / vigía)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                ii_b = st.radio("II.b - Controlar funcionamiento sirena y luces marcha atrás", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                ii_c = st.radio("II.c - Probar encloche embrague en vacío (sin vibración/golpes)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                
                st.subheader("III. Durante la operación (aprox. 1 hora de funcionamiento)")
                iii_a = st.radio("III.a - Revisar mangueras del radiador (calientes)", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                iii_b = st.radio("III.b - Revisar temperatura rodamientos intermedia", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                
                st.subheader("IV. Antes del cierre de la jornada (aprox. 15hs)")
                iv_a = st.radio("IV.a - Engrase movimientos balde", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                iv_b = st.radio("IV.b - Engrase movimientos torre", ["OK ✔️", "No OK ❌", "N/A"], horizontal=True)
                
                st.subheader("📝 Observaciones Adicionales")
                observaciones = st.text_area("Notas / Diagnóstico")
                
                guardar_cd = st.form_submit_button("💾 Guardar Control Diario")
                if guardar_cd:
                    if not maquina_seleccionada:
                        st.error("⚠️ Por favor selecciona la máquina.")
                    elif not operario:
                        st.error("⚠️ Por favor selecciona el técnico responsable.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                        INSERT INTO controles_diarios (
                            Fecha, Maquina, Tecnico, Deposito, Horimetro_KM,
                            I_a_perdidas, I_b_aceite_motor, I_c_agua_motor, I_d_tension_correa, I_e_presion_cubiertas, I_f_correa_bba_arena, I_g_acople_embrague,
                            II_a_tablero, II_b_sirena_luces, II_c_embrague_vacio,
                            III_a_mangueras_rad, III_b_temp_rodamientos,
                            IV_a_engrase_balde, IV_b_engrase_torre,
                            Observaciones, CreadoPor
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            fecha.strftime("%Y-%m-%d"), maquina_seleccionada, operario, deposito, horimetro_km,
                            i_a, i_b, i_c, i_d, i_e, i_f, i_g,
                            ii_a, ii_b, ii_c,
                            iii_a, iii_b,
                            iv_a, iv_b,
                            observaciones, st.session_state.get("usuario")
                        ))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 ¡Control Diario para {maquina_seleccionada} guardado con éxito!")
                        st.balloons()
                        st.rerun()

# --- 3. REPORTE MANTENIMIENTO REALIZADO ---
elif menu == "📋 Reporte Mant. Realizado":
    st.header("📋 Reporte de Actividades e Inspecciones")
    
    tab_mants, tab_checklist = st.tabs(["🔧 Mantenimientos Realizados", "📋 Controles Diarios (Check-List)"])
    
    with tab_mants:
        df_mant = cargar_datos_db("mantenimientos")

        if df_mant.empty:
            st.warning("No hay registros de mantenimiento realizado cargados.")
        else:
            df_mant["Fecha_dt"] = pd.to_datetime(df_mant["Fecha"], errors="coerce")
            depositos = ["Todos"] + sorted([d for d in df_mant["Deposito"].dropna().astype(str).unique() if d])
            tipos = ["Todos"] + sorted([t for t in df_mant["Tipo"].dropna().astype(str).unique() if t])
            maquinas = ["Todos"] + sorted([m for m in df_mant["Maquina"].dropna().astype(str).unique() if m])
            tecnicos = ["Todos"] + sorted([t for t in df_mant["Operario"].dropna().astype(str).unique() if t])

            c1, c2 = st.columns(2)
            filtro_deposito = c1.selectbox("Depósito", depositos)
            filtro_tipo = c2.selectbox("Tipo de mantenimiento", tipos)
            c3, c4 = st.columns(2)
            filtro_maquina = c3.selectbox("Máquina", maquinas)
            filtro_tecnico = c4.selectbox("Técnico responsable", tecnicos)
            c5, c6 = st.columns(2)
            fecha_min = df_mant["Fecha_dt"].min().date() if not df_mant["Fecha_dt"].isnull().all() else datetime.now().date()
            fecha_max = df_mant["Fecha_dt"].max().date() if not df_mant["Fecha_dt"].isnull().all() else datetime.now().date()
            rango_fecha = c5.date_input("Fecha desde", value=fecha_min, format="DD/MM/YYYY")
            rango_hasta = c6.date_input("Fecha hasta", value=fecha_max, format="DD/MM/YYYY")

            df_filtrado = df_mant.copy()
            if filtro_deposito != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Deposito"] == filtro_deposito]
            if filtro_tipo != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Tipo"] == filtro_tipo]
            if filtro_maquina != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Maquina"] == filtro_maquina]
            if filtro_tecnico != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Operario"] == filtro_tecnico]

            df_filtrado = df_filtrado[(df_filtrado["Fecha_dt"] >= pd.Timestamp(rango_fecha)) & (df_filtrado["Fecha_dt"] <= pd.Timestamp(rango_hasta) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]
            df_filtrado = df_filtrado.sort_values(by="Fecha_dt", ascending=False).reset_index(drop=True)
            
            # Usar el ID real de la base de datos para evitar confusiones de numeración
            df_filtrado["N° Registro"] = df_filtrado["id"]

            col_total, col_filtrados = st.columns(2)
            col_total.metric("Total registros", len(df_mant))
            col_filtrados.metric("Registros filtrados", len(df_filtrado))

            # Obtener base_url para links
            config_file = "config_url.json"
            base_url = "https://gestion-en-planta-adlc.streamlit.app"
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        ext_url = data.get("url_externa", "").strip()
                        if ext_url:
                            base_url = ext_url.rstrip("/")
                except:
                    pass

            # Agregar columna virtual para enlace a nueva pestaña en la visualización
            export_df = df_filtrado[["N° Registro"]].copy()
            user_token = urllib.parse.quote(st.session_state.get("token", ""))
            user_usr = urllib.parse.quote(st.session_state.get("usuario", ""))
            export_df["Ficha"] = df_filtrado["id"].apply(lambda x: f"{base_url}/?id={x}&usr={user_usr}&tkn={user_token}")
            export_df["Fecha"] = df_filtrado["Fecha"].apply(formatear_fecha_visible)
            for col in ["Deposito", "Maquina", "Operario", "Tipo", "Inicio", "Fin", "Horimetro", "Detalle"]:
                export_df[col] = df_filtrado[col]

            # Crear copia limpia para exportar a Excel (sin la columna de URL interna Ficha)
            excel_export_df = export_df[["N° Registro", "Fecha", "Deposito", "Maquina", "Operario", "Tipo", "Inicio", "Fin", "Horimetro", "Detalle"]].copy()

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                excel_export_df.to_excel(writer, index=False, sheet_name="Mantenimiento Realizado")
            output.seek(0)
            st.download_button(
                "📥 Exportar filtrados a Excel",
                data=output.getvalue(),
                file_name="mantenimiento_realizado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.caption(f"Registros encontrados: {len(df_filtrado)} (💡 Haz clic en 'Abrir Ficha' de cualquier fila para ver los detalles, editar o eliminar el reporte en una nueva pestaña)")
            
            # Mostrar la tabla con el enlace a nueva pestaña
            st.dataframe(
                export_df,
                column_config={
                    "Ficha": st.column_config.LinkColumn("🔍 Ficha", display_text="Abrir Ficha")
                },
                use_container_width=True,
                hide_index=True
            )
                                
    with tab_checklist:
        st.subheader("📋 Controles Diarios de Equipos Realizados")
        df_cd = cargar_datos_db("controles_diarios")
        
        if df_cd.empty:
            st.info("No hay controles diarios registrados.")
        else:
            df_cd_filtrado = df_cd.copy()
            
            c_f1, c_f2 = st.columns(2)
            maquinas_cd = ["Todos"] + sorted(list(df_cd["Maquina"].dropna().unique()))
            tecnicos_cd = ["Todos"] + sorted(list(df_cd["Tecnico"].dropna().unique()))
            
            filtro_maq_cd = c_f1.selectbox("Filtrar por Máquina", maquinas_cd, key="f_maq_cd")
            filtro_tec_cd = c_f2.selectbox("Filtrar por Técnico", tecnicos_cd, key="f_tec_cd")
            
            if filtro_maq_cd != "Todos":
                df_cd_filtrado = df_cd_filtrado[df_cd_filtrado["Maquina"] == filtro_maq_cd]
            if filtro_tec_cd != "Todos":
                df_cd_filtrado = df_cd_filtrado[df_cd_filtrado["Tecnico"] == filtro_tec_cd]
                
            # Formatear la fecha
            df_cd_sorted = df_cd_filtrado.sort_values(by="id", ascending=False).copy()
            df_cd_sorted["Fecha"] = df_cd_sorted["Fecha"].apply(formatear_fecha_visible)
            
            # Obtener base_url para links
            config_file = "config_url.json"
            base_url = "https://gestion-en-planta-adlc.streamlit.app"
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        ext_url = data.get("url_externa", "").strip()
                        if ext_url:
                            base_url = ext_url.rstrip("/")
                except:
                    pass
                    
            # Agregar columna de Enlace Ficha pre-autenticada
            df_cd_tabla = pd.DataFrame()
            user_token = urllib.parse.quote(st.session_state.get("token", ""))
            user_usr = urllib.parse.quote(st.session_state.get("usuario", ""))
            df_cd_tabla["Ficha"] = df_cd_sorted["id"].apply(lambda x: f"{base_url}/?id_chk={x}&usr={user_usr}&tkn={user_token}")
            
            # Copiar las demás columnas en orden
            columnas_ordenadas = ["id", "Fecha", "Maquina", "Tecnico", "Deposito", "Horimetro_KM"]
            inspecciones_cols = [
                "I_a_perdidas", "I_b_aceite_motor", "I_c_agua_motor", "I_d_tension_correa", "I_e_presion_cubiertas", "I_f_correa_bba_arena", "I_g_acople_embrague",
                "II_a_tablero", "II_b_sirena_luces", "II_c_embrague_vacio",
                "III_a_mangueras_rad", "III_b_temp_rodamientos",
                "IV_a_engrase_balde", "IV_b_engrase_torre",
                "Observaciones"
            ]
            for col in columnas_ordenadas + inspecciones_cols:
                df_cd_tabla[col] = df_cd_sorted[col]
                
            # Renombrar columnas para la visualización de la tabla para que sea más amigable
            df_cd_tabla_renombrado = df_cd_tabla.rename(columns={
                "id": "N° Registro",
                "Horimetro_KM": "Horómetro/KM",
                "I_a_perdidas": "I.a Pérdidas",
                "I_b_aceite_motor": "I.b Aceite Motor",
                "I_c_agua_motor": "I.c Agua Motor",
                "I_d_tension_correa": "I.d Tensión Correa",
                "I_e_presion_cubiertas": "I.e Presión Aire",
                "I_f_correa_bba_arena": "I.f Correa Bba Sand",
                "I_g_acople_embrague": "I.g Acople Embrague",
                "II_a_tablero": "II.a Tablero Relojes",
                "II_b_sirena_luces": "II.b Sirena/Luces",
                "II_c_embrague_vacio": "II.c Embrague Vacío",
                "III_a_mangueras_rad": "III.a Mangueras Rad",
                "III_b_temp_rodamientos": "III.b Rodamientos",
                "IV_a_engrase_balde": "IV.a Engrase Balde",
                "IV_b_engrase_torre": "IV.b Engrase Torre",
                "Observaciones": "Observaciones / Diagnóstico"
            })
            
            # Exportar a Excel (sin la columna de URL Ficha)
            excel_export_cd = df_cd_tabla_renombrado.drop(columns=["Ficha"]).copy()
            output_cd = BytesIO()
            with pd.ExcelWriter(output_cd, engine="openpyxl") as writer:
                excel_export_cd.to_excel(writer, index=False, sheet_name="Controles Diarios")
            output_cd.seek(0)
            st.download_button(
                "📥 Exportar Controles Diarios a Excel",
                data=output_cd.getvalue(),
                file_name="controles_diarios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_dl_cd"
            )
            
            # Mostrar la tabla
            st.dataframe(
                df_cd_tabla_renombrado,
                column_config={
                    "Ficha": st.column_config.LinkColumn("🔍 Ficha", display_text="Abrir Ficha")
                },
                use_container_width=True,
                hide_index=True
            )

# --- 4. PROGRAMACIÓN & PLAN DE MANTENIMIENTO (PCM - FRACTTAL STYLE) ---
elif menu == "📅 Programación & Plan de Mantenimiento (PCM)":
    st.markdown("""
    <div class="fracttal-header">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <h3 class="fracttal-title">📅 PROGRAMACIÓN & PLAN DE MANTENIMIENTO (PCM)</h3>
                <div class="fracttal-subtitle">Gestión de Órdenes de Trabajo Programadas — Preventivos & Correctivos Planificados</div>
            </div>
            <div style="text-align:right;">
                <span class="badge-operativo">⚙️ Módulo PCM Activo</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_p = cargar_datos_db("planificacion")
    
    # Asegurar columnas si faltan en dataframe
    for col_req in ["Tipo", "Prioridad", "Detalle", "Horimetro_Est"]:
        if not df_p.empty and col_req not in df_p.columns:
            df_p[col_req] = ""
            
    # Calcular KPIs del Plan
    total_ots = len(df_p) if not df_p.empty else 0
    df_pendientes = df_p[df_p["Estado"].isin(["Pendiente", "En Ejecución"])] if not df_p.empty and "Estado" in df_p.columns else pd.DataFrame()
    total_pend = len(df_pendientes)
    total_criticas = len(df_pendientes[df_pendientes["Prioridad"].str.contains("Alta", case=False, na=False)]) if not df_pendientes.empty and "Prioridad" in df_pendientes.columns else 0
    total_prev = len(df_pendientes[df_pendientes["Tipo"].str.contains("Preventivo", case=False, na=False)]) if not df_pendientes.empty and "Tipo" in df_pendientes.columns else 0
    total_corr = len(df_pendientes[df_pendientes["Tipo"].str.contains("Correctivo", case=False, na=False)]) if not df_pendientes.empty and "Tipo" in df_pendientes.columns else 0
    
    # 1. FILA DE METRICAS DEL PLAN (KPIS COMPACTOS)
    col_pk1, col_pk2, col_pk3, col_pk4 = st.columns(4)
    col_pk1.metric("OTs Pendientes / En Curso", total_pend)
    col_pk2.metric("Prioridad Alta / Crítica 🚨", total_criticas)
    col_pk3.metric("Preventivos Planificados 🛠️", total_prev)
    col_pk4.metric("Correctivos Programados 🔧", total_corr)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # 2. PESTAÑAS ORGANIZADAS
    tab_ots_activas, tab_nueva_ot, tab_historial_pcm = st.tabs([
        "📋 Programa Activo de Órdenes de Trabajo (OT)",
        "➕ Planificar Nueva Orden de Trabajo (OT)",
        "📜 Historial & Cumplimiento del Plan"
    ])

    # --- PESTAÑA 1: PROGRAMA ACTIVO (TABLERO KANBAN / LISTA DE OTS) ---
    with tab_ots_activas:
        if not df_pendientes.empty:
            c_f1, c_f2, c_f3 = st.columns(3)
            filtro_tipo = c_f1.selectbox("Filtrar Tipo OT", ["Todos", "Preventivo Programado", "Correctivo Programado", "Inspección Periódica"], key="f_pcm_tipo")
            filtro_prio = c_f2.selectbox("Filtrar Prioridad", ["Todas", "🔴 Alta / Crítica", "🟡 Media / Rutina", "🟢 Baja / Mejora"], key="f_pcm_prio")
            filtro_maq = c_f3.selectbox("Filtrar Equipo", ["Todos"] + list(df_pendientes["Maquina"].unique()), key="f_pcm_maq")
            
            df_display = df_pendientes.copy()
            if filtro_tipo != "Todos":
                df_display = df_display[df_display["Tipo"] == filtro_tipo]
            if filtro_prio != "Todas":
                df_display = df_display[df_display["Prioridad"] == filtro_prio]
            if filtro_maq != "Todos":
                df_display = df_display[df_display["Maquina"] == filtro_maq]

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            
            if df_display.empty:
                st.info("No hay Órdenes de Trabajo que coincidan con los filtros seleccionados.")
            else:
                for idx, row in df_display.iterrows():
                    db_id = row['id']
                    prio_val = str(row['Prioridad']) if pd.notna(row['Prioridad']) and str(row['Prioridad']).strip() else "🟡 Media / Rutina"
                    tipo_val = str(row['Tipo']) if pd.notna(row['Tipo']) and str(row['Tipo']).strip() else "Preventivo Programado"
                    estado_val = str(row['Estado']) if pd.notna(row['Estado']) else "Pendiente"
                    
                    badge_prio = "badge-revision" if "Alta" in prio_val else ("badge-mantenimiento" if "Media" in prio_val else "badge-operativo")
                    badge_est = "badge-mantenimiento" if estado_val == "En Ejecución" else "badge-operativo"
                    
                    with st.container(border=True):
                        c_t1, c_t2 = st.columns([3, 1])
                        with c_t1:
                            st.markdown(f"### 🚜 **{row['Maquina']}** — {row['Tarea']}")
                            st.markdown(f"<span class='{badge_prio}'>{prio_val}</span> &nbsp; <span class='badge-operativo'>🛠️ {tipo_val}</span> &nbsp; <span class='{badge_est}'>📌 Estado: {estado_val}</span>", unsafe_allow_html=True)
                            st.caption(f"📅 Fecha Prevista: **{formatear_fecha_visible(row['Fecha_Prog'])}** | 👤 Asignado: **{row['Tecnico'] if row['Tecnico'] else 'Sin asignar'}** | ⏱️ Horímetro Objetivo: **{row['Horimetro_Est'] if pd.notna(row['Horimetro_Est']) and float(row['Horimetro_Est']) > 0 else 'N/A'}**")
                            if pd.notna(row['Detalle']) and str(row['Detalle']).strip():
                                st.write(f"📝 **Detalle & Repuestos:** {row['Detalle']}")
                        
                        with c_t2:
                            st.markdown("**Acciones de Gestión:**")
                            if estado_val == "Pendiente":
                                if st.button("▶️ Iniciar OT", key=f"init_ot_{db_id}", use_container_width=True):
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE planificacion SET Estado = 'En Ejecución' WHERE id = ?", (db_id,))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()
                            
                            with st.popover("✏️ Editar OT"):
                                with st.form(key=f"edit_ot_form_{db_id}"):
                                    st.markdown("##### ✏️ Modificar Orden de Trabajo")
                                    ed_maq = st.selectbox("Máquina", maquinas_list, index=maquinas_list.index(row['Maquina']) if row['Maquina'] in maquinas_list else 0)
                                    ed_tarea = st.text_input("Título / Tarea", value=str(row['Tarea']))
                                    ed_tipo = st.selectbox("Tipo", ["Preventivo Programado", "Correctivo Programado", "Inspección Periódica"], index=["Preventivo Programado", "Correctivo Programado", "Inspección Periódica"].index(tipo_val) if tipo_val in ["Preventivo Programado", "Correctivo Programado", "Inspección Periódica"] else 0)
                                    ed_prio = st.selectbox("Prioridad", ["🔴 Alta / Crítica", "🟡 Media / Rutina", "🟢 Baja / Mejora"], index=["🔴 Alta / Crítica", "🟡 Media / Rutina", "🟢 Baja / Mejora"].index(prio_val) if prio_val in ["🔴 Alta / Crítica", "🟡 Media / Rutina", "🟢 Baja / Mejora"] else 1)
                                    ed_fecha = st.date_input("Fecha Prevista", value=pd.to_datetime(row['Fecha_Prog']).date() if pd.notna(row['Fecha_Prog']) else datetime.now().date(), format="DD/MM/YYYY")
                                    ed_tech = st.selectbox("Técnico Asignado", empleados_list, index=empleados_list.index(row['Tecnico']) if row['Tecnico'] in empleados_list else 0)
                                    ed_det = st.text_area("Detalle & Repuestos", value=str(row['Detalle']) if pd.notna(row['Detalle']) else "")
                                    
                                    if st.form_submit_button("💾 Guardar Cambios"):
                                        conn = get_connection()
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                        UPDATE planificacion SET
                                            Maquina = ?, Tarea = ?, Tipo = ?, Prioridad = ?, Fecha_Prog = ?, Tecnico = ?, Detalle = ?
                                        WHERE id = ?
                                        """, (ed_maq, ed_tarea.strip(), ed_tipo, ed_prio, ed_fecha.strftime("%Y-%m-%d"), ed_tech, ed_det.strip(), db_id))
                                        conn.commit()
                                        conn.close()
                                        st.success("¡Orden de Trabajo modificada con éxito!")
                                        st.rerun()

                            with st.popover("✅ Marcar Realizado"):
                                tech_realizo = st.selectbox("Técnico que ejecutó", empleados_list, key=f"tech_exec_{db_id}")
                                obs_ejec = st.text_input("Observación final", placeholder="Ej: Se completó según especificación", key=f"obs_exec_{db_id}")
                                if st.button("💾 Confirmar Cierre OT", key=f"confirm_close_{db_id}"):
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                                    cursor.execute("""
                                    UPDATE planificacion SET
                                        Estado = 'Realizado',
                                        Fecha_Fin = ?,
                                        Tecnico = ?
                                    WHERE id = ?
                                    """, (fecha_hoy, tech_realizo, db_id))
                                    
                                    det_auto = f"[PCM] {row['Tarea']}"
                                    if obs_ejec.strip():
                                        det_auto += f". Obs: {obs_ejec.strip()}"
                                    fecha_c = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    cursor.execute("""
                                    INSERT INTO mantenimientos (Fecha, Maquina, Operario, Tipo, Inicio, Fin, Horimetro, Detalle, Deposito, FechaCreacion, HistorialModificaciones, CreadoPor)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (fecha_hoy, row['Maquina'], tech_realizo, "Preventivo" if "Preventivo" in tipo_val else "Correctivo", "08:00", "1.0 hs", float(row['Horimetro_Est']) if pd.notna(row['Horimetro_Est']) else 0.0, det_auto, "Depósito Baigorria", fecha_c, "Ejecutado desde Planificación PCM.", st.session_state.get("usuario")))
                                    conn.commit()
                                    conn.close()
                                    st.success("¡OT completada y registrada en el historial!")
                                    st.rerun()
                                    
                            if st.button("❌ Cancelar OT", key=f"cancel_ot_{db_id}", use_container_width=True):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE planificacion SET Estado = 'Cancelado' WHERE id = ?", (db_id,))
                                conn.commit()
                                conn.close()
                                st.rerun()
        else:
            st.info("🟢 No hay Órdenes de Trabajo pendientes en el programa de mantenimiento.")

    # --- PESTAÑA 2: PLANIFICAR NUEVA ORDEN DE TRABAJO (OT) ---
    with tab_nueva_ot:
        st.markdown("##### ➕ Formulario de Planificación Técnica (PCM)")
        with st.form("form_nueva_ot_pcm"):
            c_p1, c_p2 = st.columns(2)
            maq_ot = c_p1.selectbox("Máquina / Activo Destino", maquinas_list, placeholder="Escriba para buscar equipo...")
            tipo_ot = c_p2.selectbox("Tipo de Intervención", ["Preventivo Programado", "Correctivo Programado", "Inspección Periódica"])
            
            c_p3, c_p4 = st.columns(2)
            prio_ot = c_p3.selectbox("Prioridad de Atención", ["🟡 Media / Rutina", "🔴 Alta / Crítica", "🟢 Baja / Mejora"])
            fecha_prog_ot = c_p4.date_input("Fecha Prevista de Ejecución", datetime.now(), format="DD/MM/YYYY")
            
            c_p5, c_p6 = st.columns(2)
            tech_asig_ot = c_p5.selectbox("Técnico Responsable Asignado", empleados_list, index=0 if empleados_list else None)
            horim_est_ot = c_p6.number_input("Horímetro Objetivo Estimado (opcional)", min_value=0.0, step=0.1, format="%.1f")
            
            tarea_ot = st.text_input("Título de la Tarea / OT", placeholder="Ej: Cambio de aceite de motor y filtros 500 hrs")
            detalle_ot = st.text_area("Descripción detallada del Trabajo & Repuestos Previstos", placeholder="Ej: Traer 20L de aceite Shell Rimula 15W40, filtro de aceite W950 y filtro de combustible...")
            
            btn_guardar_ot = st.form_submit_button("📅 Programar Orden de Trabajo")
            
            if btn_guardar_ot:
                if not maq_ot:
                    st.error("⚠️ Por favor selecciona la máquina o activo destino.")
                elif not tarea_ot.strip():
                    st.error("⚠️ Por favor escribe el título de la tarea u orden de trabajo.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO planificacion (Maquina, Tarea, Fecha_Prog, Estado, Fecha_Fin, Tecnico, Tipo, Prioridad, Detalle, Horimetro_Est)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (maq_ot, tarea_ot.strip(), fecha_prog_ot.strftime("%Y-%m-%d"), "Pendiente", "", tech_asig_ot, tipo_ot, prio_ot, detalle_ot.strip(), horim_est_ot))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 Orden de Trabajo programada con éxito para {maq_ot}.")
                    st.rerun()

    # --- PESTAÑA 3: HISTORIAL DE CUMPLIMIENTO ---
    with tab_historial_pcm:
        st.markdown("##### 📜 Historial de Órdenes de Trabajo Ejecutadas & Canceladas")
        if not df_p.empty:
            df_hist_pcm = df_p[df_p["Estado"].isin(["Realizado", "Cancelado"])]
            if not df_hist_pcm.empty:
                st.dataframe(
                    df_hist_pcm[["Fecha_Prog", "Fecha_Fin", "Maquina", "Tarea", "Tipo", "Prioridad", "Estado", "Tecnico"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay registros en el historial de planificaciones completadas.")
        else:
            st.info("No hay registros de planificación.")

# --- 5. GESTIÓN DE REPUESTOS E INSUMOS ---
elif menu == "📦 Gestión de Repuestos e Insumos":
    st.header("📦 Movimientos de Stock")
    with st.form("f_stock"):
        c1, c2 = st.columns(2)
        tipo_m = c1.selectbox("Acción", ["Ingreso", "Egreso"])
        prod = c1.selectbox("Producto", productos_list, index=None, placeholder="Escribe para buscar producto...")
        cant = c2.number_input("Cantidad", min_value=0.0)
        dest = c2.text_input("Ubicación / Destino")
        if st.form_submit_button("Registrar"):
            if not prod:
                st.error("⚠️ Por favor selecciona un producto.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                fecha_creacion_stk = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                usr_stk = st.session_state.get("usuario", "Desconocido")
                hist_stk = f"{fecha_creacion_stk} - Registrado por usuario: {usr_stk}"
                cursor.execute("""
                INSERT INTO stock (Fecha, Producto, Movimiento, Cantidad, Destino, FechaCreacion, HistorialModificaciones, CreadoPor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d"), prod, tipo_m, cant, dest, fecha_creacion_stk, hist_stk, usr_stk))
                conn.commit()
                conn.close()
                st.success("Stock actualizado.")

# --- 5.5. REPORTE DE MOVIMIENTOS DE STOCK (REPUESTOS E INSUMOS) ---
elif menu == "📋 Reporte Movimientos Stock":
    st.header("📋 Detalle de Movimientos de Stock (Repuestos e Insumos)")
    
    # Cargar datos
    df_s = cargar_datos_db("stock")
    
    if df_s.empty:
        st.warning("No se encontraron registros de movimientos de stock.")
    else:
        # Cálculo de Stock Remanente
        df_s['Aux_Cant'] = df_s.apply(lambda x: x['Cantidad'] if x['Movimiento'] == "Ingreso" else -x['Cantidad'], axis=1)
        stock_actual = df_s.groupby('Producto')['Aux_Cant'].sum().reset_index()
        stock_actual.columns = ['Producto', 'Stock Remanente']
        
        # Mostrar Resumen de Stock
        st.subheader("📦 Resumen de Stock Remanente")
        stock_actual = stock_actual.fillna("")
        st.dataframe(stock_actual, use_container_width=True, hide_index=True)
        
        st.divider()
        
        st.subheader("🔍 Historial Detallado")
        
        # Parsear fecha a datetime para filtros de mes y año
        df_s['Fecha_dt'] = pd.to_datetime(df_s['Fecha'], errors='coerce')
        df_s['Año'] = df_s['Fecha_dt'].dt.year.fillna(0).astype(int)
        df_s['Mes_num'] = df_s['Fecha_dt'].dt.month.fillna(0).astype(int)
        
        nombres_meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
            0: "Sin fecha"
        }
        df_s['Mes'] = df_s['Mes_num'].map(nombres_meses)
        
        # Filtros
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        filtro_prod = col_f1.multiselect("Filtrar por Producto", productos_list)
        filtro_mov = col_f2.selectbox("Movimiento", ["Todos", "Ingreso", "Egreso"], key="mov_stock_filter")
        
        anios_disponibles = sorted([str(y) for y in df_s['Año'].unique() if y > 0], reverse=True)
        filtro_anio = col_f3.selectbox("Año", ["Todos"] + anios_disponibles, key="anio_stock_filter")
        
        filtro_mes = col_f4.selectbox("Mes", ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], key="mes_stock_filter")
        
        df_mostrar = df_s.copy()
        if filtro_prod:
            df_mostrar = df_mostrar[df_mostrar['Producto'].isin(filtro_prod)]
        if filtro_mov != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Movimiento'] == filtro_mov]
        if filtro_anio != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Año'] == int(filtro_anio)]
        if filtro_mes != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Mes'] == filtro_mes]
            
        # Calcular métricas del período filtrado
        ingresos_periodo = df_mostrar[df_mostrar['Movimiento'] == "Ingreso"]['Cantidad'].sum()
        egresos_periodo = df_mostrar[df_mostrar['Movimiento'] == "Egreso"]['Cantidad'].sum()
        balance_periodo = ingresos_periodo - egresos_periodo
        
        st.markdown("##### 📊 Balance del Período Filtrado:")
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Ingresos en Período", f"{ingresos_periodo:,.1f} Uds")
        cm2.metric("Egresos en Período", f"{egresos_periodo:,.1f} Uds")
        cm3.metric("Balance Período", f"{balance_periodo:,.1f} Uds", delta=f"{balance_periodo:,.1f}", delta_color="normal" if balance_periodo >= 0 else "inverse")
        
        st.divider()
        
        # Formatear y mostrar la tabla ordenada
        df_mostrar_sorted = df_mostrar.sort_values(by="Fecha", ascending=False).copy()
        df_mostrar_sorted["Fecha"] = df_mostrar_sorted["Fecha"].apply(formatear_fecha_visible)
        df_mostrar_sorted = df_mostrar_sorted.fillna("")

        st.markdown("##### 🔍 Historial de Movimientos de Stock")
        opciones_editar_s = ["-- Ver Tabla Completa --"] + [f"ID {r['id']} | {formatear_fecha_visible(r['Fecha'])} | {r['Producto']} | {r['Movimiento']} ({r['Cantidad']} Uds) | {r['Destino']}" for _, r in df_mostrar.sort_values(by='id', ascending=False).iterrows()]
        registro_a_editar = st.selectbox("✏️ Seleccioná un registro de stock para editarlo o eliminarlo:", opciones_editar_s, key="sel_stock_direct")
        
        if registro_a_editar != "-- Ver Tabla Completa --":
            db_id = int(registro_a_editar.split(" | ")[0].replace("ID ", ""))
            row = df_s[df_s['id'] == db_id].iloc[0]
            
            with st.container(border=True):
                st.subheader(f"✏️ Editar / 🗑️ Eliminar Registro de Stock #{db_id}")
                creador_s = row.get('CreadoPor') if pd.notna(row.get('CreadoPor')) and str(row.get('CreadoPor')).strip() != "" else "Desconocido"
                fecha_crea_s = formatear_fecha_hora_visible(row.get('FechaCreacion')) if pd.notna(row.get('FechaCreacion')) and str(row.get('FechaCreacion')).strip() != "" else "N/A"
                st.info(f"👤 **Primera Carga por:** {creador_s} | 📅 **Fecha/Hora de Carga:** {fecha_crea_s}")

                historial_stk = str(row.get('HistorialModificaciones', '')).strip() if pd.notna(row.get('HistorialModificaciones')) else ""
                if historial_stk:
                    with st.expander("📜 Historial de Modificaciones y Auditoría"):
                        st.text(historial_stk)

                with st.form(f"form_edit_stock_{db_id}"):
                    c_ed1, c_ed2 = st.columns(2)
                    edit_fecha = c_ed1.date_input("Fecha", pd.to_datetime(row['Fecha']).date(), format="DD/MM/YYYY")
                    edit_prod = c_ed1.text_input("Nombre del Producto / Repuesto", value=str(row['Producto']))
                    edit_mov = c_ed2.selectbox("Movimiento", ["Ingreso", "Egreso"], index=0 if row['Movimiento'] == "Ingreso" else 1)
                    edit_cant = c_ed2.number_input("Cantidad", value=float(row['Cantidad']), min_value=0.0)
                    edit_dest = st.text_input("Destino / Ubicación", value=str(row['Destino']))
                    
                    pass_stk = st.text_input("🔑 Contraseña para confirmar cambio o eliminación", type="password")

                    col_b1, col_b2 = st.columns(2)
                    btn_save = col_b1.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    btn_delete = col_b2.form_submit_button("🗑️ Eliminar Registro", use_container_width=True)
                    
                    if btn_save:
                        usr_act = st.session_state.get("usuario", "")
                        if not verificar_password_usuario(usr_act, pass_stk):
                            st.error("🔒 Contraseña incorrecta o no ingresada. No se guardaron los cambios.")
                        elif not edit_prod.strip():
                            st.error("⚠️ El nombre del producto no puede estar vacío.")
                        else:
                            cambios_s = []
                            if str(row['Fecha']) != edit_fecha.strftime("%Y-%m-%d"):
                                cambios_s.append(f"Fecha: '{row['Fecha']}' -> '{edit_fecha.strftime('%Y-%m-%d')}'")
                            if str(row['Producto']) != edit_prod.strip():
                                cambios_s.append(f"Producto: '{row['Producto']}' -> '{edit_prod.strip()}'")
                            if str(row['Movimiento']) != edit_mov:
                                cambios_s.append(f"Movimiento: '{row['Movimiento']}' -> '{edit_mov}'")
                            if float(row['Cantidad']) != float(edit_cant):
                                cambios_s.append(f"Cantidad: {row['Cantidad']} -> {edit_cant}")
                            if str(row['Destino']) != edit_dest.strip():
                                cambios_s.append(f"Destino: '{row['Destino']}' -> '{edit_dest.strip()}'")
                            
                            log_fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            usr_str = usr_act if usr_act else "Usuario"
                            detalle_c = ", ".join(cambios_s) if cambios_s else "Sin cambios"
                            nuevo_log = f"{log_fecha} - Modificado por usuario {usr_str}: {detalle_c}"
                            hist_act = str(row.get('HistorialModificaciones', '')) if pd.notna(row.get('HistorialModificaciones')) else ""
                            nuevo_hist = (hist_act + "\n" + nuevo_log).strip()

                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                            UPDATE stock SET
                                Fecha = ?, Producto = ?, Movimiento = ?, Cantidad = ?, Destino = ?, HistorialModificaciones = ?
                            WHERE id = ?
                            """, (edit_fecha.strftime("%Y-%m-%d"), edit_prod.strip(), edit_mov, edit_cant, edit_dest.strip(), nuevo_hist, db_id))
                            conn.commit()
                            conn.close()
                            st.success("¡Registro de stock actualizado con éxito!")
                            st.rerun()
                            
                    if btn_delete:
                        usr_act = st.session_state.get("usuario", "")
                        if not verificar_password_usuario(usr_act, pass_stk):
                            st.error("🔒 Contraseña incorrecta o no ingresada. No se pudo eliminar el registro.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM stock WHERE id = ?", (db_id,))
                            conn.commit()
                            conn.close()
                            st.success("¡Registro de stock eliminado con éxito!")
                            st.rerun()
        else:
            # Sanitizar strings para que jamás se genere un badge nulo en Streamlit
            df_mostrar_sorted["Producto"] = df_mostrar_sorted["Producto"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")
            df_mostrar_sorted["Movimiento"] = df_mostrar_sorted["Movimiento"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")
            df_mostrar_sorted["Destino"] = df_mostrar_sorted["Destino"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")

            st.dataframe(
                df_mostrar_sorted[["Fecha", "Producto", "Movimiento", "Cantidad", "Destino"]],
                column_config={
                    "Fecha": st.column_config.TextColumn("Fecha"),
                    "Producto": st.column_config.TextColumn("Producto"),
                    "Movimiento": st.column_config.TextColumn("Movimiento"),
                    "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.1f"),
                    "Destino": st.column_config.TextColumn("Destino / Ubicación"),
                },
                use_container_width=True,
                hide_index=True
            )

# --- 6. GESTIÓN DE COMBUSTIBLES & LUBRICANTES ---
elif menu == "⛽ Gestión de Combustibles & Lubricantes":
    st.header("⛽ Gestión de Combustibles & Lubricantes")
    with st.form("f_hidro"):
        c1, c2 = st.columns(2)
        t_m = c1.selectbox("Movimiento", ["Ingreso", "Egreso"])
        prod_h = c1.selectbox("Tipo", hidro_list, index=None, placeholder="Escribe para buscar tipo...")
        cant_h = c2.number_input("Litros", min_value=0.0)
        dest_h = c2.selectbox("Destino", ["Stock Central"] + maquinas_list, index=None, placeholder="Escribe para buscar destino...")
        oper_h = st.selectbox("Responsable", empleados_list, index=None, placeholder="Escribe para buscar responsable...")
        if st.form_submit_button("Cargar Registro"):
            if not prod_h:
                st.error("⚠️ Por favor selecciona el tipo de hidrocarburo.")
            elif not dest_h:
                st.error("⚠️ Por favor selecciona el destino.")
            elif not oper_h:
                st.error("⚠️ Por favor selecciona el responsable.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                fecha_creacion_hd = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                usr_hd = st.session_state.get("usuario", "Desconocido")
                hist_hd = f"{fecha_creacion_hd} - Registrado por usuario: {usr_hd}"
                cursor.execute("""
                INSERT INTO hidrocarburos (Fecha, Producto, Movimiento, Cantidad, Destino, Operario, FechaCreacion, HistorialModificaciones, CreadoPor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d"), prod_h, t_m, cant_h, dest_h, oper_h, fecha_creacion_hd, hist_hd, usr_hd))
                conn.commit()
                conn.close()
                st.success("Registrado.")

# --- 7. BALANCES & REPORTES DE HIDROCARBUROS ---
elif menu == "📋 Balances & Reportes de Hidrocarburos":
    st.header("📋 Detalle de Movimientos de Hidrocarburos")
    
    # Cargar datos
    df_h = cargar_datos_db("hidrocarburos")
    
    if df_h.empty:
        st.warning("No se encontraron registros de movimientos de hidrocarburos.")
    else:
        # Cálculo de Stock Remanente para el encabezado
        df_h['Aux_Cant'] = df_h.apply(lambda x: x['Cantidad'] if x['Movimiento'] == "Ingreso" else -x['Cantidad'], axis=1)
        stock_actual = df_h.groupby('Producto')['Aux_Cant'].sum().reset_index()
        stock_actual.columns = ['Producto', 'Stock Remanente (Ltrs)']

        # Mostrar Resumen de Stock
        st.subheader("📦 Resumen de Stock Remanente")
        stock_actual = stock_actual.fillna("")
        st.dataframe(stock_actual, use_container_width=True, hide_index=True)

        st.divider()

        # Mostrar Detalle Completo
        st.subheader("🔍 Historial Detallado")
        
        # Parsear fecha a datetime para filtros de mes y año
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        df_h['Año'] = df_h['Fecha_dt'].dt.year.fillna(0).astype(int)
        df_h['Mes_num'] = df_h['Fecha_dt'].dt.month.fillna(0).astype(int)
        
        nombres_meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
            0: "Sin fecha"
        }
        df_h['Mes'] = df_h['Mes_num'].map(nombres_meses)
        
        # Filtros opcionales para facilitar la lectura
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        filtro_prod = col_f1.multiselect("Filtrar por Producto", ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"], default=["Gas-oil"])
        filtro_mov = col_f2.selectbox("Movimiento", ["Todos", "Ingreso", "Egreso"])
        
        anios_disponibles = sorted([str(y) for y in df_h['Año'].unique() if y > 0], reverse=True)
        filtro_anio = col_f3.selectbox("Año", ["Todos"] + anios_disponibles)
        
        filtro_mes = col_f4.selectbox("Mes", ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])

        df_mostrar = df_h.copy()
        if filtro_prod:
            df_mostrar = df_mostrar[df_mostrar['Producto'].isin(filtro_prod)]
        if filtro_mov != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Movimiento'] == filtro_mov]
        if filtro_anio != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Año'] == int(filtro_anio)]
        if filtro_mes != "Todos":
            df_mostrar = df_mostrar[df_mostrar['Mes'] == filtro_mes]

        # Calcular métricas del período filtrado (Las "otras métricas" solicitadas)
        ingresos_periodo = df_mostrar[df_mostrar['Movimiento'] == "Ingreso"]['Cantidad'].sum()
        egresos_periodo = df_mostrar[df_mostrar['Movimiento'] == "Egreso"]['Cantidad'].sum()
        balance_periodo = ingresos_periodo - egresos_periodo
        
        st.markdown("##### 📊 Balance del Período Filtrado:")
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Ingresos en Período", f"{ingresos_periodo:,.1f} Lts/Uds")
        cm2.metric("Consumos en Período", f"{egresos_periodo:,.1f} Lts/Uds")
        cm3.metric("Balance Período", f"{balance_periodo:,.1f} Lts/Uds", delta=f"{balance_periodo:,.1f}", delta_color="normal" if balance_periodo >= 0 else "inverse")
        
        st.divider()

        # Formatear y mostrar la tabla ordenada
        df_mostrar_sorted = df_mostrar.sort_values(by="Fecha", ascending=False).copy()
        df_mostrar_sorted["Fecha"] = df_mostrar_sorted["Fecha"].apply(formatear_fecha_visible)
        df_mostrar_sorted = df_mostrar_sorted.fillna("")

        # Selector directo sobre la lista de registros
        st.markdown("##### 🔍 Historial de Movimientos")
        opciones_editar_h = ["-- Ver Tabla Completa --"] + [f"ID {r['id']} | {formatear_fecha_visible(r['Fecha'])} | {r['Producto']} | {r['Movimiento']} ({r['Cantidad']} Lts) | {r['Destino']}" for _, r in df_mostrar.sort_values(by='id', ascending=False).iterrows()]
        registro_a_editar_h = st.selectbox("✏️ Seleccioná un registro de la lista para editarlo o eliminarlo:", opciones_editar_h, key="sel_hidro_direct")
        
        if registro_a_editar_h != "-- Ver Tabla Completa --":
            db_id_h = int(registro_a_editar_h.split(" | ")[0].replace("ID ", ""))
            row_h = df_h[df_h['id'] == db_id_h].iloc[0]
            
            with st.container(border=True):
                st.subheader(f"✏️ Editar / 🗑️ Eliminar Movimiento #{db_id_h}")
                creador_h = row_h.get('CreadoPor') if pd.notna(row_h.get('CreadoPor')) and str(row_h.get('CreadoPor')).strip() != "" else "Desconocido"
                fecha_crea_h = formatear_fecha_hora_visible(row_h.get('FechaCreacion')) if pd.notna(row_h.get('FechaCreacion')) and str(row_h.get('FechaCreacion')).strip() != "" else "N/A"
                st.info(f"👤 **Primera Carga por:** {creador_h} | 📅 **Fecha/Hora de Carga:** {fecha_crea_h}")

                historial_hd = str(row_h.get('HistorialModificaciones', '')).strip() if pd.notna(row_h.get('HistorialModificaciones')) else ""
                if historial_hd:
                    with st.expander("📜 Historial de Modificaciones y Auditoría"):
                        st.text(historial_hd)

                with st.form(f"form_edit_hidro_{db_id_h}"):
                    c_edh1, c_edh2 = st.columns(2)
                    edit_fecha_h = c_edh1.date_input("Fecha", pd.to_datetime(row_h['Fecha']).date(), format="DD/MM/YYYY")
                    edit_prod_h = c_edh1.selectbox("Tipo de Hidrocarburo", ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"], 
                                                   index=["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"].index(row_h['Producto']) if row_h['Producto'] in ["Gas-oil", "Aceite Motor 15W40", "Hidráulico 68", "Grasa de Litio"] else 0)
                    edit_mov_h = c_edh2.selectbox("Movimiento", ["Ingreso", "Egreso"], index=0 if row_h['Movimiento'] == "Ingreso" else 1)
                    edit_cant_h = c_edh2.number_input("Cantidad (Litros)", value=float(row_h['Cantidad']), min_value=0.0)
                    
                    edit_dest_h = st.selectbox("Destino", ["Stock Central"] + maquinas_list, 
                                               index=(["Stock Central"] + maquinas_list).index(row_h['Destino']) if row_h['Destino'] in (["Stock Central"] + maquinas_list) else 0)
                    edit_oper_h = st.selectbox("Responsable", ["-- Sin especificar --"] + empleados_list, 
                                               index=(["-- Sin especificar --"] + empleados_list).index(row_h['Operario']) if row_h['Operario'] in (["-- Sin especificar --"] + empleados_list) else 0)
                    
                    pass_hidro = st.text_input("🔑 Contraseña para confirmar cambio o eliminación", type="password")

                    col_bh1, col_bh2 = st.columns(2)
                    btn_save_h = col_bh1.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    btn_delete_h = col_bh2.form_submit_button("🗑️ Eliminar Registro", use_container_width=True)
                    
                    if btn_save_h:
                        usr_act = st.session_state.get("usuario", "")
                        if not verificar_password_usuario(usr_act, pass_hidro):
                            st.error("🔒 Contraseña incorrecta o no ingresada. No se guardaron los cambios.")
                        else:
                            cambios_h = []
                            if str(row_h['Fecha']) != edit_fecha_h.strftime("%Y-%m-%d"):
                                cambios_h.append(f"Fecha: '{row_h['Fecha']}' -> '{edit_fecha_h.strftime('%Y-%m-%d')}'")
                            if str(row_h['Producto']) != str(edit_prod_h):
                                cambios_h.append(f"Producto: '{row_h['Producto']}' -> '{edit_prod_h}'")
                            if str(row_h['Movimiento']) != str(edit_mov_h):
                                cambios_h.append(f"Movimiento: '{row_h['Movimiento']}' -> '{edit_mov_h}'")
                            if float(row_h['Cantidad']) != float(edit_cant_h):
                                cambios_h.append(f"Cantidad: {row_h['Cantidad']} -> {edit_cant_h}")
                            if str(row_h['Destino']) != str(edit_dest_h):
                                cambios_h.append(f"Destino: '{row_h['Destino']}' -> '{edit_dest_h}'")
                            op_val = "" if edit_oper_h == "-- Sin especificar --" else edit_oper_h
                            if str(row_h['Operario']) != str(op_val):
                                cambios_h.append(f"Responsable: '{row_h['Operario']}' -> '{op_val}'")
                            
                            log_fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            usr_str = usr_act if usr_act else "Usuario"
                            detalle_c = ", ".join(cambios_h) if cambios_h else "Sin cambios"
                            nuevo_log = f"{log_fecha} - Modificado por usuario {usr_str}: {detalle_c}"
                            hist_act = str(row_h.get('HistorialModificaciones', '')) if pd.notna(row_h.get('HistorialModificaciones')) else ""
                            nuevo_hist = (hist_act + "\n" + nuevo_log).strip()

                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                            UPDATE hidrocarburos SET
                                Fecha = ?, Producto = ?, Movimiento = ?, Cantidad = ?, Destino = ?, Operario = ?, HistorialModificaciones = ?
                            WHERE id = ?
                            """, (edit_fecha_h.strftime("%Y-%m-%d"), edit_prod_h, edit_mov_h, edit_cant_h, edit_dest_h, op_val, nuevo_hist, db_id_h))
                            conn.commit()
                            conn.close()
                            st.success("¡Registro de hidrocarburos actualizado con éxito!")
                            st.rerun()
                            
                    if btn_delete_h:
                        usr_act = st.session_state.get("usuario", "")
                        if not verificar_password_usuario(usr_act, pass_hidro):
                            st.error("🔒 Contraseña incorrecta o no ingresada. No se pudo eliminar el registro.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM hidrocarburos WHERE id = ?", (db_id_h,))
                            conn.commit()
                            conn.close()
                            st.success("¡Registro de hidrocarburos eliminado con éxito!")
                            st.rerun()
        else:
            # Sanitizar strings para que jamás se genere un badge nulo en Streamlit
            df_mostrar_sorted["Producto"] = df_mostrar_sorted["Producto"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")
            df_mostrar_sorted["Movimiento"] = df_mostrar_sorted["Movimiento"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")
            df_mostrar_sorted["Destino"] = df_mostrar_sorted["Destino"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")
            df_mostrar_sorted["Operario"] = df_mostrar_sorted["Operario"].astype(str).apply(lambda x: str(x).strip() if str(x).strip() not in ["None", "nan", ""] else "-")

            st.dataframe(
                df_mostrar_sorted[["Fecha", "Producto", "Movimiento", "Cantidad", "Destino", "Operario"]],
                column_config={
                    "Fecha": st.column_config.TextColumn("Fecha"),
                    "Producto": st.column_config.TextColumn("Producto"),
                    "Movimiento": st.column_config.TextColumn("Movimiento"),
                    "Cantidad": st.column_config.NumberColumn("Cantidad (Lts)", format="%.1f Lts"),
                    "Destino": st.column_config.TextColumn("Destino"),
                    "Operario": st.column_config.TextColumn("Responsable"),
                },
                use_container_width=True,
                hide_index=True
            )

        st.divider()
        st.markdown("##### 📥 Exportar Registros Filtrados para Administración:")
        c_exp1, c_exp2 = st.columns(2)
        
        # 1. Excel
        output_h = BytesIO()
        excel_df_h = df_mostrar_sorted[["Fecha", "Producto", "Movimiento", "Cantidad", "Destino", "Operario"]].copy()
        with pd.ExcelWriter(output_h, engine="openpyxl") as writer:
            excel_df_h.to_excel(writer, index=False, sheet_name="Movimientos Hidrocarburos")
        output_h.seek(0)
        
        c_exp1.download_button(
            "📊 Exportar a Excel (.xlsx)",
            data=output_h.getvalue(),
            file_name=f"Reporte_Hidrocarburos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # 2. PDF Imprimible
        pdf_bytes_h = generar_pdf_hidrocarburos(
            df_mostrar_sorted,
            filtro_prod_str=", ".join(filtro_prod) if filtro_prod else "Todos",
            filtro_mov_str=filtro_mov,
            filtro_anio_str=str(filtro_anio),
            filtro_mes_str=filtro_mes,
            ingresos=ingresos_periodo,
            egresos=egresos_periodo,
            balance=balance_periodo,
            usuario_emisor=st.session_state.get("usuario", "")
        )
        
        c_exp2.download_button(
            "📄 Exportar Reporte a PDF (.pdf)",
            data=pdf_bytes_h,
            file_name=f"Reporte_Hidrocarburos_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- 8. DATOS MAESTROS & GESTIÓN QR ---
elif menu == "⚙️ Datos Maestros & Gestión QR":
    st.header("⚙️ Datos Maestros & Gestión QR")
    
    tab_datos_maestros, tab_usuarios = st.tabs(["📊 Datos Maestros", "👥 Gestión de Usuarios"])
    
    with tab_datos_maestros:
        st.header("⚙️ Configuración de Datos Maestros")
        col1, col2, col3 = st.columns(3)
    
        with col1:
            st.subheader("🚜 Máquinas")
            nueva_m = st.text_input("Añadir Nueva Máquina")
            if st.button("➕ Guardar Máquina"):
                if nueva_m:
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO maquinas (Nombre) VALUES (?)", (nueva_m,))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        st.error("Esa máquina ya está registrada.")
                    finally:
                        conn.close()
                    st.rerun()
        
            st.divider()
            if maquinas_list:
                m_borrar = st.selectbox("Seleccionar Máquina para borrar", ["-- Seleccionar --"] + maquinas_list)
                if st.button("🗑️ Borrar Máquina Seleccionada"):
                    if m_borrar != "-- Seleccionar --":
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM maquinas WHERE Nombre = ?", (m_borrar,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                    
            st.divider()
            st.subheader("📋 Generación de Códigos QR para Máquinas")
        
            import json
            config_file = "config_url.json"
            url_externa_previa = "https://gestion-en-planta-adlc.streamlit.app"
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        if data.get("url_externa", "").strip():
                            url_externa_previa = data.get("url_externa", "").strip()
                except:
                    pass
                
            url_externa = st.text_input(
                "🌐 URL Base de la Aplicación (Dominio en la Nube)", 
                value=url_externa_previa, 
                placeholder="Ej: https://gestion-en-planta-adlc.streamlit.app"
            )
        
            if url_externa != url_externa_previa:
                try:
                    with open(config_file, "w") as f:
                        json.dump({"url_externa": url_externa.strip()}, f)
                except:
                    pass
                
            base_url_qr = url_externa.strip().rstrip("/") if url_externa.strip() else "https://gestion-en-planta-adlc.streamlit.app"

            if maquinas_list:
                st.markdown("##### 📌 Generar QR de una Máquina Individual")
                m_qr = st.selectbox("Seleccionar Máquina para QR", ["-- Seleccionar --"] + maquinas_list)
                if m_qr != "-- Seleccionar --":
                    url_qr = f"{base_url_qr}/?qr_maq={urllib.parse.quote(m_qr)}"
                    api_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(url_qr)}"
                
                    col_q1, col_q2 = st.columns([1, 2])
                    with col_q1:
                        st.image(api_qr, caption=f"QR: {m_qr}")
                    with col_q2:
                        st.markdown(f"#### 🚜 **{m_qr}**")
                        st.write(f"🔗 **Enlace QR:** `{url_qr}`")
                        st.success("💡 **Instrucciones:** Imprimí o pegá este QR en la máquina. Cualquier operario que lo escanee desde su celular podrá registrar el mantenimiento o el check-list diario de este equipo al instante.")
                
                st.divider()
                st.markdown("##### 🖨️ Grilla de Códigos QR de Toda la Planta (Imprimible)")
                if st.checkbox("👁️ Mostrar todos los QR de máquinas juntas para imprimir"):
                    cols_qr = st.columns(3)
                    for idx, maq_name in enumerate(maquinas_list):
                        col_curr = cols_qr[idx % 3]
                        with col_curr:
                            with st.container(border=True):
                                url_maq_item = f"{base_url_qr}/?qr_maq={urllib.parse.quote(maq_name)}"
                                api_qr_item = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(url_maq_item)}"
                                st.markdown(f"**🚜 {maq_name}**")
                                st.image(api_qr_item, use_container_width=True)
                                st.caption(f"Escanear para {maq_name}")

            st.divider()
            st.subheader("⛽ Código QR para Control de Hidrocarburos")
            st.markdown("Imprimí y pegá este código QR en la estación de carga, surtidores o área de lubricantes. Los operarios podrán escanearlo desde sus celulares para registrar cargas de combustible y aceites en tiempo real.")
            
            url_qr_hidro = f"{base_url_qr}/?qr_hidro=1"
            api_qr_hidro = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(url_qr_hidro)}"
            
            col_hq1, col_hq2 = st.columns([1, 2])
            with col_hq1:
                st.image(api_qr_hidro, caption="QR Surtidor de Hidrocarburos")
            with col_hq2:
                st.markdown("#### ⛽ **QR Surtidor / Estación de Servicio**")
                st.write(f"🔗 **Enlace QR:** `{url_qr_hidro}`")
                st.success("💡 **Instrucciones:** Al escanear este QR con cualquier celular, se abrirá el formulario directo para registrar Ingresos y Egresos de Gas-oil, Aceite Motor, Hidráulico o Grasa.")

        with col2:
            st.subheader("👤 Personal")
            nueva_p = st.text_input("Añadir Nuevo Empleado")
            if st.button("➕ Guardar Empleado"):
                if nueva_p:
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO empleados (Nombre) VALUES (?)", (nueva_p,))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        st.error("Ese empleado ya está registrado.")
                    finally:
                        conn.close()
                    st.rerun()
        
            st.divider()
            if empleados_list:
                p_borrar = st.selectbox("Seleccionar Empleado para borrar", ["-- Seleccionar --"] + empleados_list)
                if st.button("🗑️ Borrar Empleado Selected"):
                    if p_borrar != "-- Seleccionar --":
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM empleados WHERE Nombre = ?", (p_borrar,))
                        conn.commit()
                        conn.close()
                        st.rerun()

        with col3:
            st.subheader("📦 Repuestos")
            nuevo_s = st.text_input("Añadir Nuevo Producto")
            if st.button("➕ Guardar Producto"):
                if nuevo_s:
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO productos (Nombre) VALUES (?)", (nuevo_s,))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        st.error("Ese producto ya está registrado.")
                    finally:
                        conn.close()
                    st.rerun()
        
            st.divider()
            if productos_list:
                s_borrar = st.selectbox("Seleccionar Producto para borrar", ["-- Seleccionar --"] + productos_list)
                if st.button("🗑️ Borrar Producto Selected"):
                    if s_borrar != "-- Seleccionar --":
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM productos WHERE Nombre = ?", (s_borrar,))
                        conn.commit()
                        conn.close()
                        st.rerun()


    with tab_usuarios:
        st.subheader("👥 Gestión de Usuarios y Permisos")
        CONTRASENA_MAESTRA = "RozasCruzMaster2026!"
        
        pass_maestra = st.text_input("Contraseña Maestra para gestionar usuarios", type="password", key="pass_maestra_chk")
        
        if pass_maestra:
            if pass_maestra == CONTRASENA_MAESTRA:
                st.success("🔓 Acceso concedido.")
                
                st.subheader("➕ Crear Nuevo Usuario")
                with st.form("form_nuevo_usuario"):
                    nuevo_u = st.text_input("Usuario / Técnico responsable")
                    nuevo_p = st.text_input("Contraseña de Carga", type="password")
                    nuevo_rj = st.text_input("Puesto de Trabajo (Planta y función en la empresa)", placeholder="Ej: Planta San Lorenzo - Mecánico")
                    nuevo_r = st.selectbox("Rol de Acceso", ["Operario", "Administrador"])
                    
                    guardar_u = st.form_submit_button("💾 Guardar Nuevo Usuario")
                    if guardar_u:
                        if not nuevo_u.strip() or not nuevo_p.strip():
                            st.error("⚠️ Por favor completa el usuario y la contraseña.")
                        else:
                            import uuid
                            token_u = uuid.uuid4().hex
                            
                            # Conectar e insertar
                            import sqlite3
                            conn = sqlite3.connect("gestion_planta.db")
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO usuarios (Usuario, Password, Token, Rol, Puesto) VALUES (?, ?, ?, ?, ?)",
                                               (nuevo_u.strip(), nuevo_p.strip(), token_u, nuevo_r, nuevo_rj.strip()))
                                conn.commit()
                                st.success(f"🎉 Usuario '{nuevo_u}' registrado correctamente.")
                            except sqlite3.IntegrityError:
                                st.error("⚠️ Ese nombre de usuario ya existe.")
                            finally:
                                conn.close()
                            st.rerun()
                
                st.divider()
                st.subheader("👥 Usuarios del Sistema")
                import sqlite3
                conn = sqlite3.connect("gestion_planta.db")
                import pandas as pd
                df_users = pd.read_sql_query("SELECT Usuario, Rol, Password, Puesto FROM usuarios", conn)
                conn.close()
                
                if df_users.empty:
                    st.info("No hay usuarios registrados.")
                else:
                    st.dataframe(df_users[["Usuario", "Rol", "Puesto"]], use_container_width=True, hide_index=True)
                    
                    # Sección: Editar Usuario
                    st.divider()
                    st.subheader("📝 Editar Usuario")
                    u_a_editar = st.selectbox("Seleccionar usuario a editar", ["-- Seleccionar --"] + list(df_users["Usuario"]))
                    if u_a_editar != "-- Seleccionar --":
                        user_row = df_users[df_users["Usuario"] == u_a_editar].iloc[0]
                        current_rol = user_row["Rol"]
                        current_pass = user_row["Password"]
                        current_puesto = user_row["Puesto"] if pd.notna(user_row["Puesto"]) else ""
                        
                        with st.form("form_editar_usuario"):
                            edit_u = st.text_input("Nombre de Usuario / Nombre de Técnico", value=u_a_editar)
                            edit_p = st.text_input("Contraseña de Carga", value=current_pass, type="password")
                            edit_rj = st.text_input("Puesto de Trabajo", value=current_puesto)
                            edit_r = st.selectbox("Rol de Acceso", ["Operario", "Administrador"], index=0 if current_rol == "Operario" else 1)
                            
                            guardar_cambios = st.form_submit_button("💾 Guardar Cambios")
                            if guardar_cambios:
                                if not edit_u.strip() or not edit_p.strip():
                                    st.error("⚠️ Por favor completa el usuario y la contraseña.")
                                else:
                                    conn = sqlite3.connect("gestion_planta.db")
                                    cursor = conn.cursor()
                                    try:
                                        # Prohibir cambiar el nombre del admin por defecto
                                        if u_a_editar == "admin" and edit_u.strip() != "admin":
                                            st.error("⚠️ No se puede cambiar el nombre del usuario administrador principal ('admin').")
                                        else:
                                            cursor.execute("""
                                            UPDATE usuarios SET
                                                Usuario = ?, Password = ?, Rol = ?, Puesto = ?
                                            WHERE Usuario = ?
                                            """, (edit_u.strip(), edit_p.strip(), edit_r, edit_rj.strip(), u_a_editar))
                                            conn.commit()
                                            st.success(f"🎉 Cambios guardados para el usuario '{edit_u.strip()}'.")
                                            st.rerun()
                                    except sqlite3.IntegrityError:
                                        st.error("⚠️ Ese nombre de usuario ya existe en otro registro.")
                                    finally:
                                        conn.close()
                    
                    # Sección: Eliminar Usuario
                    st.divider()
                    st.subheader("🗑️ Eliminar Usuario")
                    u_a_borrar = st.selectbox("Seleccionar usuario a eliminar", ["-- Seleccionar --"] + list(df_users["Usuario"]))
                    if st.button("🗑️ Eliminar permanentemente", use_container_width=True):
                        if u_a_borrar != "-- Seleccionar --":
                            if u_a_borrar == "admin":
                                st.error("⚠️ No se puede eliminar el usuario administrador principal ('admin').")
                            else:
                                conn = sqlite3.connect("gestion_planta.db")
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM usuarios WHERE Usuario = ?", (u_a_borrar,))
                                conn.commit()
                                conn.close()
                                st.success(f"Usuario '{u_a_borrar}' eliminado con éxito.")
                                st.rerun()
            else:
                st.error("❌ Contraseña Maestra incorrecta.")

# --- 9. EXPORTACIÓN GLOBAL DE DATOS ---
elif menu == "📥 Exportación Global de Datos":
    st.header("📥 Descargar Reporte Completo")
    st.write("Presione el botón para generar un archivo Excel con todas las tablas de la base de datos.")
    
    if st.button("Generar Archivo Excel"):
        tablas = {
            "maquinas": "maquinas",
            "empleados": "empleados",
            "productos": "productos",
            "mantenimientos": "mantenimientos",
            "planificacion": "planificacion",
            "stock": "stock",
            "hidrocarburos": "hidrocarburos",
            "controles_diarios": "controles_diarios"
        }
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for clave_nombre, tabla_sql in tablas.items():
                df = cargar_datos_db(tabla_sql)
                if not df.empty:
                    df.to_excel(writer, sheet_name=clave_nombre, index=False)
        
        st.download_button(
            label="💾 Descargar Excel",
            data=output.getvalue(),
            file_name=f"Reporte_Gestion_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )