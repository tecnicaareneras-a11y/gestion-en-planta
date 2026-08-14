import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import xlsxwriter
import base64
import os
import json
import math
import numpy as np
from fpdf import FPDF

# Forzamos a Matplotlib a no buscar ventanas gráficas
import matplotlib
matplotlib.use('Agg')

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Laboratorio", layout="wide", page_icon="🧪")

# --- OPTIMIZACIÓN RESPONSIVE MÓVIL ---
st.markdown("""
<style>
@media (max-width: 768px) {
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    .stButton > button {
        width: 100% !important;
        min-height: 2.8rem !important;
        font-size: 1.05rem !important;
        border-radius: 8px !important;
    }
    input {
        font-size: 16px !important;
    }
    div[data-baseweb="select"] {
        font-size: 16px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE RUTAS Y ARCHIVOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo_empresa.png")
PIE_PATH = os.path.join(BASE_DIR, "pie_de_pagina.png")
CORTES_FILE = os.path.join(BASE_DIR, "cortes_config.json")
RAYEN_TOLERANCIAS_FILE = os.path.join(BASE_DIR, "rayen_tolerancias.json")
RAYEN_EQUIPAMIENTO_FILE = os.path.join(BASE_DIR, "rayen_equipamiento.json")
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios.json")

DEFAULT_USUARIOS = {
    "admin": {
        "nombre": "Administrador Maestro",
        "clave": "lab123",
        "rol": "Master"
    },
    "operador": {
        "nombre": "Laboratorista Planta",
        "clave": "operador123",
        "rol": "Operador"
    }
}

# --- DESCARGAR BASE DE DATOS DE GOOGLE DRIVE AL INICIAR ---
@st.cache_resource
def descargar_db_inicial():
    try:
        import gdrive_sync
        success = gdrive_sync.descargar_db_desde_gdrive()
        return {
            "status": "OK" if success else "Error",
            "download_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S") if success else None,
            "error": gdrive_sync.LAST_SYNC["error"] if not success else None
        }
    except Exception as e:
        return {
            "status": "Error",
            "download_time": None,
            "error": str(e)
        }

descargar_db_inicial()

def get_db_connection():
    conn = sqlite3.connect('laboratorio.db', timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except:
        pass
    return conn

def init_tabla_usuarios():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario_id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                clave TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        ''')
        c.execute("SELECT COUNT(*) FROM usuarios")
        if c.fetchone()[0] == 0:
            migrated = False
            if os.path.exists(USUARIOS_FILE):
                try:
                    with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
                        u_dict = json.load(f)
                        for uk, uv in u_dict.items():
                            c.execute("INSERT OR REPLACE INTO usuarios (usuario_id, nombre, clave, rol) VALUES (?, ?, ?, ?)",
                                      (uk.strip().lower(), uv.get("nombre", uk), uv.get("clave", "1234"), uv.get("rol", "Operador")))
                        migrated = True
                except:
                    pass
            if not migrated:
                for uk, uv in DEFAULT_USUARIOS.items():
                    c.execute("INSERT OR REPLACE INTO usuarios (usuario_id, nombre, clave, rol) VALUES (?, ?, ?, ?)",
                              (uk, uv["nombre"], uv["clave"], uv["rol"]))
        conn.commit()
        conn.close()
    except:
        pass

def cargar_usuarios():
    init_tabla_usuarios()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT usuario_id, nombre, clave, rol FROM usuarios")
        rows = c.fetchall()
        conn.close()
        res = {}
        for r in rows:
            res[r[0]] = {"nombre": r[1], "clave": r[2], "rol": r[3]}
        if "admin" not in res:
            res["admin"] = DEFAULT_USUARIOS["admin"]
        return res
    except:
        return dict(DEFAULT_USUARIOS)

def guardar_usuarios(dict_usr):
    init_tabla_usuarios()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT usuario_id FROM usuarios")
        db_ids = set(r[0] for r in c.fetchall())
        current_ids = set(k.strip().lower() for k in dict_usr.keys())
        
        for del_id in (db_ids - current_ids):
            if del_id != "admin":
                c.execute("DELETE FROM usuarios WHERE usuario_id = ?", (del_id,))
                
        for uk, uv in dict_usr.items():
            c.execute("INSERT OR REPLACE INTO usuarios (usuario_id, nombre, clave, rol) VALUES (?, ?, ?, ?)",
                      (uk.strip().lower(), uv.get("nombre", uk), uv.get("clave", ""), uv.get("rol", "Operador")))
        conn.commit()
        conn.close()
        try:
            import gdrive_sync
            gdrive_sync.subir_db_a_gdrive()
        except:
            pass
    except:
        pass

DEFAULT_TOLERANCIAS_RAYEN = {
    "AFS": {"min": 40.0, "max": 50.0},
    "#20": {"min": 0.0, "max": 0.5},
    "#30": {"min": 0.0, "max": 1.0},
    "#140": {"min": 97.5, "max": 100.0},
    "%Fe2O3": {"min": 0.0, "max": 0.15}
}

DEFAULT_EQUIPAMIENTO_RAYEN = {
    "tamices": "Marca Zonytest, tamiz conforme especificaciones normas ASTME - 11/01 IRAM 1501. Mallas S/ ISO 9044",
    "balanza": "BOECO BSP 40",
    "espectrofotometro": "UV HACH - 1900",
    "control_ultimo": "31-may-26",
    "control_proximo": "29-ago-26"
}

CORTES_DEFAULT = [
    {"nombre": "#30/70", "mallas": ["#40", "#50", "#60", "#70"], "min_verde": 90.0, "min_amarillo": 80.0},
    {"nombre": "#40/70", "mallas": ["#50", "#60", "#70"], "min_verde": 90.0, "min_amarillo": 80.0},
    {"nombre": "#50/140", "mallas": ["#70", "#100", "#140"], "min_verde": 90.0, "min_amarillo": 80.0},
    {"nombre": "#30/140", "mallas": ["#40", "#50", "#60", "#70", "#100", "#140"], "min_verde": 90.0, "min_amarillo": 80.0}
]

def cargar_cortes_config():
    if os.path.exists(CORTES_FILE):
        try:
            with open(CORTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return [dict(c) for c in CORTES_DEFAULT]

def guardar_cortes_config(cortes_list):
    with open(CORTES_FILE, "w", encoding="utf-8") as f:
        json.dump(cortes_list, f, ensure_ascii=False, indent=2)

def cargar_tolerancias_rayen():
    if os.path.exists(RAYEN_TOLERANCIAS_FILE):
        try:
            with open(RAYEN_TOLERANCIAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_TOLERANCIAS_RAYEN.items():
                    if k not in data:
                        data[k] = dict(v)
                return data
        except:
            pass
    return {k: dict(v) for k, v in DEFAULT_TOLERANCIAS_RAYEN.items()}

def cargar_equipamiento_rayen():
    if os.path.exists(RAYEN_EQUIPAMIENTO_FILE):
        try:
            with open(RAYEN_EQUIPAMIENTO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_EQUIPAMIENTO_RAYEN.items():
                    if k not in data:
                        data[k] = v
                return data
        except:
            pass
    return dict(DEFAULT_EQUIPAMIENTO_RAYEN)

def guardar_equipamiento_rayen(equip_dict):
    with open(RAYEN_EQUIPAMIENTO_FILE, "w", encoding="utf-8") as f:
        json.dump(equip_dict, f, ensure_ascii=False, indent=2)

def evaluar_apto_rayen(df_r, val_afs, rayen_config):
    if df_r is None or df_r.empty:
        return False, {}
    
    col_acum = "Acumulado % Retenido" if "Acumulado % Retenido" in df_r.columns else "Retenido %"
    
    ret_20 = float(df_r[df_r["Tamiz N°"] == "#20"][col_acum].values[0]) if "#20" in df_r["Tamiz N°"].values else 0.0
    ret_30 = float(df_r[df_r["Tamiz N°"] == "#30"][col_acum].values[0]) if "#30" in df_r["Tamiz N°"].values else 0.0
    ret_140 = float(df_r[df_r["Tamiz N°"] == "#140"][col_acum].values[0]) if "#140" in df_r["Tamiz N°"].values else 0.0
    
    afs_min = float(rayen_config.get("AFS", {}).get("min", 40.0))
    afs_max = float(rayen_config.get("AFS", {}).get("max", 50.0))
    t20_min = float(rayen_config.get("#20", {}).get("min", 0.0))
    t20_max = float(rayen_config.get("#20", {}).get("max", 0.5))
    t30_min = float(rayen_config.get("#30", {}).get("min", 0.0))
    t30_max = float(rayen_config.get("#30", {}).get("max", 1.0))
    t140_min = float(rayen_config.get("#140", {}).get("min", 97.5))
    t140_max = float(rayen_config.get("#140", {}).get("max", 100.0))
    
    ok_afs = (afs_min <= val_afs <= afs_max)
    ok_20 = (t20_min <= ret_20 <= t20_max)
    ok_30 = (t30_min <= ret_30 <= t30_max)
    ok_140 = (t140_min <= ret_140 <= t140_max)
    
    is_apto = (ok_afs and ok_20 and ok_30 and ok_140)
    detalles = {
        "val_afs": val_afs, "ok_afs": ok_afs, "afs_rango": f"{afs_min} - {afs_max}",
        "ret_20": ret_20, "ok_20": ok_20, "t20_rango": f"{t20_min}% - {t20_max}%",
        "ret_30": ret_30, "ok_30": ok_30, "t30_rango": f"{t30_min}% - {t30_max}%",
        "ret_140": ret_140, "ok_140": ok_140, "t140_rango": f"{t140_min}% - {t140_max}%"
    }
    return is_apto, detalles

def formatear_fecha(val):
    if not val or pd.isna(val) or str(val).strip() in ["", "-", "None"]:
        return "-"
    val_str = str(val).strip()
    parts = val_str.split(" ")
    date_part = parts[0]
    time_part = f" {parts[1]}" if len(parts) > 1 else ""
    
    if "-" in date_part:
        sub = date_part.split("-")
        if len(sub) == 3 and len(sub[0]) == 4: # YYYY-MM-DD
            return f"{sub[2]}/{sub[1]}/{sub[0]}" + time_part
    return val_str

def parsear_fecha_obj(val):
    if not val or pd.isna(val) or str(val).strip() in ["", "-", "None"]:
        return datetime.now().date()
    val_str = str(val).strip().split(" ")[0]
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(val_str, fmt).date()
        except:
            pass
    return datetime.now().date()

def add_logo_ui():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{encoded}");
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-size: 160px;
                background-position: top 10px right 80px;
            }}
            @media (max-width: 600px) {{ .stApp {{ background-image: none; }} }}
            </style>
            """,
            unsafe_allow_html=True
        )

# --- CONSTANTES ---
TAMICES_AFS = ["#8", "#12", "#20", "#30", "#40", "#50", "#70", "#100", "#140", "#200", "#270", "Fdo."]
FACTORES_AFS = [5, 5, 10, 20, 30, 40, 50, 70, 100, 140, 200, 300]
TAMICES_FRACKING = ["#20", "#30", "#40", "#50", "#60", "#70", "#100", "#140", "Fdo."]
FACTORES_FRACKING = [10, 20, 30, 40, 50, 70, 100, 140, 300]
TAMICES_MF = ["#4", "#8", "#18", "#30", "#50", "#100", "Fdo."]
ABERTURAS_MF = ["4.75", "2.36", "1", "0.6", "0.3", "0.15", "-"]

MICRONES = {
    "#4": "4750", "#8": "2360", "#10": "2000", "#16": "1180", "#18": "1000", "#20": "850", 
    "#30": "600", "#40": "425", "#50": "300", "#60": "250", "#70": "212", 
    "#100": "150", "#140": "106", "#200": "75", "#270": "53", "Fdo.": "-"
}

# --- CLASE PARA CÁLCULO DE d10/d60/CU (Tamaño Efectivo) ---
class AnalizadorD10:
    def __init__(self, tamices: list, pesos: list, tamices_nos: list = None):
        if tamices_nos is not None:
            datos_completos = sorted(zip(tamices, pesos, tamices_nos), key=lambda x: x[0], reverse=True)
            self.tamices = [x[0] for x in datos_completos]
            self.pesos = [x[1] for x in datos_completos]
            self.tamices_nos = [x[2] for x in datos_completos]
        else:
            datos_completos = sorted(zip(tamices, pesos), key=lambda x: x[0], reverse=True)
            self.tamices = [x[0] for x in datos_completos]
            self.pesos = [x[1] for x in datos_completos]
            self.tamices_nos = [f"{x:.2f}" if x > 0 else "Fdo." for x in self.tamices]
            
        self.peso_total = sum(self.pesos)
        
        self.pct_retenido = []
        self.pct_acumulado = []  
        self.pct_pasa = []       
        
        if self.peso_total > 0:
            acumulado = 0.0
            for p in self.pesos:
                pct_r = (p / self.peso_total) * 100.0
                self.pct_retenido.append(pct_r)
                acumulado += pct_r
                self.pct_acumulado.append(acumulado)
                self.pct_pasa.append(max(0.0, 100.0 - acumulado))
        else:
            self.pct_retenido = [0.0] * len(self.pesos)
            self.pct_acumulado = [0.0] * len(self.pesos)
            self.pct_pasa = [0.0] * len(self.pesos)

    def interpolar_diametro(self, target_pct: float) -> float:
        if self.peso_total <= 0:
            return 0.0
            
        for i in range(len(self.tamices) - 1):
            p1 = self.pct_pasa[i]      
            p2 = self.pct_pasa[i+1]    
            
            if p1 >= target_pct >= p2:
                d1 = self.tamices[i]     
                d2 = self.tamices[i+1]   
                
                if p1 == p2:
                    return d1
                    
                if p1 <= 0 or p2 <= 0 or target_pct <= 0:
                    return d2 + ((target_pct - p2) / (p1 - p2)) * (d1 - d2)
                
                log_x = math.log10(target_pct)
                log_p1 = math.log10(p1)
                log_p2 = math.log10(p2)
                
                dx = d2 + ((log_x - log_p2) / (log_p1 - log_p2)) * (d1 - d2)
                return dx
                
        return 0.0

    def interpolar_porcentaje(self, target_diame: float) -> float:
        if self.peso_total <= 0:
            return 0.0
        for i in range(len(self.tamices) - 1):
            d1 = self.tamices[i]
            d2 = self.tamices[i+1]
            
            if d1 >= target_diame >= d2:
                p1 = self.pct_pasa[i]
                p2 = self.pct_pasa[i+1]
                
                if d1 == d2:
                    return p1
                    
                d1_val = d1 if d1 > 0 else 0.001
                d2_val = d2 if d2 > 0 else 0.001
                
                log_d1 = math.log10(d1_val)
                log_d2 = math.log10(d2_val)
                log_target = math.log10(target_diame if target_diame > 0 else 0.001)
                
                pct = p1 + (p2 - p1) * ((log_target - log_d1) / (log_d2 - log_d1))
                return max(0.0, pct)
        return 0.0

    def calcular_modulo_finura_especifico(self) -> float:
        """
        Calcula el MF según la norma ASTM C136 usando estrictamente las mallas indicadas:
        #4, #8, #18, #30, #50, #100, #200.
        """
        if self.peso_total <= 0:
            return 0.0
            
        tamices_norma = ["#4", "#8", "#18", "#30", "#50", "#100", "#200"]
        suma_acumulados = 0.0
        
        for t_std in tamices_norma:
            if t_std in self.tamices_nos:
                idx = self.tamices_nos.index(t_std)
                suma_acumulados += self.pct_acumulado[idx]
            else:
                abertura_std = 0.0
                if t_std == "#4": abertura_std = 4.75
                elif t_std == "#8": abertura_std = 2.36
                elif t_std == "#18": abertura_std = 1.00
                elif t_std == "#30": abertura_std = 0.60
                elif t_std == "#50": abertura_std = 0.30
                elif t_std == "#100": abertura_std = 0.15
                elif t_std == "#200": abertura_std = 0.075
                
                p_pasa = self.interpolar_porcentaje(abertura_std)
                p_acum_ret = max(0.0, 100.0 - p_pasa)
                suma_acumulados += p_acum_ret
                
        return round(suma_acumulados / 100.0, 2)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('laboratorio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analisis (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT)''')
    columnas = [
        ("num_analisis", "TEXT"), ("fecha_carga", "TEXT"), ("fecha_viaje", "TEXT"), 
        ("cliente", "TEXT"), ("origen", "TEXT"), ("clasificacion", "TEXT"), 
        ("producto", "TEXT"), ("silo", "TEXT"), ("dominio", "TEXT"), ("observaciones", "TEXT"),
        ("t8", "REAL"), ("t12", "REAL"), ("t20", "REAL"), ("t30", "REAL"), ("t40", "REAL"),
        ("t50", "REAL"), ("t60", "REAL"), ("t70", "REAL"), ("t100", "REAL"), 
        ("t140", "REAL"), ("t200", "REAL"), ("t270", "REAL"), ("tfdo", "REAL"),
        ("mf4", "REAL"), ("mf8", "REAL"), ("mf18", "REAL"), ("mf30", "REAL"),
        ("mf50", "REAL"), ("mf100", "REAL"),
        ("d10_json_datos", "TEXT"), ("d10_limites_json", "TEXT"),
        ("rayen_json", "TEXT"), ("rayen_lote_tipo", "TEXT"), ("rayen_fecha_elaboracion", "TEXT"),
        ("creado_por", "TEXT"), ("modificado_por", "TEXT"), ("fecha_modificacion", "TEXT")
    ]
    c.execute("PRAGMA table_info(analisis)")
    existentes = [info[1] for info in c.fetchall()]
    for col, tipo in columnas:
        if col not in existentes:
            c.execute(f"ALTER TABLE analisis ADD COLUMN {col} {tipo}")
    conn.commit(); conn.close()

def eliminar_reporte(id_r):
    conn = sqlite3.connect('laboratorio.db'); c = conn.cursor()
    c.execute("DELETE FROM analisis WHERE id = ?", (id_r,))
    conn.commit(); conn.close()
    st.cache_data.clear()
    try:
        import gdrive_sync
        gdrive_sync.subir_db_a_gdrive()
    except:
        pass

# --- CÁLCULOS TÉCNICOS ---
def calcular_granulometria(pesos, tamices, factores):
    df = pd.DataFrame({"Tamiz N°": tamices, "Factor": factores, "Neto Grs": pesos})
    total = df["Neto Grs"].sum()
    if total > 0:
        df["Retenido %"] = (df["Neto Grs"] * 100) / total
        df["Productos"] = df["Retenido %"] * df["Factor"]
        df["Acumulado % Retenido"] = df["Retenido %"].cumsum()
        return df, total, df["Productos"].sum() / 100
    return None, 0, 0

def calcular_mf(pesos):
    df = pd.DataFrame({"Tamiz N°": TAMICES_MF, "Abertura (mm)": ABERTURAS_MF, "Neto Grs": pesos})
    total = df["Neto Grs"].sum()
    if total > 0:
        df["Retenido %"] = ((df["Neto Grs"] * 100) / total).round(2)
        df["Acumulado % Retenido"] = df["Retenido %"].cumsum().round(2)
        suma_a = df[df["Tamiz N°"] != "Fdo."]["Acumulado % Retenido"].sum()
        return df, total, suma_a / 100, suma_a
    return None, 0, 0, 0

def agregar_fila_total(df):
    df_sum = df.copy()
    totales = {df_sum.columns[0]: "TOTAL"}
    for col in df_sum.columns:
        if col in ["Neto Grs", "Retenido %", "Acumulado % Retenido", "Productos", "E (%) Pasa", "Porcentaje Que Pasa %"]:
            if col in ["Acumulado % Retenido", "E (%) Pasa", "Porcentaje Que Pasa %"]:
                totales[col] = "-"
            else:
                totales[col] = df_sum[col].sum()
    return pd.concat([df_sum, pd.DataFrame([totales])], ignore_index=True).fillna("")

@st.cache_data
def obtener_historial_calculado():
    conn = sqlite3.connect('laboratorio.db')
    df = pd.read_sql_query("SELECT * FROM analisis ORDER BY id DESC", conn)
    conn.close()
    resultados = []
    
    # Pre-calcular factores AFS y Fracking para evitar llamadas repetidas
    factores_afs = [5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 70.0, 100.0, 140.0, 200.0, 300.0, 0.0]
    factores_frack = [10.0, 20.0, 30.0, 40.0, 50.0, 70.0, 100.0, 140.0, 0.0]
    
    for _, f in df.iterrows():
        tipo = f['tipo']
        res = {
            "ID": f['id'],
            "Tipo": tipo,
            "tipo": tipo,
            "Análisis": f['num_analisis'],
            "Fecha": formatear_fecha(f['fecha_viaje']), 
            "Cliente": f['cliente'],
            "Producto": f['producto'],
            "Origen": f.get('origen', ''),
            "Silo": f.get('silo', ''),
            "AFS": 0.0,
            "MF": 0.0, 
            "R_30/70": 0.0,
            "R_40/70": 0.0,
            "R_50/140": 0.0,
            "R_30/140": 0.0,
            "R_50": 0.0,
            "R_100": 0.0,
            "Cumple_Req": 0,
            "t8": 0.0,
            "R_8": 0.0,
            "d10": 0.0,
            "d60": 0.0,
            "CU": 0.0
        }
        try:
            if tipo == "AFS":
                t8_val = float(f['t8']) if ('t8' in f and pd.notnull(f['t8'])) else 0.0
                res["t8"] = round(t8_val, 2)
                
                # Cargar pesos del tamiz
                pesos = [t8_val]
                for t in ['t12', 't20', 't30', 't40', 't50', 't70', 't100', 't140', 't200', 't270', 'tfdo']:
                    val_cell = f.get(t)
                    pesos.append(float(val_cell) if val_cell is not None and val_cell != "" else 0.0)
                
                total = sum(pesos)
                if total > 0:
                    res["R_8"] = round((t8_val * 100) / total, 2)
                    weighted_sum = sum(p_val * f_val for p_val, f_val in zip(pesos, factores_afs))
                    res["AFS"] = round(weighted_sum / total, 2)
                    
                    retenido_pct = [(p_val * 100) / total for p_val in pesos]
                    res["R_30/70"] = round(sum(retenido_pct[4:7]), 2)
                    res["R_40/70"] = round(sum(retenido_pct[5:7]), 2)
                    res["R_50/140"] = round(sum(retenido_pct[6:9]), 2)
                    res["R_30/140"] = round(sum(retenido_pct[4:9]), 2)
                    
                    # Cómputo del requisito de calidad #50 (entre 10% y 40%) y #100 (mínimo 15%)
                    r50_val = round(retenido_pct[5], 2)
                    r100_val = round(retenido_pct[7], 2)
                    res["R_50"] = r50_val
                    res["R_100"] = r100_val
                    res["Cumple_Req"] = 1 if (10.0 <= r50_val <= 40.0 and r100_val >= 15.0) else 0
                    
            elif tipo == "Fracking":
                pesos = []
                for t in ['t20', 't30', 't40', 't50', 't60', 't70', 't100', 't140', 'tfdo']:
                    val_cell = f.get(t)
                    pesos.append(float(val_cell) if val_cell is not None and val_cell != "" else 0.0)
                
                total = sum(pesos)
                if total > 0:
                    weighted_sum = sum(p_val * f_val for p_val, f_val in zip(pesos, factores_frack))
                    res["AFS"] = round(weighted_sum / total, 2)
                    
                    retenido_pct = [(p_val * 100) / total for p_val in pesos]
                    res["R_30/70"] = round(sum(retenido_pct[2:6]), 2)
                    res["R_40/70"] = round(sum(retenido_pct[3:6]), 2)
                    res["R_50/140"] = round(sum(retenido_pct[5:8]), 2)
                    res["R_30/140"] = round(sum(retenido_pct[2:8]), 2)
                    
            elif tipo == "MF":
                pesos = []
                for t in ['mf4', 'mf8', 'mf18', 'mf30', 'mf50', 'mf100', 'tfdo']:
                    val_cell = f.get(t)
                    pesos.append(float(val_cell) if val_cell is not None and val_cell != "" else 0.0)
                
                total = sum(pesos)
                if total > 0:
                    retenido_pct = [(x * 100) / total for x in pesos]
                    acumulado_pct = []
                    curr = 0.0
                    for x in retenido_pct:
                        curr += x
                        acumulado_pct.append(curr)
                    res["MF"] = round(sum(acumulado_pct[0:6]) / 100, 2)
                    
            elif tipo == "Rayen":
                res["AFS"] = 0.0
                res["rayen_json"] = f.get('rayen_json')
                if f.get('rayen_json'):
                    try:
                        p_rayen = json.loads(f['rayen_json'])
                        for m_k in ["m1", "m2", "m3"]:
                            m_data = p_rayen.get(m_k)
                            if m_data and m_data.get("afs_val"):
                                res["AFS"] = round(float(m_data["afs_val"]), 2)
                                break
                    except: pass
        except: pass
        resultados.append(res)
    return pd.DataFrame(resultados)

# --- EXPORTACIÓN PDF ---
def generar_pdf_fast(f, df_r, rendimientos_seleccionados, te_seleccionados=None, mostrar_rechazo_t8=False):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    if f['tipo'] == "Rayen":
        # 1. Logo superior derecho
        if os.path.exists(LOGO_PATH):
            pdf.image(LOGO_PATH, x=155, y=10, w=38)
            
        # 2. Título principal azul marino centrado
        pdf.set_y(22)
        pdf.set_font("Arial", 'B', 14); pdf.set_text_color(31, 78, 120)
        pdf.cell(0, 8, "CERTIFICADO DE ANÁLISIS - RAYEN", ln=True, align='C')
        pdf.ln(3)
        
        # 3. Banner Azul "IDENTIFICACIÓN DE LA MUESTRA"
        pdf.set_fill_color(31, 78, 120); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 9.5); pdf.cell(0, 6.5, " IDENTIFICACIÓN DE LA MUESTRA Y PROTOCOLO", ln=True, fill=True)
        
        # 4. Grilla de metadatos con bordes iguales a los demás reportes
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8.5)
        f_c = f.fillna("-")
        obs_txt = str(f_c.get('observaciones') if ('observaciones' in f_c and str(f_c['observaciones']) != "-") else f_c['dominio'])
        lote_tipo = str(f_c.get('rayen_lote_tipo') or 'LOTE PARCIAL').upper()
        fe_v_str = formatear_fecha(f_c['fecha_viaje'])
        
        meta = [
            ("Fecha:", fe_v_str, "Protocolo Nº:", str(f_c['num_analisis'])),
            ("Origen:", str(f_c['origen']), "Cliente:", str(f_c['cliente'])),
            ("Lote:", f"{obs_txt} ({lote_tipo})", "Total tn lote:", "550 tn")
        ]
        for l1, v1, l2, v2 in meta:
            pdf.set_font("Arial", 'B', 8.5); pdf.cell(32, 5.5, l1, border=1)
            pdf.set_font("Arial", '', 8.5); pdf.cell(63, 5.5, v1, border=1)
            pdf.set_font("Arial", 'B', 8.5); pdf.cell(32, 5.5, l2, border=1)
            pdf.set_font("Arial", '', 8.5); pdf.cell(63, 5.5, v2, border=1, ln=True)
            
        pdf.ln(3)
        
        # 5. Banner Azul "DISTRIBUCIÓN Y RESULTADOS DE MUESTRAS"
        pdf.set_fill_color(31, 78, 120); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 9.5); pdf.cell(0, 6.5, " RESULTADOS DE ENSAYOS DE CALIDAD (M1, M2, M3)", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        
        payload = {}
        if f.get('rayen_json'):
            try: payload = json.loads(f['rayen_json'])
            except: pass
            
        r_cfg = cargar_tolerancias_rayen()
        t20_min = float(r_cfg.get('#20', {}).get('min', 0.0))
        t20_max = float(r_cfg.get('#20', {}).get('max', 0.5))
        t30_min = float(r_cfg.get('#30', {}).get('min', 0.0))
        t30_max = float(r_cfg.get('#30', {}).get('max', 1.0))
        t140_min = float(r_cfg.get('#140', {}).get('min', 97.5))
        
        for m_name in ["M1", "M2", "M3"]:
            pdf.set_font("Arial", 'B', 9); pdf.set_text_color(31, 78, 120)
            pdf.cell(0, 4.5, f"Muestra {m_name}", ln=True)
            pdf.set_text_color(0, 0, 0)
            
            m_data = payload.get(m_name.lower())
            is_proc = (m_data is not None and m_data.get("afs_id") is not None)
            
            # Encabezado azul claro de tabla
            pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(217, 225, 242)
            pdf.cell(28, 4, "Tamiz Nº", border=1, align='C', fill=True)
            pdf.cell(25, 4, "Neto Grs", border=1, align='C', fill=True)
            pdf.cell(25, 4, "Retenido %", border=1, align='C', fill=True)
            pdf.cell(45, 4, "Norma min % / max %", border=1, align='C', fill=True)
            pdf.cell(22, 4, "Resultado", border=1, align='C', fill=True)
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            if is_proc:
                n20 = f"{float(m_data.get('neto_20', 0.0)):.1f}".replace('.', ',')
                r20 = f"{float(m_data.get('ret_20', 0.0)):.2f}".replace('.', ',')
                res20 = "Ok" if (t20_min <= float(m_data.get('ret_20', 0.0)) <= t20_max) else "No Ok"
                
                n30 = f"{float(m_data.get('neto_30', 0.0)):.1f}".replace('.', ',')
                r30 = f"{float(m_data.get('ret_30', 0.0)):.2f}".replace('.', ',')
                res30 = "Ok" if (t30_min <= float(m_data.get('ret_30', 0.0)) <= t30_max) else "No Ok"
                
                n140 = f"{float(m_data.get('neto_140', 0.0)):.1f}".replace('.', ',')
                r140 = f"{float(m_data.get('ret_140', 0.0)):.2f}".replace('.', ',')
                res140 = "Ok" if (float(m_data.get('ret_140', 0.0)) >= t140_min) else "No Ok"
                
                ntot = f"{float(m_data.get('neto_total', 100.0)):.1f}".replace('.', ',')
                fe_str = f"{float(m_data.get('fe2o3', 0.0)):.2f}%".replace('.', ',')
            else:
                n20 = n30 = n140 = ntot = "#¡DIV/0!"
                r20 = r30 = r140 = "#¡DIV/0!"
                res20 = res30 = res140 = "#¡DIV/0!"
                fe_str = ""
                
            # 20
            pdf.cell(28, 4, "20", border=1, align='C')
            pdf.cell(25, 4, n20, border=1, align='C')
            pdf.cell(25, 4, r20, border=1, align='C')
            pdf.cell(22.5, 4, f"{t20_min}".replace('.', ','), border=1, align='C')
            pdf.cell(22.5, 4, f"{t20_max}".replace('.', ','), border=1, align='C')
            pdf.cell(22, 4, res20, border=1, align='C')
            pdf.ln()
            
            # 30
            pdf.cell(28, 4, "30", border=1, align='C')
            pdf.cell(25, 4, n30, border=1, align='C')
            pdf.cell(25, 4, r30, border=1, align='C')
            pdf.cell(22.5, 4, f"{t30_min}".replace('.', ','), border=1, align='C')
            pdf.cell(22.5, 4, f"{t30_max}".replace('.', ','), border=1, align='C')
            pdf.cell(22, 4, res30, border=1, align='C')
            pdf.ln()
            
            # 140
            pdf.cell(28, 4, "140", border=1, align='C')
            pdf.cell(25, 4, n140, border=1, align='C')
            pdf.cell(25, 4, r140, border=1, align='C')
            pdf.cell(22.5, 4, f"{t140_min}".replace('.', ','), border=1, align='C')
            pdf.cell(22.5, 4, "-", border=1, align='C')
            pdf.cell(22, 4, res140, border=1, align='C')
            pdf.ln()
            
            # Total
            pdf.cell(28, 4, "Total", border=1, align='C')
            pdf.cell(25, 4, ntot, border=1, align='C')
            pdf.cell(25, 4, "100,00" if is_proc else "#¡DIV/0!", border=1, align='C')
            pdf.cell(67, 4, "", border=1)
            pdf.ln()
            
            # Fe2O3
            pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(242, 242, 242)
            pdf.cell(28, 4, "% Fe2O3", border=1, align='C', fill=True)
            pdf.set_font("Arial", '', 8)
            pdf.cell(25, 4, fe_str, border=1, align='C')
            pdf.ln(4.5)
            
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 4, f"Observaciones: {obs_txt}", ln=True)
        pdf.ln(1.5)
        
        eq = st.session_state.get('rayen_equip_config', cargar_equipamiento_rayen())
        pdf.set_font("Arial", 'B', 8); pdf.cell(0, 4, "Equipamiento de Medición:", ln=True)
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 3.5, f"Tamices: {eq.get('tamices', '')}", ln=True)
        pdf.cell(0, 3.5, f"Balanza analítica: {eq.get('balanza', '')}", ln=True)
        pdf.cell(0, 3.5, f"Espectrofotómetro: {eq.get('espectrofotometro', '')}", ln=True)
        
        pdf.cell(55, 3.5, "Control elementos de medición y pesaje:", border=0)
        pdf.cell(30, 3.5, eq.get('control_ultimo', ''), border=0, align='C')
        pdf.cell(30, 3.5, "próximo:", border=0, align='C')
        pdf.cell(30, 3.5, eq.get('control_proximo', ''), border=0, align='C', ln=True)
        
        pdf.ln(2)
        pdf.set_y(236)
        pdf.cell(0, 3.5, "...................................................", ln=True, align='C')
        pdf.cell(0, 3.5, "P/ Control de Calidad", ln=True, align='C')
        
        # Nota sobre tamices y controles de calidad SOBRE el pie de página
        pdf.set_y(254)
        pdf.set_font("Arial", '', 7.5)
        pdf.cell(190, 3.5, "Tamices: Marca Zonytest, tamiz conforme especificaciones normas ASTM E11/10 - IRAM 1501. Mallas S/ ISO 9044", ln=True)
        f_p = st.session_state.get('fecha_control_pesaje', datetime.now())
        if not hasattr(f_p, 'strftime'): f_p = datetime.now()
        prox = f_p + timedelta(days=90)
        pdf.cell(190, 3.5, f"Control elementos de medición y pesaje {f_p.strftime('%d/%m/%Y')}. Próximo control {prox.strftime('%d/%m/%Y')}", ln=True)
        
        # Pie de página oficial
        if os.path.exists(PIE_PATH):
            pdf.image(PIE_PATH, x=0, y=268, w=210)
        return bytes(pdf.output())


    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=155, y=10, w=38)
    
    pdf.set_y(25)
    pdf.set_font("Arial", 'B', 14); pdf.set_text_color(31, 78, 120)
    pdf.cell(0, 10, "CERTIFICADO DE ANÁLISIS GRANULOMÉTRICO", ln=True, align='C')
    
    pdf.set_y(38); pdf.set_fill_color(31, 78, 120); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, " IDENTIFICACIÓN DE LA MUESTRA", ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 9)
    f_c = f.fillna("-")
    obs_txt = str(f_c.get('observaciones') if ('observaciones' in f_c and str(f_c['observaciones']) != "-") else f_c['dominio'])
    meta = [("Número Análisis:", str(f_c['num_analisis']), "Fecha Análisis:", formatear_fecha(f_c['fecha_carga'])),
            ("Cliente:", str(f_c['cliente']), "Fecha Viaje:", formatear_fecha(f_c['fecha_viaje'])),
            ("Origen:", str(f_c['origen']), "Clasificación:", str(f_c['clasificacion'])),
            ("Producto:", str(f_c['producto']), "Silo / Obs.:", f"{f_c['silo']} / {obs_txt}")]
    for l1, v1, l2, v2 in meta:
        pdf.set_font("Arial", 'B', 9); pdf.cell(35, 6, l1, border=1)
        pdf.set_font("Arial", '', 9); pdf.cell(60, 6, v1, border=1)
        pdf.set_font("Arial", 'B', 9); pdf.cell(35, 6, l2, border=1)
        pdf.set_font("Arial", '', 9); pdf.cell(60, 6, v2, border=1, ln=True)
    
    pdf.ln(4); pdf.set_fill_color(31, 78, 120); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, " DISTRIBUCIÓN DE TAMAÑO DE PARTÍCULA", ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(217, 225, 242); pdf.set_font("Arial", 'B', 9)
    
    is_d10 = (f['tipo'] in ["Tamaño Efectivo", "Tamaño Efectivo de Part."])
    if is_d10:
        cols = [25, 30, 30, 30, 40, 35]
        h_pdf = ["Tamiz Nº", "Abertura mm", "Neto Grs", "Retenido %", "Acumulado % Retenido", "E (%) Pasa"]
    else:
        cols = [30, 40, 40, 40, 40]
        h_pdf = ["Tamiz N°", "Apertura (um)", "Neto (grs)", "Retenido %", "Acumulado %"]
        
    for i, h in enumerate(h_pdf): pdf.cell(cols[i], 7, h, border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    for _, row in df_r.iterrows():
        pdf.cell(cols[0], 5.2, str(row[df_r.columns[0]]), border=1, align='C')
        pdf.cell(cols[1], 5.2, str(row[df_r.columns[1]]), border=1, align='C')
        pdf.cell(cols[2], 5.2, f"{float(row[df_r.columns[2]]):.2f}" if is_d10 else f"{row['Neto Grs']:.2f}", border=1, align='C')
        pdf.cell(cols[3], 5.2, f"{float(row[df_r.columns[3]]):.2f}" if is_d10 else f"{row['Retenido %']:.2f}", border=1, align='C')
        pdf.cell(cols[4], 5.2, f"{float(row[df_r.columns[4]]):.2f}" if is_d10 else f"{row['Acumulado % Retenido']:.2f}", border=1, align='C')
        if is_d10:
            pdf.cell(cols[5], 5.2, f"{float(row[df_r.columns[5]]):.2f}", border=1, align='C')
        pdf.ln()
    
    pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(242, 242, 242)
    pdf.cell(cols[0], 6, "TOTAL", border=1, align='C', fill=True)
    pdf.cell(cols[1], 6, "", border=1, fill=True)
    if is_d10:
        neto_total = df_r[df_r.columns[2]].astype(float).sum()
        pdf.cell(cols[2], 6, f"{neto_total:.2f}", border=1, align='C', fill=True)
        pdf.cell(cols[3], 6, "100.00", border=1, align='C', fill=True)
        pdf.cell(cols[4], 6, "-", border=1, align='C', fill=True)
        pdf.cell(cols[5], 6, "-", border=1, align='C', fill=True)
    else:
        pdf.cell(cols[2], 6, f"{df_r['Neto Grs'].sum():.2f}", border=1, align='C', fill=True)
        pdf.cell(cols[3], 6, "100.00", border=1, align='C', fill=True)
        pdf.cell(cols[4], 6, "-", border=1, align='C', fill=True)
    
    pdf.ln(8); pdf.set_font("Arial", 'B', 10)
    if f['tipo'] in ["AFS", "Fracking"]:
        factors = FACTORES_AFS if f['tipo'] == "AFS" else FACTORES_FRACKING
        v_afs = (df_r["Retenido %"][:len(factors)] * factors).sum() / 100
        pdf.cell(0, 5, f"Número AFS: {v_afs:.2f}", ln=True)
        if f['tipo'] == "AFS" and mostrar_rechazo_t8:
            t8_val = float(f['t8']) if ('t8' in f and pd.notnull(f['t8'])) else 0.0
            if t8_val > 0:
                pdf.set_text_color(200, 0, 0)
                pdf.cell(0, 5, f"(*) ALERTA RECHAZO: Retenido en Tamiz #8: {t8_val:.2f} g", ln=True)
                pdf.set_text_color(0, 0, 0)
        for rend in rendimientos_seleccionados:
            c_info = next((c for c in st.session_state.cortes_config if c["nombre"] == rend), None)
            v = df_r[df_r["Tamiz N°"].isin(c_info["mallas"])]["Retenido %"].sum() if c_info else 0.0
            pdf.cell(0, 5, f"Rendimiento {rend}: {v:.2f}%", ln=True)
    elif f['tipo'] == "MF":
        p_mf = [f[f'mf{str(t).replace("#","").lower()}'] for t in [4, 8, 18, 30, 50, 100]] + [f['tfdo']]
        _, _, mf_val, _ = calcular_mf(p_mf)
        pdf.cell(0, 5, f"Módulo de Finura: {mf_val:.2f}", ln=True)
    elif is_d10:
        datos_list = json.loads(f['d10_json_datos'])
        limites = json.loads(f['d10_limites_json']) if f['d10_limites_json'] else {"val_x": 1.40, "val_y": 0.70}
        val_x = limites.get("val_x", 1.40)
        val_y = limites.get("val_y", 0.70)
        
        tams = []
        pesos = []
        tamices_nos = []
        for x in datos_list:
            tams.append(float(x.get('Abertura (mm)', x.get('Tamiz (mm)', 0.0))))
            pesos.append(float(x.get('Neto Grs', 0.0)))
            tamices_nos.append(str(x.get('Tamiz N°', "")))
            
        analizador = AnalizadorD10(tams, pesos, tamices_nos)
        
        d10 = analizador.interpolar_diametro(10.0)
        d60 = analizador.interpolar_diametro(60.0)
        cu = d60 / d10 if d10 > 0 else 0.0
        mf_val = analizador.calcular_modulo_finura_especifico()
        
        pct_pasa_val_x = analizador.interpolar_porcentaje(val_x)
        pct_acum_val_x = 100.0 - pct_pasa_val_x
        pct_pasa_val_y = analizador.interpolar_porcentaje(val_y)
        
        if te_seleccionados is None:
            te_seleccionados = ["d10 (Efectivo)", "d60", "CU (d60/d10)", f"Granos > {val_x} mm", f"Granos < {val_y} mm", "Módulo de Finura (MF)"]
            
        if any("d10" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"Tamaño Efectivo (d10): {d10:.2f} mm", ln=True)
        if any("d60" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"d60 calculado: {d60:.2f} mm", ln=True)
        if any("CU" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"Coeficiente de Uniformidad (CU): {cu:.2f}", ln=True)
        if any("Módulo" in opt or "MF" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"Módulo de Finura (MF): {mf_val:.2f}", ln=True)
        if any("Granos >" in opt or f"> {val_x}" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"Granos > {val_x} mm: {pct_acum_val_x:.2f}% (Máx 1%)", ln=True)
        if any("Granos <" in opt or f"< {val_y}" in opt for opt in te_seleccionados):
            pdf.cell(0, 5, f"Granos < {val_y} mm: {pct_pasa_val_y:.2f}% (Máx 1%)", ln=True)

    # Bloque de gráfica protegido con try/except
    try:
        plt.figure(figsize=(6.5, 2.0))
        if is_d10:
            datos_list = json.loads(f['d10_json_datos'])
            tams = [float(x.get('Abertura (mm)', x.get('Tamiz (mm)', 0.0))) for x in datos_list]
            pesos = [float(x.get('Neto Grs', 0.0)) for x in datos_list]
            analizador = AnalizadorD10(tams, pesos)
            
            plot_tams = [t for t in tams if t > 0]
            plt.plot(plot_tams, [analizador.interpolar_porcentaje(t) for t in plot_tams], marker='o', color='#0070C0', linewidth=2, label="% Que Pasa")
            
            d10 = analizador.interpolar_diametro(10.0)
            d60 = analizador.interpolar_diametro(60.0)
            if d10 > 0: plt.plot(d10, 10, marker='d', color='red', markersize=8, label=f"d10 ({d10:.2f} mm)")
            if d60 > 0: plt.plot(d60, 60, marker='s', color='purple', markersize=8, label=f"d60 ({d60:.2f} mm)")
            
            plt.xscale('log')
            plt.gca().invert_xaxis()
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.ylim(-5, 105)
            plt.legend(fontsize=8)
            plt.xlabel("Abertura del Tamiz (mm)")
            plt.ylabel("% Que Pasa")
        else:
            plt.plot(df_r["Tamiz N°"], df_r["Acumulado % Retenido"], marker='s', color='#00B050', linewidth=1.5, label="% Acumulado")
            plt.plot(df_r["Tamiz N°"], df_r["Retenido %"], marker='o', color='#0070C0', linewidth=1.2, linestyle='--', label="% Retenido")
            plt.grid(True, linestyle='--', alpha=0.5); plt.ylim(-5, 105); plt.legend(fontsize=8)
            plt.xlabel("Tamiz"); plt.ylabel("% Retenidos")
            
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()

        curr_y = pdf.get_y()
        max_h = 48.0
        if curr_y + max_h > 248:
            max_h = max(25.0, 248.0 - curr_y - 2)
            
        pdf.image(img_buf, x=30, y=curr_y + 2, w=150, h=max_h)
    except:
        plt.close()
        pdf.set_y(pdf.get_y() + 5)
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, "[Gráfica no disponible para esta muestra]", ln=True, align='C')
    
    pdf.set_y(254) 
    pdf.set_font("Arial", '', 7.5)
    pdf.cell(190, 3.5, "Tamices: Marca Zonytest, tamiz conforme especificaciones normas ASTM E11/10 - IRAM 1501. Mallas S/ ISO 9044", ln=True)
    f_p = st.session_state.get('fecha_control_pesaje', datetime.now())
    if not hasattr(f_p, 'strftime'): f_p = datetime.now()
    prox = f_p + timedelta(days=90)
    pdf.cell(190, 3.5, f"Control elementos de medición y pesaje {f_p.strftime('%d/%m/%Y')}. Próximo control {prox.strftime('%d/%m/%Y')}", ln=True)
    
    if os.path.exists(PIE_PATH): 
        pdf.image(PIE_PATH, x=0, y=268, w=210)
    return bytes(pdf.output())

# --- EXPORTACIÓN EXCEL ---
def generar_excel_fast(f, df_r, rendimientos_seleccionados, te_seleccionados=None):
    output = io.BytesIO()
    if f['tipo'] == "Rayen":
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Reporte')
        f_tit = workbook.add_format({'bold':True, 'size':14, 'align':'center', 'font_color':'#1F4E78'})
        f_val = workbook.add_format({'border':1, 'size':9})
        f_lbl = workbook.add_format({'bold':True, 'bg_color':'#F2F2F2', 'border':1, 'size':9})
        f_hdr = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'size':9})
        sheet.write(0, 0, "PROTOCOLO DE CALIDAD RAYEN", f_tit)
        f_c = f.fillna("-")
        lote_tipo = str(f_c.get('rayen_lote_tipo') or 'Lote Parcial')
        meta = [
            ("Número Protocolo:", str(f_c['num_analisis']), "Fecha Elaboración:", formatear_fecha(f_c.get('rayen_fecha_elaboracion') or f_c['fecha_carga'])),
            ("Cliente:", str(f_c['cliente']), "Fecha Viaje:", formatear_fecha(f_c['fecha_viaje'])),
            ("Origen:", str(f_c['origen']), "Clasificación:", str(f_c['clasificacion'])),
            ("Producto:", str(f_c['producto']), "Modalidad Lote:", f"{lote_tipo} (550tn)"),
            ("Silo:", str(f_c['silo']), "Observaciones:", str(f_c.get('observaciones') or f_c['dominio']))
        ]
        r_i = 2
        for l1, v1, l2, v2 in meta:
            sheet.write(r_i, 0, l1, f_lbl); sheet.write(r_i, 1, v1, f_val)
            sheet.write(r_i, 2, l2, f_lbl); sheet.write(r_i, 3, v2, f_val)
            r_i += 1
            
        r_i += 1
        payload = {}
        if f.get('rayen_json'):
            try: payload = json.loads(f['rayen_json'])
            except: pass
        m_activas = payload.get("m_activas", ["M1"])
        
        sheet.write(r_i, 0, "Malla / Parámetro", f_hdr)
        for idx, m_k in enumerate(m_activas):
            sheet.write(r_i, idx+1, f"Muestra {m_k.upper()}", f_hdr)
        r_i += 1
        
        rows_params = [
            ("#20 (% Acum. Retenido)", "ret_20"),
            ("#30 (% Acum. Retenido)", "ret_30"),
            ("#140 (% Acum. Retenido)", "ret_140"),
            ("Total (% Acum. Retenido)", "total"),
            ("% Fe2O3", "fe2o3")
        ]
        for label_p, key_p in rows_params:
            sheet.write(r_i, 0, label_p, f_val)
            for idx, m_k in enumerate(m_activas):
                m_data = payload.get(m_k.lower(), {})
                if key_p == "total": val_str = "100.00%"
                else: val_str = f"{float(m_data.get(key_p, 0.0)):.2f}%"
                sheet.write(r_i, idx+1, val_str, f_val)
            r_i += 1
            
        eq = st.session_state.get('rayen_equip_config', cargar_equipamiento_rayen())
        r_i += 1
        sheet.write(r_i, 0, "Equipamiento:", f_lbl)
        sheet.write(r_i, 1, f"Tamices: {eq.get('tamices', '')}", f_val)
        r_i += 1
        sheet.write(r_i, 1, f"Balanza analítica: {eq.get('balanza', '')}", f_val)
        r_i += 1
        sheet.write(r_i, 1, f"Espectrofotómetro: {eq.get('espectrofotometro', '')}", f_val)
        r_i += 1
        sheet.write(r_i, 1, f"Control elementos de medición y pesaje: {eq.get('control_ultimo', '')}   próximo   {eq.get('control_proximo', '')}", f_val)
            
        workbook.close(); output.seek(0); return output.getvalue()

    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('Reporte')
    sheet.set_paper(9); sheet.set_margins(0.5, 0.5, 0.5, 0.5)
    sheet.set_column('A:A', 15); sheet.set_column('B:G', 14)
    f_tit = workbook.add_format({'bold':True, 'size':14, 'align':'center', 'font_color':'#1F4E78'})
    f_sec = workbook.add_format({'bold':True, 'size':10, 'bg_color':'#1F4E78', 'font_color':'white', 'border':1, 'align':'center'})
    f_lbl = workbook.add_format({'bold':True, 'bg_color':'#F2F2F2', 'border':1, 'size':9})
    f_val = workbook.add_format({'border':1, 'size':9})
    f_th = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'size':9})
    f_num = workbook.add_format({'border':1, 'align':'center', 'num_format':'0.00', 'size':9})
    f_tot = workbook.add_format({'bold':True, 'border':1, 'align':'center', 'bg_color':'#F2F2F2', 'num_format':'0.00'})
    if os.path.exists(LOGO_PATH): sheet.insert_image('F1', LOGO_PATH, {'x_scale':0.28, 'y_scale':0.28, 'x_offset':45, 'y_offset':5})
    sheet.merge_range('A5:G5', "CERTIFICADO DE ANÁLISIS GRANULOMÉTRICO", f_tit)
    f_c = f.fillna("-"); row = 7
    sheet.merge_range(row, 0, row, 6, "IDENTIFICACIÓN DE LA MUESTRA", f_sec); row += 1
    obs_txt = str(f_c.get('observaciones') if ('observaciones' in f_c and str(f_c['observaciones']) != "-") else f_c['dominio'])
    metadata = [("Número Análisis:", f_c['num_analisis'], "Fecha Análisis:", formatear_fecha(f_c['fecha_carga'])), ("Cliente:", f_c['cliente'], "Fecha Viaje:", formatear_fecha(f_c['fecha_viaje'])), ("Origen:", f_c['origen'], "Clasificación:", f_c['clasificacion']), ("Producto:", f_c['producto'], "Silo / Obs.:", f"{f_c['silo']} / {obs_txt}")]
    for l1, v1, l2, v2 in metadata:
        sheet.write(row, 0, l1, f_lbl); sheet.merge_range(row, 1, row, 2, str(v1), f_val); sheet.write(row, 3, l2, f_lbl); sheet.merge_range(row, 4, row, 6, str(v2), f_val); row += 1
    row += 1; sheet.merge_range(row, 0, row, 6, "DISTRIBUCIÓN DE TAMAÑO DE PARTÍCULA", f_sec); row += 1
    
    is_d10 = (f['tipo'] in ["Tamaño Efectivo", "Tamaño Efectivo de Part."])
    if is_d10:
        h_ex = ["Tamiz Nº", "Abertura mm", "Neto Grs", "Retenido %", "Acumulado % Retenido", "E (%) Pasa"]
    else:
        h_ex = ["Tamiz N°", "Apertura (um)", "Neto (grs)", "Retenido %", "Acumulado %"]
        
    for i, h in enumerate(h_ex): sheet.write(row, i, h, f_th)
    row += 1; start_t = row
    for _, r_data in df_r.iterrows():
        sheet.write(row, 0, r_data[df_r.columns[0]], f_num)
        try:
            v1 = float(r_data[df_r.columns[1]])
            sheet.write(row, 1, v1, f_num)
        except:
            sheet.write(row, 1, r_data[df_r.columns[1]], f_num)
            
        sheet.write(row, 2, float(r_data[df_r.columns[2]]), f_num)
        sheet.write(row, 3, float(r_data[df_r.columns[3]]), f_num)
        sheet.write(row, 4, float(r_data[df_r.columns[4]]), f_num)
        if is_d10:
            sheet.write(row, 5, float(r_data[df_r.columns[5]]), f_num)
        row += 1
        
    sheet.write(row, 0, "TOTAL", f_tot); sheet.write(row, 1, "", f_tot)
    neto_total = df_r[df_r.columns[2]].astype(float).sum()
    sheet.write(row, 2, neto_total, f_tot)
    sheet.write(row, 3, 100.00, f_tot); sheet.write(row, 4, "-", f_tot)
    if is_d10:
        sheet.write(row, 5, "-", f_tot)
    
    row_i = start_t
    
    if f['tipo'] in ["AFS", "Fracking"]:
        factors = FACTORES_AFS if f['tipo'] == "AFS" else FACTORES_FRACKING
        v_afs = (df_r["Retenido %"][:len(factors)] * factors).sum() / 100
        sheet.write(row_i, 5, "Número AFS", f_lbl); sheet.write(row_i, 6, round(v_afs, 2), f_val); row_i += 1
        if f['tipo'] == "AFS":
            t8_val = float(f['t8']) if ('t8' in f and pd.notnull(f['t8'])) else 0.0
            if t8_val > 0:
                sheet.write(row_i, 5, "Alerta Tamiz #8", f_lbl); sheet.write(row_i, 6, f"{t8_val:.2f}g (RECHAZO)", f_val); row_i += 1
        for rend in rendimientos_seleccionados:
            c_info = next((c for c in st.session_state.cortes_config if c["nombre"] == rend), None)
            v = df_r[df_r["Tamiz N°"].isin(c_info["mallas"])]["Retenido %"].sum() if c_info else 0.0
            sheet.write(row_i, 5, f"Rend. {rend}", f_lbl); sheet.write(row_i, 6, f"{v:.2f}%", f_val); row_i += 1
    elif f['tipo'] == "MF":
        p_mf = [f[f'mf{str(t).replace("#","").lower()}'] for t in [4, 8, 18, 30, 50, 100]] + [f['tfdo']]
        _, _, mf_val, _ = calcular_mf(p_mf)
        sheet.write(row_i, 5, "Módulo de Finura", f_lbl); sheet.write(row_i, 6, round(mf_val, 2), f_val); row_i += 1
    elif is_d10:
        datos_list = json.loads(f['d10_json_datos'])
        limites = json.loads(f['d10_limites_json']) if f['d10_limites_json'] else {"val_x": 1.40, "val_y": 0.70}
        val_x = limites.get("val_x", 1.40)
        val_y = limites.get("val_y", 0.70)
        
        tams = [float(x.get('Abertura (mm)', x.get('Tamiz (mm)', 0.0))) for x in datos_list]
        pesos = [float(x.get('Neto Grs', 0.0)) for x in datos_list]
        analizador = AnalizadorD10(tams, pesos)
        
        d10 = analizador.interpolar_diametro(10.0)
        d60 = analizador.interpolar_diametro(60.0)
        cu = d60 / d10 if d10 > 0 else 0.0
        mf_val = analizador.calcular_modulo_finura_especifico()
        
        pct_pasa_val_x = analizador.interpolar_porcentaje(val_x)
        pct_acum_val_x = 100.0 - pct_pasa_val_x
        pct_pasa_val_y = analizador.interpolar_porcentaje(val_y)
        
        if te_seleccionados is None:
            te_seleccionados = ["d10 (Efectivo)", "d60", "CU (d60/d10)", "Módulo de Finura (MF)", f"Granos > {val_x} mm", f"Granos < {val_y} mm"]
            
        if any("d10" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, "d10 (Efectivo)", f_lbl); sheet.write(row_i, 6, f"{d10:.2f} mm", f_val); row_i += 1
        if any("d60" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, "d60", f_lbl); sheet.write(row_i, 6, f"{d60:.2f} mm", f_val); row_i += 1
        if any("CU" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, "CU (d60/d10)", f_lbl); sheet.write(row_i, 6, f"{cu:.2f}", f_val); row_i += 1
        if any("Módulo" in opt or "MF" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, "Módulo de Finura", f_lbl); sheet.write(row_i, 6, f"{mf_val:.2f}", f_val); row_i += 1
        if any("Granos >" in opt or f"> {val_x}" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, f"Granos > {val_x}mm", f_lbl); sheet.write(row_i, 6, f"{pct_acum_val_x:.2f}%", f_val); row_i += 1
        if any("Granos <" in opt or f"< {val_y}" in opt for opt in te_seleccionados):
            sheet.write(row_i, 5, f"Granos < {val_y}mm", f_lbl); sheet.write(row_i, 6, f"{pct_pasa_val_y:.2f}%", f_val); row_i += 1

    # Bloque de gráfica protegido en Excel
    try:
        plt.figure(figsize=(9, 4.2))
        if is_d10:
            plot_tams = [t for t in tams if t > 0]
            plt.plot(plot_tams, [analizador.interpolar_porcentaje(t) for t in plot_tams], marker='o', color='#0070C0', linewidth=2, label="% Que Pasa")
            if d10 > 0: plt.plot(d10, 10, marker='d', color='red', markersize=8, label=f"d10 ({d10:.2f} mm)")
            if d60 > 0: plt.plot(d60, 60, marker='s', color='purple', markersize=8, label=f"d60 ({d60:.2f} mm)")
            plt.xscale('log')
            plt.gca().invert_xaxis()
            plt.grid(True, linestyle='--', alpha=0.6); plt.legend(loc='best')
            plt.xlabel("Abertura del Tamiz (mm)"); plt.ylabel("% Que Pasa")
        else:
            plt.plot(df_r["Tamiz N°"], df_r["Acumulado % Retenido"], marker='s', color='#00B050', linewidth=2.5, label="% Acumulado")
            plt.plot(df_r["Tamiz N°"], df_r["Retenido %"], marker='o', color='#0070C0', linewidth=1.5, linestyle='--', label="% Retenido")
            plt.grid(True, linestyle='--', alpha=0.6); plt.ylim(-5, 105); plt.legend(loc='best')
            plt.xlabel("Tamiz"); plt.ylabel("% Retenidos")
            
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=130, bbox_inches='tight')
        plt.close()
        sheet.insert_image(row + 2, 0, 'plot.png', {'image_data': img_buf, 'x_scale': 0.85, 'y_scale': 0.85})
    except:
        plt.close()
        sheet.write(row + 2, 0, "[Gráfica no disponible para esta muestra]")
    
    row_fix = 60
    sheet.merge_range(row_fix, 0, row_fix, 6, "Tamices: Marca Zonytest, tamiz conforme especificaciones normas ASTM E11/10 - IRAM 1501. Mallas S/ ISO 9044", workbook.add_format({'size': 9}))
    f_p = st.session_state.fecha_control_pesaje
    prox = f_p + timedelta(days=90)
    sheet.merge_range(row_fix + 1, 0, row_fix + 1, 6, f"Control elementos de medición y pesaje {f_p.strftime('%d/%m/%Y')}. Próximo control {prox.strftime('%d/%m/%Y')}", workbook.add_format({'size': 9}))
    if os.path.exists(PIE_PATH): sheet.insert_image(62, 0, PIE_PATH, {'x_scale': 0.72, 'y_scale': 0.72})
    workbook.close(); return output.getvalue()

# --- VISTA DE REPORTE INDIVIDUAL EN DETALLE ---
def mostrar_reporte_unico(report_id):
    conn = sqlite3.connect('laboratorio.db')
    f = pd.read_sql_query(f"SELECT * FROM analisis WHERE id={report_id}", conn)
    conn.close()
    if f.empty:
        st.error(f"Reporte con ID {report_id} no encontrado o ha sido eliminado.")
        return
    f = f.iloc[0]
    
    st.markdown(f"## 📋 Certificado de Análisis Granulométrico ({f['tipo']})")
    st.markdown(f"### Análisis N°: `{f['num_analisis']}`")
    
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.markdown(f"👤 **Cliente:** {f['cliente'] or '-'}")
    c_m2.markdown(f"📦 **Producto:** {f['producto'] or '-'}")
    c_m3.markdown(f"📅 **Fecha Análisis:** {formatear_fecha(f['fecha_carga'])}")
    
    c_m4, c_m5, c_m6 = st.columns(3)
    c_m4.markdown(f"📍 **Origen:** {f['origen'] or '-'}")
    c_m5.markdown(f"🏷️ **Clasificación:** {f['clasificacion'] or '-'}")
    c_m6.markdown(f"🚚 **Fecha Viaje:** {formatear_fecha(f['fecha_viaje'])}")
    
    obs_txt = f.get('observaciones') or f.get('dominio') or '-'
    c_m7, c_m8 = st.columns(2)
    c_m7.markdown(f"🪣 **Silo:** {f['silo'] or '-'}")
    c_m8.markdown(f"📝 **Observaciones:** {obs_txt}")
    
    u_crea = f.get('creado_por') or 'Sistema'
    u_mod = f.get('modificado_por') or u_crea
    f_mod = f.get('fecha_modificacion') or f['fecha_carga']
    
    c_m9, c_m10 = st.columns(2)
    c_m9.markdown(f"👤 **Registrado por:** `{u_crea}`")
    c_m10.markdown(f"✏️ **Última modificación:** `{u_mod}` ({formatear_fecha(f_mod)})")
    
    st.divider()
    
    df_r = pd.DataFrame()
    is_d10 = (f['tipo'] in ["Tamaño Efectivo", "Tamaño Efectivo de Part."])
    
    if f['tipo'] == "AFS": 
        t8_val = float(f['t8']) if ('t8' in f and pd.notnull(f['t8'])) else 0.0
        p = [t8_val] + [float(f[f't{str(t).replace("#","").lower()}'] or 0.0) for t in [12, 20, 30, 40, 50, 70, 100, 140, 200, 270, 'fdo']]
        df_r, tot, val_afs = calcular_granulometria(p, TAMICES_AFS, FACTORES_AFS)
        st.metric("Resultado AFS", f"{val_afs:.2f}")
        if t8_val > 0:
            ret_8_pct = df_r[df_r['Tamiz N°']=='#8']['Retenido %'].values[0] if (df_r is not None and '#8' in df_r['Tamiz N°'].values) else 0.0
            st.warning(f"🚨 **CONDICIÓN DE RECHAZO POR GRUESOS:** Esta muestra presenta **{t8_val:.2f} g** ({ret_8_pct:.2f}%) retenidos en **Tamiz N° 8 (#8)**.")
            
        # Evaluación Apto Rayen
        is_apto, detalles_rayen = evaluar_apto_rayen(df_r, val_afs, st.session_state.get('rayen_config', cargar_tolerancias_rayen()))
        col_ray1, col_ray2 = st.columns([3, 1])
        if is_apto:
            col_ray1.markdown("""<div style="background-color:#28a745; padding:12px; border-radius:8px; color:white; font-weight:bold; text-align:center;">🟩 APTO RAYEN (Cumple especificación de finura y retenidos)</div>""", unsafe_allow_html=True)
        else:
            fail_reasons = []
            if not detalles_rayen.get("ok_afs"): fail_reasons.append(f"AFS ({val_afs:.2f} fuera de {detalles_rayen.get('afs_rango')})")
            if not detalles_rayen.get("ok_20"): fail_reasons.append(f"#20 ({detalles_rayen.get('ret_20'):.2f}% fuera de {detalles_rayen.get('t20_rango')})")
            if not detalles_rayen.get("ok_30"): fail_reasons.append(f"#30 ({detalles_rayen.get('ret_30'):.2f}% fuera de {detalles_rayen.get('t30_rango')})")
            if not detalles_rayen.get("ok_140"): fail_reasons.append(f"#140 ({detalles_rayen.get('ret_140'):.2f}% fuera de {detalles_rayen.get('t140_rango')})")
            msg_fail = " | ".join(fail_reasons)
            col_ray1.markdown(f"""<div style="background-color:#dc3545; padding:12px; border-radius:8px; color:white; font-weight:bold; text-align:center;">🟥 NO APTO RAYEN ({msg_fail})</div>""", unsafe_allow_html=True)
            
        with col_ray2:
            if st.button("📜 Protocolo Rayen", use_container_width=True, key="btn_abrir_proto_rayen"):
                st.session_state["edit_rayen_id"] = None
                st.session_state["base_afs_id_rayen"] = f['id']
                st.session_state["modo_armador_rayen"] = True
                if "report_id" in st.query_params:
                    del st.query_params["report_id"]
                st.rerun()

        # Evaluación Requisito de Calidad QC #50 / #100
        ret_50 = df_r[df_r['Tamiz N°']=='#50']['Retenido %'].values[0] if (df_r is not None and '#50' in df_r['Tamiz N°'].values) else 0.0
        ret_100 = df_r[df_r['Tamiz N°']=='#100']['Retenido %'].values[0] if (df_r is not None and '#100' in df_r['Tamiz N°'].values) else 0.0
        ok_50 = (10.0 <= ret_50 <= 40.0)
        ok_100 = (ret_100 >= 15.0)
        cumple_qc = ok_50 and ok_100
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if cumple_qc:
            st.markdown(f"""<div style="background-color:#28a745; padding:12px; border-radius:8px; color:white; font-weight:bold; text-align:center; margin-bottom: 5px;">🟩 CONFORME QC #50/#100 (#50: {ret_50:.2f}% | #100: {ret_100:.2f}%)</div>""", unsafe_allow_html=True)
        else:
            fail_reasons_qc = []
            if not ok_50: fail_reasons_qc.append(f"#50 ({ret_50:.2f}% fuera de 10-40%)")
            if not ok_100: fail_reasons_qc.append(f"#100 ({ret_100:.2f}% fuera de ≥15%)")
            msg_fail_qc = " | ".join(fail_reasons_qc)
            st.markdown(f"""<div style="background-color:#f59e0b; padding:12px; border-radius:8px; color:white; font-weight:bold; text-align:center; margin-bottom: 5px;">🟧 NO CONFORME QC #50/#100 ({msg_fail_qc})</div>""", unsafe_allow_html=True)

    elif f['tipo'] == "Rayen":
        st.markdown(f"## 📜 Certificado de Protocolo Rayen")
        st.markdown(f"### Protocolo N°: `{f['num_analisis']}`")
        
        lote_tipo = f.get('rayen_lote_tipo') or 'Lote Parcial'
        st.info(f"Modalidad de Despacho: **{lote_tipo}** (550 tn)")
        
        payload = {}
        if f.get('rayen_json'):
            try: payload = json.loads(f['rayen_json'])
            except: pass
            
        r_cfg = cargar_tolerancias_rayen()
        t20_min = float(r_cfg.get('#20', {}).get('min', 0.0))
        t20_max = float(r_cfg.get('#20', {}).get('max', 0.5))
        t30_min = float(r_cfg.get('#30', {}).get('min', 0.0))
        t30_max = float(r_cfg.get('#30', {}).get('max', 1.0))
        t140_min = float(r_cfg.get('#140', {}).get('min', 97.5))
        
        cols_m = st.columns(3)
        for idx, m_name in enumerate(["M1", "M2", "M3"]):
            m_data = payload.get(m_name.lower())
            is_proc = (m_data is not None and m_data.get("afs_id") is not None)
            
            with cols_m[idx]:
                st.markdown(f"### Muestra **{m_name}**")
                if is_proc:
                    afs_num = m_data.get('afs_num') or '-'
                    st.write(f"**AFS Asociado:** N° `{afs_num}`")
                    n20 = f"{float(m_data.get('neto_20', 0.0)):.1f}"
                    r20 = f"{float(m_data.get('ret_20', 0.0)):.2f}%"
                    res20 = "Ok" if (t20_min <= float(m_data.get('ret_20', 0.0)) <= t20_max) else "No Ok"
                    
                    n30 = f"{float(m_data.get('neto_30', 0.0)):.1f}"
                    r30 = f"{float(m_data.get('ret_30', 0.0)):.2f}%"
                    res30 = "Ok" if (t30_min <= float(m_data.get('ret_30', 0.0)) <= t30_max) else "No Ok"
                    
                    n140 = f"{float(m_data.get('neto_140', 0.0)):.1f}"
                    r140 = f"{float(m_data.get('ret_140', 0.0)):.2f}%"
                    res140 = "Ok" if (float(m_data.get('ret_140', 0.0)) >= t140_min) else "No Ok"
                    
                    ntot = f"{float(m_data.get('neto_total', 100.0)):.1f}"
                    fe_str = f"{float(m_data.get('fe2o3', 0.0)):.2f}%"
                else:
                    st.caption("*(Sin procesar)*")
                    n20 = n30 = n140 = ntot = "#¡DIV/0!"
                    r20 = r30 = r140 = "#¡DIV/0!"
                    res20 = res30 = res140 = "#¡DIV/0!"
                    fe_str = "-"
                    
                df_disp = pd.DataFrame({
                    "Tamiz N°": ["20", "30", "140", "Total", "% Fe2O3"],
                    "Neto Grs": [n20, n30, n140, ntot, "-"],
                    "Retenido %": [r20, r30, r140, "100.00%" if is_proc else "#¡DIV/0!", fe_str],
                    "Resultado": [res20, res30, res140, "-", "-"]
                })
                st.table(df_disp)
                    
        st.divider()
        eq = st.session_state.get('rayen_equip_config', cargar_equipamiento_rayen())
        st.markdown("**Equipamiento:**")
        st.markdown(f"Tamices: {eq.get('tamices', '')}")
        st.markdown(f"Balanza analítica {eq.get('balanza', '')}")
        st.markdown(f"Espectrofotómetro {eq.get('espectrofotometro', '')}")
        st.markdown(f"Control elementos de medición y pesaje &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; `{eq.get('control_ultimo', '')}` &nbsp;&nbsp;&nbsp;&nbsp; *próximo* &nbsp;&nbsp;&nbsp;&nbsp; `{eq.get('control_proximo', '')}`")
            
        st.divider()
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            rendimientos_sel = st.session_state.get('rendimientos_seleccionados', ["#30/70", "#40/70", "#50/140", "#30/140"])
            pdf_data = generar_pdf_fast(f, df_disp, rendimientos_sel)
            st.download_button(
                label="📄 Exportar a PDF",
                data=pdf_data,
                file_name=f"Protocolo_Rayen_{f['num_analisis']}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_pdf_rayen_direct"
            )
        with c_exp2:
            excel_data = generar_excel_fast(f, df_disp, rendimientos_sel)
            st.download_button(
                label="📊 Exportar a Excel",
                data=excel_data,
                file_name=f"Protocolo_Rayen_{f['num_analisis']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_excel_rayen_direct"
            )
        with c_exp3:
            if st.button("✏️ Editar Protocolo", use_container_width=True, key="btn_editar_proto_rayen"):
                st.session_state["edit_rayen_id"] = f['id']
                st.session_state["base_afs_id_rayen"] = None
                st.session_state["modo_armador_rayen"] = True
                if "report_id" in st.query_params:
                    del st.query_params["report_id"]
                st.rerun()
    elif f['tipo'] == "Fracking": 
        p = [f[f't{str(t).replace("#","").lower()}'] for t in [20, 30, 40, 50, 60, 70, 100, 140, 'fdo']]; df_r, tot, val_afs = calcular_granulometria(p, TAMICES_FRACKING, FACTORES_FRACKING); st.metric("Resultado AFS", f"{val_afs:.2f}")
    elif f['tipo'] == "MF": 
        p = [f[f'mf{str(t).replace("#","").lower()}'] for t in [4, 8, 18, 30, 50, 100]] + [f['tfdo']]; df_r, tot, mf, s_a = calcular_mf(p); st.metric("Módulo Finura", f"{mf:.2f}")
    elif is_d10:
        datos_list = json.loads(f['d10_json_datos'])
        limites = json.loads(f['d10_limites_json']) if f['d10_limites_json'] else {"val_x": 1.40, "val_y": 0.70}
        val_x = limites.get("val_x", 1.40)
        val_y = limites.get("val_y", 0.70)
        
        tams = []
        pesos = []
        tamices_nos = []
        for x in datos_list:
            tams.append(float(x.get('Abertura (mm)', x.get('Tamiz (mm)', 0.0))))
            pesos.append(float(x.get('Neto Grs', 0.0)))
            if 'Tamiz N°' in x: tamices_nos.append(str(x['Tamiz N°']))
            else: tamices_nos.append(f"{x.get('Tamiz (mm)', 0.0):.2f}")
        
        analizador = AnalizadorD10(tams, pesos, tamices_nos)
        d10 = analizador.interpolar_diametro(10.0)
        d60 = analizador.interpolar_diametro(60.0)
        cu = d60 / d10 if d10 > 0 else 0.0
        mf_val = analizador.calcular_modulo_finura_especifico()
        
        pct_pasa_val_x = analizador.interpolar_porcentaje(val_x)
        pct_acum_val_x = 100.0 - pct_pasa_val_x
        pct_pasa_val_y = analizador.interpolar_porcentaje(val_y)
        
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("d10 (Efectivo)", f"{d10:.2f} mm")
        c_m2.metric("d60", f"{d60:.2f} mm")
        c_m3.metric("CU (d60/d10)", f"{cu:.2f}")
        c_m4.metric("Módulo Finura (MF)", f"{mf_val:.2f}")
        
        c_chk1, c_chk2 = st.columns(2)
        col_chk1_color = "#28a745" if pct_acum_val_x <= 1.0 else "#dc3545"
        col_chk2_color = "#28a745" if pct_pasa_val_y <= 1.0 else "#dc3545"
        
        c_chk1.markdown(f"""<div style="background-color:{col_chk1_color}; padding:15px; border-radius:10px; text-align:center; color:white; font-weight:bold;">Granos > {val_x} mm (% Ret. Acum.):<br>{pct_acum_val_x:.2f}% (Máx 1%)</div>""", unsafe_allow_html=True)
        c_chk2.markdown(f"""<div style="background-color:{col_chk2_color}; padding:15px; border-radius:10px; text-align:center; color:white; font-weight:bold;">Granos < {val_y} mm (% Que Pasa):<br>{pct_pasa_val_y:.2f}% (Máx 1%)</div>""", unsafe_allow_html=True)
        
        df_r = pd.DataFrame({
            "Tamiz Nº": tamices_nos, "Abertura mm": [f"{ab:.3f}" if ab > 0 else "0.000" for ab in tams], "Neto Grs": pesos,
            "Retenido %": [round(x, 2) for x in analizador.pct_retenido], "Acumulado % Retenido": [round(x, 2) for x in analizador.pct_acumulado], "E (%) Pasa": [round(x, 2) for x in analizador.pct_pasa]
        })

    # Gráficas en pantalla protegidas
    if f['tipo'] in ["AFS", "Fracking"]:
        cortes_dict = {}
        for c_info in st.session_state.get('cortes_config', CORTES_DEFAULT):
            nombre = c_info["nombre"]
            mallas = c_info["mallas"]
            val_sum = df_r[df_r["Tamiz N°"].isin(mallas)]["Retenido %"].sum()
            lv = float(c_info.get("min_verde", 90.0))
            la = float(c_info.get("min_amarillo", 80.0))
            cortes_dict[nombre] = (val_sum, lv, la)
            
        num_cortes = len(cortes_dict)
        if num_cortes > 0:
            cols = st.columns(min(num_cortes, 6))
            for i, (nombre, (val, lv, la)) in enumerate(cortes_dict.items()):
                col_idx = i % len(cols)
                color = "#28a745" if val >= lv else ("#ffc107" if val >= la else "#dc3545")
                cols[col_idx].markdown(f"""<div style="background-color:{color}; padding:12px; border-radius:10px; text-align:center; color:white; font-weight:bold; margin-bottom:10px;">{nombre}<br>{val:.2f}%</div>""", unsafe_allow_html=True)
        
        fig_web = go.Figure()
        fig_web.add_trace(go.Scatter(x=df_r["Tamiz N°"], y=df_r["Retenido %"], name="% Retenido", line=dict(color='blue')))
        fig_web.add_trace(go.Scatter(x=df_r["Tamiz N°"], y=df_r["Acumulado % Retenido"], name="% Acumulado", line=dict(color='green')))
        
        # Checkbox para alternar la visualización de límites de calidad en la gráfica
        ver_limites_qc = st.checkbox("🔍 Mostrar Límites de Control de Calidad (#50 y #100)", value=True, key=f"chk_qc_{f['id']}")
        if ver_limites_qc:
            fig_web.add_trace(go.Scatter(
                x=["#50", "#50"], y=[10.0, 40.0],
                mode="lines+markers",
                name="Espec. #50 (10-40%)",
                line=dict(color="rgba(40, 167, 69, 0.7)", width=12),
                marker=dict(symbol="line-ew", size=14, color="green")
            ))
            fig_web.add_trace(go.Scatter(
                x=["#100", "#100"], y=[15.0, 100.0],
                mode="lines+markers",
                name="Espec. #100 (≥15%)",
                line=dict(color="rgba(56, 189, 248, 0.7)", width=12),
                marker=dict(symbol="line-ew", size=14, color="blue")
            ))
        st.plotly_chart(fig_web, use_container_width=True)
    elif is_d10:
        try:
            fig_web = go.Figure()
            plot_tams = [t for t in tams if t > 0]
            fig_web.add_trace(go.Scatter(x=plot_tams, y=[analizador.interpolar_porcentaje(t) for t in plot_tams], name="% Que Pasa", line=dict(color='#0070C0', width=2), mode='lines+markers'))
            if d10 > 0: fig_web.add_trace(go.Scatter(x=[d10], y=[10], name="d10", marker=dict(color='red', size=10, symbol='diamond')))
            if d60 > 0: fig_web.add_trace(go.Scatter(x=[d60], y=[60], name="d60", marker=dict(color='purple', size=10, symbol='square')))
            fig_web.update_layout(xaxis=dict(type="log", title="Abertura (mm)", autorange="reversed"), yaxis=dict(title="% Que Pasa"))
            st.plotly_chart(fig_web, use_container_width=True)
        except:
            st.caption("No se pudo renderizar la curva interactiva para esta muestra histórica.")
    elif f['tipo'] == "Rayen":
        pass
    elif not df_r.empty:
        fig_web = go.Figure()
        fig_web.add_trace(go.Scatter(x=df_r["Tamiz N°"], y=df_r["Retenido %"], name="% Retenido", line=dict(color='blue')))
        fig_web.add_trace(go.Scatter(x=df_r["Tamiz N°"], y=df_r["Acumulado % Retenido"], name="% Acumulado", line=dict(color='green')))
        st.plotly_chart(fig_web, use_container_width=True)

    if not df_r.empty:
        st.table(agregar_fila_total(df_r))
        
    st.subheader("📤 Exportar")
    rend_opciones = [c["nombre"] for c in st.session_state.get('cortes_config', [])] if f['tipo'] not in ["MF", "Tamaño Efectivo", "Tamaño Efectivo de Part."] else []
    sel_rend = st.multiselect("Rendimientos:", rend_opciones, default=rend_opciones)
    
    sel_te = None
    if is_d10:
        opciones_te = ["d10 (Efectivo)", "d60", "CU (d60/d10)", "Módulo de Finura (MF)", f"Granos > {val_x} mm", f"Granos < {val_y} mm"]
        sel_te = st.multiselect("Parámetros:", opciones_te, default=opciones_te)
    
    inc_t8 = False
    if f['tipo'] == "AFS":
        t8_val = float(f['t8']) if ('t8' in f and pd.notnull(f['t8'])) else 0.0
        if t8_val > 0:
            inc_t8 = st.checkbox(f"⚠️ Incluir en PDF la alerta de rechazo por Tamiz #8 ({t8_val:.2f}g)", value=False)
            
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        d_ex = generar_excel_fast(f, df_r, sel_rend, te_seleccionados=sel_te)
        st.download_button("Excel", d_ex, f"Reporte_{f['num_analisis']}.xlsx", use_container_width=True)
    with c2:
        d_pdf = generar_pdf_fast(f, df_r, sel_rend, te_seleccionados=sel_te, mostrar_rechazo_t8=inc_t8)
        st.download_button("PDF", d_pdf, f"Reporte_{f['num_analisis']}.pdf", "application/pdf", use_container_width=True)
    with c3:
        if st.button("Eliminar", use_container_width=True):
            eliminar_reporte(f['id'])
            st.success("Reporte enviado a la papelera")
            st.rerun()

# --- APP STREAMLIT ---
init_db(); add_logo_ui()
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cortes_config' not in st.session_state: st.session_state.cortes_config = cargar_cortes_config()
if 'fecha_control_pesaje' not in st.session_state: st.session_state.fecha_control_pesaje = datetime.now().date()

def crear_grafico_velocimetro(titulo, valor, min_val=0, max_val=100, sufijo="%"):
    if valor >= 90.0:
        bar_color = "#10b981"
    elif valor >= 75.0:
        bar_color = "#f59e0b"
    else:
        bar_color = "#ef4444"
        
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = round(valor, 1),
        number = {'suffix': sufijo, 'font': {'size': 38, 'color': "#ffffff", 'family': "Arial, sans-serif"}},
        title = {'text': f"<b>{titulo}</b>", 'font': {'size': 15, 'color': "#cbd5e1", 'family': "Arial, sans-serif"}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#475569", 'tickfont': {'color': '#94a3b8', 'size': 11}},
            'bar': {'color': bar_color, 'thickness': 0.55},
            'bgcolor': "#1e293b",
            'borderwidth': 1.5,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 75], 'color': 'rgba(239, 68, 68, 0.18)'},
                {'range': [75, 90], 'color': 'rgba(245, 158, 11, 0.18)'},
                {'range': [90, 100], 'color': 'rgba(16, 185, 129, 0.18)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 3},
                'thickness': 0.75,
                'value': valor
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=25, r=25, t=40, b=20),
        height=230
    )
    return fig

def render_metricas_tamiz8_ui():
    st.title("📊 Métricas de Control: Tamiz N° 8")
    st.info("Monitoreo histórico de retención y control de calidad sobre Tamiz N° 8 (2.36 mm).")
    st.divider()
    
    df_hist = obtener_historial_calculado()
    if df_hist.empty:
        st.warning("No hay datos cargados en el sistema.")
        return

    df_t8 = df_hist[df_hist["Tipo"].astype(str).str.contains("AFS|Rayen", case=False, na=False)].copy()
    
    df_t8["t8_val"] = pd.to_numeric(df_t8.get("t8", 0.0), errors='coerce').fillna(0.0)
    df_t8["R_8_val"] = pd.to_numeric(df_t8.get("R_8", 0.0), errors='coerce').fillna(0.0)
    
    total_eval = len(df_t8)
    muestras_con_retenido = len(df_t8[df_t8["t8_val"] > 0])
    muestras_sin_retenido = total_eval - muestras_con_retenido
    pct_sin_retenido = (muestras_sin_retenido / total_eval * 100.0) if total_eval > 0 else 100.0
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background:#161b22; border-radius:12px; padding:18px; text-align:center; border:1px solid #30363d;">
            <div style="color:#8b949e; font-size:0.85rem; font-weight:700;">TOTAL EVALUADOS (#8)</div>
            <div style="font-size:2.5rem; font-weight:800; color:#38bdf8; margin:6px 0;">{total_eval}</div>
            <div style="color:#94a3b8; font-size:0.78rem;">Muestras AFS y Rayen</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:#064e3b; border-radius:12px; padding:18px; text-align:center; border:1px solid #10b981;">
            <div style="color:#a7f3d0; font-size:0.85rem; font-weight:700;">CONFORME (0g Retenido)</div>
            <div style="font-size:2.5rem; font-weight:800; color:#6ee7b7; margin:6px 0;">{muestras_sin_retenido}</div>
            <div style="color:#a7f3d0; font-size:0.78rem;">{pct_sin_retenido:.1f}% Cumplimiento Óptimo</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#7f1d1d; border-radius:12px; padding:18px; text-align:center; border:1px solid #ef4444;">
            <div style="color:#fca5a5; font-size:0.85rem; font-weight:700;">ALERTA / RECHAZO (>0g Retenido)</div>
            <div style="font-size:2.5rem; font-weight:800; color:#f87171; margin:6px 0;">{muestras_con_retenido}</div>
            <div style="color:#fca5a5; font-size:0.78rem;">Muestras con material en #8</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if not df_t8.empty:
        st.subheader("📈 Historial de Retenciones en Tamiz #8 (Gramos y % Retenido)")
        fig_t8 = go.Figure()
        fig_t8.add_trace(go.Bar(
            x=df_t8["Análisis"].astype(str),
            y=df_t8["t8_val"],
            name="Peso Retenido en #8 (Grs)",
            marker_color="#ef4444"
        ))
        fig_t8.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#cbd5e1"),
            xaxis=dict(title="N° de Análisis", showgrid=False),
            yaxis=dict(title="Gramos Retenidos", gridcolor="#334155"),
            margin=dict(l=20, r=20, t=30, b=30),
            height=300
        )
        st.plotly_chart(fig_t8, use_container_width=True)

    st.subheader("📋 Registro Detallado Tamiz #8")
    cols_show = [c for c in ["ID", "Análisis", "Fecha", "Cliente", "Producto", "Tipo", "t8", "R_8"] if c in df_t8.columns]
    st.dataframe(df_t8[cols_show], use_container_width=True, hide_index=True)

def render_dashboard_inicio_ui():
    st.title("🧪 Sistema de Gestión de Laboratorio")
    st.info("Bienvenido, **Areneras de la Cruz y Rozas S.A.**")
    st.divider()
    
    # 1. Filtro de Período (Estilo referencia)
    c_fil1, c_fil2 = st.columns([1.2, 1.8])
    with c_fil1:
        filtro_periodo = st.radio("🗓️ **Período de Análisis**", ["Histórico Completo", "Filtrar por Mes/Año"], horizontal=True, key="radio_periodo_dash")
    
    df_hist = obtener_historial_calculado()
    
    if filtro_periodo == "Filtrar por Mes/Año" and not df_hist.empty:
        with c_fil2:
            col_m, col_a = st.columns(2)
            mes_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = col_m.selectbox("Mes:", mes_nombres, index=datetime.now().month-1, key="sb_mes_dash")
            mes_num = mes_nombres.index(mes_sel) + 1
            anio_sel = col_a.selectbox("Año:", [2024, 2025, 2026], index=2, key="sb_anio_dash")
            
            try:
                df_hist['fecha_dt'] = pd.to_datetime(df_hist['Fecha'], format='%d/%m/%Y', errors='coerce')
                df_hist = df_hist[(df_hist['fecha_dt'].dt.month == mes_num) & (df_hist['fecha_dt'].dt.year == anio_sel)]
            except:
                pass

    # 2. Conteo de Análisis Totales
    total_db_count = len(df_hist) if not df_hist.empty else 0
    count_afs = len(df_hist[df_hist["Tipo"].astype(str).str.contains("AFS", case=False, na=False)]) if not df_hist.empty else 0
    count_te = len(df_hist[df_hist["Tipo"].astype(str).str.contains("Tamaño", case=False, na=False)]) if not df_hist.empty else 0
    count_mf = len(df_hist[df_hist["Tipo"].astype(str).str.contains("MF", case=False, na=False)]) if not df_hist.empty else 0
    count_rayen = len(df_hist[df_hist["Tipo"].astype(str).str.contains("Rayen", case=False, na=False)]) if not df_hist.empty else 0

    # 3. Rendimiento #30/140 (con fallback SQL directo)
    avg_rend_30_140 = 0.0
    count_30_140 = 0
    if not df_hist.empty and "R_30/140" in df_hist.columns:
        r_series = pd.to_numeric(df_hist["R_30/140"], errors='coerce').fillna(0.0)
        valid_30_140 = r_series[r_series > 0]
        if not valid_30_140.empty:
            avg_rend_30_140 = float(valid_30_140.mean())
            count_30_140 = len(valid_30_140)

    # Fallback SQL directo si count_30_140 es 0
    if count_30_140 == 0 and os.path.exists('laboratorio.db'):
        try:
            conn = sqlite3.connect('laboratorio.db')
            df_sql = pd.read_sql_query("SELECT t8, t12, t20, t30, t40, t50, t60, t70, t100, t140, t200, t270, tfdo FROM analisis WHERE tipo IN ('AFS', 'Fracking')", conn)
            conn.close()
            calc_r = []
            for _, r_row in df_sql.iterrows():
                all_weights = [float(r_row[col] or 0.0) for col in r_row.index if pd.notnull(r_row[col])]
                tot_w = sum(all_weights)
                if tot_w > 0:
                    cut_w = sum([float(r_row[col] or 0.0) for col in ['t40', 't50', 't60', 't70', 't100', 't140'] if col in r_row and pd.notnull(r_row[col])])
                    calc_r.append((cut_w / tot_w) * 100.0)
            if calc_r:
                avg_rend_30_140 = float(sum(calc_r) / len(calc_r))
                count_30_140 = len(calc_r)
        except:
            pass

    # 4. Aptos Rayen
    rayen_total = 0
    rayen_aptos = 0
    if not df_hist.empty:
        col_tipo_name = "Tipo" if "Tipo" in df_hist.columns else "tipo"
        df_rayen = df_hist[df_hist[col_tipo_name].astype(str).str.contains("Rayen", case=False, na=False)]
        for idx, row in df_rayen.iterrows():
            r_json_raw = row.get("rayen_json")
            if r_json_raw:
                try:
                    payload = json.loads(r_json_raw) if isinstance(r_json_raw, str) else r_json_raw
                    sub_aptos = []
                    for m_k in ["m1", "m2", "m3"]:
                        m_obj = payload.get(m_k)
                        if m_obj and isinstance(m_obj, dict) and m_obj.get("afs_id"):
                            sub_aptos.append(bool(m_obj.get("is_apto", False)))
                    if sub_aptos:
                        rayen_total += 1
                        if all(sub_aptos):
                            rayen_aptos += 1
                except:
                    pass
                    
    pct_rayen_aptos = (rayen_aptos / rayen_total * 100.0) if rayen_total > 0 else 0.0

    # 5. Cumplimiento Requisito Tamiz #50/#100
    qc_total = 0
    qc_aptos = 0
    if not df_hist.empty:
        col_tipo_name = "Tipo" if "Tipo" in df_hist.columns else "tipo"
        df_afs_qc = df_hist[df_hist[col_tipo_name].astype(str).str.contains("AFS", case=False, na=False)]
        for _, row in df_afs_qc.iterrows():
            qc_total += 1
            if row.get("Cumple_Req") == 1:
                qc_aptos += 1
    pct_qc_aptos = (qc_aptos / qc_total * 100.0) if qc_total > 0 else 0.0

    # Layout Secciones estilo Referencia (se ensancha la columna de velocímetros para alojar los 3)
    col_kpi, col_gauge = st.columns([1.0, 2.3])
    
    with col_kpi:
        st.subheader("📈 Resumen General")
        st.markdown(f"""
        <div style="background: #161b22; border-radius:14px; padding:22px; border:1px solid #30363d; box-shadow: 0 10px 25px rgba(0,0,0,0.4);">
            <div style="margin-bottom: 18px;">
                <span style="color:#8b949e; font-size:0.85rem; text-transform:uppercase; font-weight:700;">Análisis Totales Realizados</span>
                <div style="font-size: 2.8rem; font-weight:800; color:#ffffff;">{total_db_count}</div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:15px; border-top:1px solid #30363d; padding-top:15px;">
                <div>
                    <span style="color:#8b949e; font-size:0.78rem;">Muestras AFS</span>
                    <div style="font-size:1.4rem; font-weight:700; color:#38bdf8;">{count_afs}</div>
                </div>
                <div>
                    <span style="color:#8b949e; font-size:0.78rem;">Tamaño Efectivo</span>
                    <div style="font-size:1.4rem; font-weight:700; color:#a855f7;">{count_te}</div>
                </div>
                <div>
                    <span style="color:#8b949e; font-size:0.78rem;">Módulo de Finura</span>
                    <div style="font-size:1.4rem; font-weight:700; color:#f59e0b;">{count_mf}</div>
                </div>
                <div>
                    <span style="color:#8b949e; font-size:0.78rem;">Protocolos Rayen</span>
                    <div style="font-size:1.4rem; font-weight:700; color:#10b981;">{count_rayen}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_gauge:
        st.subheader("📊 Indicadores de Tipo")
        g1, g2, g3 = st.columns(3)
        with g1:
            fig_g1 = crear_grafico_velocimetro("Rendimiento Corte #30/140", avg_rend_30_140)
            st.plotly_chart(fig_g1, use_container_width=True)
            st.caption(f"🎯 **Meta: Alto (>90%)** | {count_30_140} muestras")
        with g2:
            fig_g2 = crear_grafico_velocimetro("Protocolos Aptos Rayen", pct_rayen_aptos)
            st.plotly_chart(fig_g2, use_container_width=True)
            st.caption(f"🎯 **Meta: Alto (>90%)** | {rayen_aptos} de {rayen_total} Aptos")
        with g3:
            fig_g3 = crear_grafico_velocimetro("Conformidad #50/#100", pct_qc_aptos)
            st.plotly_chart(fig_g3, use_container_width=True)
            st.caption(f"🎯 **Meta: Alto (>95%)** | {qc_aptos} de {qc_total} Aptas")

    st.markdown("<br>", unsafe_allow_html=True)
    if not df_hist.empty:
        st.subheader("📋 Últimos Análisis Registrados")
        cols_ult = [c for c in ["ID", "Análisis", "Fecha", "Cliente", "Producto", "Tipo", "creado_por"] if c in df_hist.columns]
        st.dataframe(df_hist[cols_ult].head(10), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not df_hist.empty:
        st.subheader("📋 Últimos Análisis Registrados")
        cols_ult = [c for c in ["ID", "Análisis", "Fecha", "Cliente", "Producto", "Tipo", "creado_por"] if c in df_hist.columns]
        st.dataframe(df_hist[cols_ult].head(10), use_container_width=True, hide_index=True)

def render_config_rendimientos_ui(key_prefix=""):
    corte_nombres = [c["nombre"] for c in st.session_state.cortes_config]
    if not corte_nombres:
        st.info("No hay cortes configurados.")
    else:
        corte_sel = st.selectbox("Seleccionar Corte:", corte_nombres, key=f"{key_prefix}_sb_corte_sel")
        corte_obj = next((c for c in st.session_state.cortes_config if c["nombre"] == corte_sel), None)
        if corte_obj:
            c1, c2 = st.columns(2)
            v_min = c1.number_input("Min Verde %", 0.0, 100.0, float(corte_obj.get("min_verde", 90.0)), key=f"{key_prefix}_mv_{corte_sel}")
            a_min = c2.number_input("Min Amar. %", 0.0, 100.0, float(corte_obj.get("min_amarillo", 80.0)), key=f"{key_prefix}_ma_{corte_sel}")
            
            if v_min != corte_obj.get("min_verde") or a_min != corte_obj.get("min_amarillo"):
                corte_obj["min_verde"] = v_min
                corte_obj["min_amarillo"] = a_min
                guardar_cortes_config(st.session_state.cortes_config)
                
            mallas_str = ", ".join(corte_obj.get("mallas", []))
            st.caption(f"Mallas compuestas: {mallas_str}")
            
            if st.button("🗑️ Eliminar Corte", key=f"{key_prefix}_del_{corte_sel}", use_container_width=True):
                st.session_state.cortes_config = [c for c in st.session_state.cortes_config if c["nombre"] != corte_sel]
                guardar_cortes_config(st.session_state.cortes_config)
                st.rerun()

    st.markdown("---")
    with st.popover("➕ Agregar Nuevo Corte", use_container_width=True):
        st.subheader("Nuevo Corte de Rendimiento")
        nuevo_nombre = st.text_input("Nombre Corte (ej: #20/40)", key=f"{key_prefix}_pop_nombre")
        mallas_disponibles = ["#12", "#20", "#30", "#40", "#50", "#60", "#70", "#100", "#140", "#200", "#270"]
        nuevas_mallas = st.multiselect("Mallas a sumar:", mallas_disponibles, key=f"{key_prefix}_pop_mallas")
        col_nv1, col_nv2 = st.columns(2)
        n_v = col_nv1.number_input("Min Verde %", 0.0, 100.0, 90.0, key=f"{key_prefix}_pop_v")
        n_a = col_nv2.number_input("Min Amarillo %", 0.0, 100.0, 80.0, key=f"{key_prefix}_pop_a")
        
        if st.button("Guardar Corte", key=f"{key_prefix}_pop_save", use_container_width=True):
            if nuevo_nombre and nuevas_mallas:
                existe = any(c["nombre"] == nuevo_nombre for c in st.session_state.cortes_config)
                if not existe:
                    st.session_state.cortes_config.append({
                        "nombre": nuevo_nombre,
                        "mallas": nuevas_mallas,
                        "min_verde": n_v,
                        "min_amarillo": n_a
                    })
                    guardar_cortes_config(st.session_state.cortes_config)
                    st.success(f"Corte {nuevo_nombre} guardado!")
                    st.rerun()
                else:
                    st.error("Ya existe un corte con ese nombre.")
            else:
                st.warning("Ingrese nombre y al menos una malla.")

def render_config_rayen_ui(key_prefix=""):
    if 'rayen_config' not in st.session_state:
        st.session_state.rayen_config = cargar_tolerancias_rayen()
        
    c_rc = st.session_state.rayen_config
    
    st.markdown("**Rango AFS**")
    col_a1, col_a2 = st.columns(2)
    afs_min = col_a1.number_input("AFS Mín", 0.0, 200.0, float(c_rc.get("AFS", {}).get("min", 40.0)), key=f"{key_prefix}_rc_afs_min")
    afs_max = col_a2.number_input("AFS Máx", 0.0, 200.0, float(c_rc.get("AFS", {}).get("max", 50.0)), key=f"{key_prefix}_rc_afs_max")
    
    st.markdown("**% Acumulado Retenido Mallas**")
    c20_1, c20_2 = st.columns(2)
    t20_min = c20_1.number_input("#20 Acum. Mín %", 0.0, 100.0, float(c_rc.get("#20", {}).get("min", 0.0)), key=f"{key_prefix}_rc_t20_min")
    t20_max = c20_2.number_input("#20 Acum. Máx %", 0.0, 100.0, float(c_rc.get("#20", {}).get("max", 0.5)), key=f"{key_prefix}_rc_t20_max")
    
    c30_1, c30_2 = st.columns(2)
    t30_min = c30_1.number_input("#30 Acum. Mín %", 0.0, 100.0, float(c_rc.get("#30", {}).get("min", 0.0)), key=f"{key_prefix}_rc_t30_min")
    t30_max = c30_2.number_input("#30 Acum. Máx %", 0.0, 100.0, float(c_rc.get("#30", {}).get("max", 1.0)), key=f"{key_prefix}_rc_t30_max")
    
    c140_1, c140_2 = st.columns(2)
    t140_min = c140_1.number_input("#140 Acum. Mín %", 0.0, 100.0, float(c_rc.get("#140", {}).get("min", 97.5)), key=f"{key_prefix}_rc_t140_min")
    t140_max = c140_2.number_input("#140 Acum. Máx %", 0.0, 100.0, float(c_rc.get("#140", {}).get("max", 100.0)), key=f"{key_prefix}_rc_t140_max")
    
    st.markdown("**% Fe2O3**")
    cfe_1, cfe_2 = st.columns(2)
    fe_min = cfe_1.number_input("Fe2O3 Mín %", 0.0, 100.0, float(c_rc.get("%Fe2O3", {}).get("min", 0.0)), key=f"{key_prefix}_rc_fe_min")
    fe_max = cfe_2.number_input("Fe2O3 Máx %", 0.0, 100.0, float(c_rc.get("%Fe2O3", {}).get("max", 0.15)), key=f"{key_prefix}_rc_fe_max")
    
    new_rc = {
        "AFS": {"min": afs_min, "max": afs_max},
        "#20": {"min": t20_min, "max": t20_max},
        "#30": {"min": t30_min, "max": t30_max},
        "#140": {"min": t140_min, "max": t140_max},
        "%Fe2O3": {"min": fe_min, "max": fe_max}
    }
    
def render_config_equipamiento_rayen_ui(key_prefix=""):
    if 'rayen_equip_config' not in st.session_state:
        st.session_state.rayen_equip_config = cargar_equipamiento_rayen()
        
    eq = st.session_state.rayen_equip_config
    
    st.markdown("**Especificación de Equipamiento**")
    t_tam = st.text_input("Tamices:", eq.get("tamices", ""), key=f"{key_prefix}_eq_tam")
    t_bal = st.text_input("Balanza Analítica:", eq.get("balanza", ""), key=f"{key_prefix}_eq_bal")
    t_esp = st.text_input("Espectrofotómetro:", eq.get("espectrofotometro", ""), key=f"{key_prefix}_eq_esp")
    
    st.markdown("**Control Medición y Pesaje**")
    col_e1, col_e2 = st.columns(2)
    f_ult = col_e1.text_input("Último Control:", eq.get("control_ultimo", "31-may-26"), key=f"{key_prefix}_eq_fult")
    f_prox = col_e2.text_input("Próximo Control:", eq.get("control_proximo", "29-ago-26"), key=f"{key_prefix}_eq_fprox")
    
    new_eq = {
        "tamices": t_tam,
        "balanza": t_bal,
        "espectrofotometro": t_esp,
        "control_ultimo": f_ult,
        "control_proximo": f_prox
    }
    
    if new_eq != eq:
        st.session_state.rayen_equip_config = new_eq
        guardar_equipamiento_rayen(new_eq)

def armar_protocolo_rayen_ui():
    st.title("📜 Armador de Protocolo de Calidad Rayen")
    st.info("💡 **Operatoria de Silos:** Seleccione qué muestra/s (M1, M2, M3) habilitar y asocie libremente el análisis AFS correspondiente a cada posición.")
    
    edit_id_raw = st.session_state.get("edit_rayen_id")
    edit_id = int(edit_id_raw) if (edit_id_raw is not None and str(edit_id_raw).isdigit()) else None
    
    base_afs_id_raw = st.session_state.get("base_afs_id_rayen")
    base_afs_id = int(base_afs_id_raw) if (base_afs_id_raw is not None and str(base_afs_id_raw).isdigit()) else None
    
    conn = sqlite3.connect('laboratorio.db')
    
    existing_proto = None
    if edit_id is not None:
        df_p = pd.read_sql_query(f"SELECT * FROM analisis WHERE id={edit_id}", conn)
        if not df_p.empty: existing_proto = df_p.iloc[0]
            
    base_afs_row = None
    if base_afs_id:
        df_base = pd.read_sql_query(f"SELECT * FROM analisis WHERE id={base_afs_id}", conn)
        if not df_base.empty: base_afs_row = df_base.iloc[0]
            
    df_all_afs = pd.read_sql_query("SELECT id, num_analisis, fecha_viaje, cliente, producto, t8, t12, t20, t30, t40, t50, t70, t100, t140, t200, t270, tfdo FROM analisis WHERE tipo='AFS' ORDER BY id DESC", conn)
    conn.close()
    
    dict_afs_by_id = {}
    afs_ids_options = [0]
    labels_map = {0: "-- Seleccionar AFS --"}
    
    for _, r_afs in df_all_afs.iterrows():
        afs_id_int = int(r_afs['id'])
        lbl = f"N° {r_afs['num_analisis']} | {r_afs['producto'] or 'Arena'} | ({formatear_fecha(r_afs['fecha_viaje'])})"
        dict_afs_by_id[afs_id_int] = r_afs.to_dict()
        afs_ids_options.append(afs_id_int)
        labels_map[afs_id_int] = lbl
        
    lote_tipo_def = existing_proto['rayen_lote_tipo'] if (existing_proto is not None and existing_proto.get('rayen_lote_tipo')) else "Lote Parcial"
    ref_row = existing_proto if existing_proto is not None else base_afs_row
    
    st.subheader("1. Identificación del Lote y Despacho")
    c1, c2, c3 = st.columns(3)
    num = c1.text_input("Número Análisis / Protocolo", value=str(ref_row['num_analisis']) if ref_row is not None else "", key="rayen_num_proto")
    
    f_v_val = parsear_fecha_obj(ref_row['fecha_viaje']) if (ref_row is not None and ref_row.get('fecha_viaje')) else datetime.now().date()
    f_v = c2.date_input("Fecha Viaje", value=f_v_val, format="DD/MM/YYYY", key="rayen_fv_proto")
    cli = c3.text_input("Cliente", value=str(ref_row['cliente']) if ref_row is not None else "", key="rayen_cli_proto")
    
    c4, c5, c6 = st.columns(3)
    ori = c4.text_input("Origen", value=str(ref_row['origen']) if ref_row is not None else "", key="rayen_ori_proto")
    cla = c5.text_input("Clasificación", value=str(ref_row['clasificacion']) if ref_row is not None else "", key="rayen_cla_proto")
    pro = c6.text_input("Producto", value=str(ref_row['producto']) if ref_row is not None else "", key="rayen_pro_proto")
    
    c7, c8 = st.columns(2)
    sil = c7.text_input("Silo", value=str(ref_row['silo']) if ref_row is not None else "", key="rayen_sil_proto")
    obs_def = str(ref_row.get('observaciones') or ref_row.get('dominio') or '') if ref_row is not None else ''
    obs = c8.text_input("Observaciones", value=obs_def, key="rayen_obs_proto")
    
    st.divider()
    st.subheader("2. Modalidad de Lote (550 tn)")
    lote_tipo = st.radio("Seleccione la modalidad de despacho:", ["Lote Parcial", "Lote Total"], index=0 if lote_tipo_def == "Lote Parcial" else 1, horizontal=True, key="rayen_lote_tipo_radio")
    
    st.divider()
    st.subheader("3. Asignación Flexible de Muestras (M1, M2, M3)")
    
    existing_payload = {}
    if existing_proto is not None and existing_proto.get('rayen_json'):
        try: existing_payload = json.loads(existing_proto['rayen_json'])
        except: pass
        
    m_activas_def = existing_payload.get("m_activas", ["M1"])
    
    col_chk1, col_chk2, col_chk3 = st.columns(3)
    chk_m1 = col_chk1.checkbox("Habilitar M1", value=("M1" in m_activas_def), key="chk_m1")
    chk_m2 = col_chk2.checkbox("Habilitar M2", value=("M2" in m_activas_def), key="chk_m2")
    chk_m3 = col_chk3.checkbox("Habilitar M3", value=("M3" in m_activas_def), key="chk_m3")
    
    def render_m_section(m_label, m_key, is_enabled):
        if not is_enabled: return None
            
        st.markdown(f"#### 📍 Muestra **{m_label}**")
        m_data_prev = existing_payload.get(m_key) or {}
        
        target_afs_id = m_data_prev.get("afs_id") or (base_afs_row['id'] if (m_key == "m1" and base_afs_row is not None) else 0)
        target_afs_id = int(target_afs_id) if target_afs_id and int(target_afs_id) in dict_afs_by_id else 0
        
        default_idx = 0
        if target_afs_id in afs_ids_options:
            default_idx = afs_ids_options.index(target_afs_id)
            
        sel_afs_id = st.selectbox(
            f"Asociar AFS para {m_label}:",
            options=afs_ids_options,
            format_func=lambda x: labels_map.get(x, "-- Seleccionar AFS --"),
            index=default_idx,
            key=f"sel_afs_id_{m_key}"
        )
        
        afs_selected = dict_afs_by_id.get(sel_afs_id) if (sel_afs_id and sel_afs_id != 0) else None
        
        neto_20 = 0.0; neto_30 = 0.0; neto_140 = 0.0; neto_total = 0.0
        ret_20 = 0.0; ret_30 = 0.0; ret_140 = 0.0; val_afs = 0.0
        is_apto = False
        msg_fail = ""
        
        if afs_selected:
            t8_v = float(afs_selected.get('t8') or 0.0)
            pesos_afs = [t8_v] + [float(afs_selected.get(f't{str(t).replace("#","").lower()}') or 0.0) for t in [12, 20, 30, 40, 50, 70, 100, 140, 200, 270, 'fdo']]
            df_cal, _, val_afs = calcular_granulometria(pesos_afs, TAMICES_AFS, FACTORES_AFS)
            if df_cal is not None and not df_cal.empty:
                col_acum = "Acumulado % Retenido" if "Acumulado % Retenido" in df_cal.columns else "Retenido %"
                neto_20 = round(float(df_cal[df_cal["Tamiz N°"] == "#20"]["Neto Grs"].values[0]), 2) if "#20" in df_cal["Tamiz N°"].values else 0.0
                neto_30 = round(float(df_cal[df_cal["Tamiz N°"] == "#30"]["Neto Grs"].values[0]), 2) if "#30" in df_cal["Tamiz N°"].values else 0.0
                neto_140 = round(float(df_cal[df_cal["Tamiz N°"] == "#140"]["Neto Grs"].values[0]), 2) if "#140" in df_cal["Tamiz N°"].values else 0.0
                neto_total = round(float(df_cal["Neto Grs"].sum()), 2)
                
                ret_20 = round(float(df_cal[df_cal["Tamiz N°"] == "#20"][col_acum].values[0]), 2) if "#20" in df_cal["Tamiz N°"].values else 0.0
                ret_30 = round(float(df_cal[df_cal["Tamiz N°"] == "#30"][col_acum].values[0]), 2) if "#30" in df_cal["Tamiz N°"].values else 0.0
                ret_140 = round(float(df_cal[df_cal["Tamiz N°"] == "#140"][col_acum].values[0]), 2) if "#140" in df_cal["Tamiz N°"].values else 0.0
                
            is_apto, detalles_rayen = evaluar_apto_rayen(df_cal, val_afs, st.session_state.get('rayen_config', cargar_tolerancias_rayen()))
            
            if is_apto:
                st.success(f"🟩 **AFS N° {afs_selected['num_analisis']} APTO RAYEN** (AFS: {val_afs:.2f} | #20: {ret_20:.2f}% | #30: {ret_30:.2f}% | #140: {ret_140:.2f}%)")
            else:
                fail_reasons = []
                if not detalles_rayen.get("ok_afs"): fail_reasons.append(f"AFS ({val_afs:.2f} fuera de {detalles_rayen.get('afs_rango')})")
                if not detalles_rayen.get("ok_20"): fail_reasons.append(f"#20 ({detalles_rayen.get('ret_20'):.2f}% fuera de {detalles_rayen.get('t20_rango')})")
                if not detalles_rayen.get("ok_30"): fail_reasons.append(f"#30 ({detalles_rayen.get('ret_30'):.2f}% fuera de {detalles_rayen.get('t30_rango')})")
                if not detalles_rayen.get("ok_140"): fail_reasons.append(f"#140 ({detalles_rayen.get('ret_140'):.2f}% fuera de {detalles_rayen.get('t140_rango')})")
                msg_fail = " | ".join(fail_reasons)
                st.error(f"🚨 **AFS N° {afs_selected['num_analisis']} NO APTO RAYEN** ({msg_fail})")
                
            df_table = pd.DataFrame({
                "Tamiz N°": ["#20", "#30", "#140", "Total"],
                "Neto Grs": [f"{neto_20:.1f}", f"{neto_30:.1f}", f"{neto_140:.1f}", f"{neto_total:.1f}"],
                "% Acumulado Retenido": [f"{ret_20:.2f}%", f"{ret_30:.2f}%", f"{ret_140:.2f}%", "100.00%"]
            })
            st.write(f"Resultados AFS ({val_afs:.2f}) asignados a {m_label}:")
            st.table(df_table)
        else:
            st.warning(f"⚠️ Seleccione un AFS de la lista para la Muestra {m_label}.")
            
        col_fe1, col_fe2 = st.columns([1, 2])
        fe_val = col_fe1.number_input(f"% Fe2O3 para {m_label}:", 0.0, 100.0, float(m_data_prev.get("fe2o3", 0.35)), step=0.01, key=f"fe_{m_key}")
        
        fe_max = float(st.session_state.get('rayen_config', {}).get('%Fe2O3', {}).get('max', 0.50))
        if fe_val <= fe_max: col_fe2.success(f"✅ % Fe2O3 Conforme ({fe_val:.2f}% <= Máx {fe_max:.2f}%)")
        else: col_fe2.error(f"🚨 % Fe2O3 Fuera de Norma ({fe_val:.2f}% > Máx {fe_max:.2f}%)")
            
        return {
            "afs_id": afs_selected['id'] if afs_selected else None,
            "afs_num": afs_selected['num_analisis'] if afs_selected else "",
            "afs_val": val_afs,
            "neto_20": neto_20,
            "neto_30": neto_30,
            "neto_140": neto_140,
            "neto_total": neto_total,
            "ret_20": ret_20,
            "ret_30": ret_30,
            "ret_140": ret_140,
            "fe2o3": fe_val,
            "is_apto": is_apto,
            "msg_fail": msg_fail
        }
        
    m1_data = render_m_section("M1", "m1", chk_m1)
    m2_data = render_m_section("M2", "m2", chk_m2)
    m3_data = render_m_section("M3", "m3", chk_m3)
    
    st.divider()
    c_save, c_canc = st.columns(2)
    
    if c_save.button("💾 Guardar Protocolo Rayen", use_container_width=True, key="btn_save_proto_rayen"):
        m_activas = []
        if chk_m1:
            if not m1_data or not m1_data.get("afs_id"):
                st.error("❌ Debe seleccionar un AFS para la Muestra M1 antes de guardar.")
                return
            if not m1_data.get("is_apto"):
                st.error(f"🚨 La Muestra M1 (AFS N° {m1_data.get('afs_num')}) NO ES APTA RAYEN ({m1_data.get('msg_fail')}). Seleccione un AFS que cumpla los requisitos.")
                return
            m_activas.append("M1")
            
        if chk_m2:
            if not m2_data or not m2_data.get("afs_id"):
                st.error("❌ Debe seleccionar un AFS para la Muestra M2 antes de guardar.")
                return
            if not m2_data.get("is_apto"):
                st.error(f"🚨 La Muestra M2 (AFS N° {m2_data.get('afs_num')}) NO ES APTA RAYEN ({m2_data.get('msg_fail')}). Seleccione un AFS que cumpla los requisitos.")
                return
            m_activas.append("M2")
            
        if chk_m3:
            if not m3_data or not m3_data.get("afs_id"):
                st.error("❌ Debe seleccionar un AFS para la Muestra M3 antes de guardar.")
                return
            if not m3_data.get("is_apto"):
                st.error(f"🚨 La Muestra M3 (AFS N° {m3_data.get('afs_num')}) NO ES APTA RAYEN ({m3_data.get('msg_fail')}). Seleccione un AFS que cumpla los requisitos.")
                return
            m_activas.append("M3")
        
        if not m_activas:
            st.error("Debe habilitar al menos una muestra (M1, M2 o M3).")
            return
            
        rayen_payload = {
            "lote_tipo": lote_tipo,
            "m_activas": m_activas,
            "m1": m1_data,
            "m2": m2_data,
            "m3": m3_data
        }
        
        fe_c = datetime.now().strftime("%d/%m/%Y %H:%M")
        fe_v_s = f_v.strftime("%d/%m/%Y")
        u_act = st.session_state.get("nombre_usuario") or st.session_state.get("usuario_actual", "admin")
        
        conn_s = sqlite3.connect('laboratorio.db'); c_s = conn_s.cursor()
        
        if edit_id is not None:
            c_s.execute('''UPDATE analisis SET num_analisis=?, fecha_viaje=?, cliente=?, origen=?, clasificacion=?, producto=?, silo=?, observaciones=?, rayen_json=?, rayen_lote_tipo=?, rayen_fecha_elaboracion=?, modificado_por=?, fecha_modificacion=? WHERE id=?''',
                        (str(num), str(fe_v_s), str(cli), str(ori), str(cla), str(pro), str(sil), str(obs), json.dumps(rayen_payload), str(lote_tipo), str(fe_c), str(u_act), str(fe_c), int(edit_id)))
            target_id = int(edit_id)
        else:
            c_s.execute('''INSERT INTO analisis (tipo, num_analisis, fecha_carga, fecha_viaje, cliente, origen, clasificacion, producto, silo, observaciones, rayen_json, rayen_lote_tipo, rayen_fecha_elaboracion, creado_por, modificado_por, fecha_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        ("Rayen", str(num), str(fe_c), str(fe_v_s), str(cli), str(ori), str(cla), str(pro), str(sil), str(obs), json.dumps(rayen_payload), str(lote_tipo), str(fe_c), str(u_act), str(u_act), str(fe_c)))
            target_id = int(c_s.lastrowid)
            
        conn_s.commit(); conn_s.close()
        st.cache_data.clear()
        try:
            import gdrive_sync
            gdrive_sync.realizar_copia_seguridad_local()
        except: pass
        
        st.session_state["modo_armador_rayen"] = False
        st.session_state["edit_rayen_id"] = None
        st.session_state["base_afs_id_rayen"] = None
        st.session_state["reporte_seleccionado_id"] = target_id
        st.query_params.clear()
        st.query_params["report_id"] = str(target_id)
        st.rerun()
        
    if c_canc.button("❌ Cancelar", use_container_width=True, key="btn_cancel_proto_rayen"):
        st.session_state["modo_armador_rayen"] = False
        st.rerun()

if "report_id" in st.query_params and not st.session_state.get("modo_armador_rayen"):
    st.session_state.auth = True
    report_id = int(st.query_params["report_id"])
    
    st.sidebar.title("⚙️ Opciones del Reporte")
    with st.sidebar.expander("⚙️ Configuración Rendimientos"):
        render_config_rendimientos_ui("rep")
    with st.sidebar.expander("⚙️ Configuración Rayen"):
        render_config_rayen_ui("rep")
    with st.sidebar.expander("⚖️ Control de Equipos"):
        st.session_state.fecha_control_pesaje = st.date_input("Fecha Control Pesaje", st.session_state.fecha_control_pesaje, format="DD/MM/YYYY")
        
    mostrar_reporte_unico(report_id)
    st.stop()

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔑 Ingreso al Sistema")
        dict_usr = cargar_usuarios()
        opt_usr = list(dict_usr.keys())
        sel_u = st.selectbox("Seleccione Usuario:", opt_usr, format_func=lambda x: f"{x} ({dict_usr[x].get('nombre', '')})")
        pw = st.text_input("Contraseña:", type="password", key="input_pw_main")
        if st.button("Entrar", use_container_width=True, key="btn_main_login"):
            if sel_u in dict_usr and dict_usr[sel_u]["clave"] == pw:
                st.session_state.auth = True
                st.session_state.usuario_actual = sel_u
                st.session_state.nombre_usuario = dict_usr[sel_u].get("nombre", sel_u)
                st.session_state.rol_actual = dict_usr[sel_u].get("rol", "Operador")
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
else:
    u_curr = st.session_state.get("usuario_actual", "admin")
    u_nom = st.session_state.get("nombre_usuario", "Administrador")
    u_rol = st.session_state.get("rol_actual", "Master")
    
    st.sidebar.title("MENÚ")
    st.sidebar.info(f"👤 **Sesión:** {u_nom}  \n🏷️ **Rol:** {u_rol}")
    
    menu = st.sidebar.radio("Ir a:", ["Inicio", "AFS", "MF", "Fracking", "Tamaño Efectivo de Part.", "Ver Reportes", "📊 Métricas Tamiz #8", "📈 Control de Calidad #50/#100"])
    st.sidebar.divider()
    
    # Inyectar estado de sincronización
    try:
        import gdrive_sync
        sync_info = descargar_db_inicial()
        upload_info = gdrive_sync.LAST_SYNC
        with st.sidebar.expander("☁️ Estado de Nube Google Drive", expanded=True):
            if sync_info["status"] == "OK":
                st.success("Conectado con Google Drive")
                if sync_info["download_time"]:
                    st.caption(f"Descargado al arrancar: {sync_info['download_time']}")
                
                # Mostrar estado de la última subida
                if upload_info["upload_time"]:
                    st.info(f"Último guardado: {upload_info['upload_time']}")
                elif upload_info["status"] == "Error":
                    st.error(f"Error al subir: {upload_info['error']}")
            elif sync_info["status"] == "Error":
                st.error("Error de Sincronización")
                st.caption(sync_info["error"])
            else:
                st.warning(f"Estado: {sync_info['status']}")
                
            # Botón de sincronización forzada
            st.divider()
            if st.button("🔄 Sincronizar Ahora", use_container_width=True, key="btn_sync_gdrive_now"):
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error cargando módulo de sync: {e}")
    st.sidebar.divider()

    if u_rol == "Master":
        with st.sidebar.expander("👤 Gestión de Usuarios"):
            st.markdown("#### Administración de Usuarios")
            dict_usr = cargar_usuarios()
            
            id_edit = st.session_state.get("editing_user_id", "")
            usr_obj = dict_usr.get(id_edit, {})
            
            with st.form("form_nuevo_usr_side"):
                st.markdown(f"**{'Editar' if id_edit else 'Crear / Editar'} Usuario**")
                nu_id = st.text_input("Usuario ID (sin espacios):", value=id_edit).strip().lower()
                nu_nom = st.text_input("Nombre Completo:", value=usr_obj.get("nombre", ""))
                nu_pass = st.text_input("Contraseña:", value=usr_obj.get("clave", ""), type="password")
                rol_idx = 1 if usr_obj.get("rol") == "Master" else 0
                nu_rol = st.selectbox("Rol:", ["Operador", "Master"], index=rol_idx)
                
                c_g1, c_g2 = st.columns(2)
                sub_btn = c_g1.form_submit_button("➕ Guardar")
                can_btn = c_g2.form_submit_button("❌ Limpiar")
                
                if sub_btn:
                    if nu_id and nu_pass and nu_nom:
                        dict_usr[nu_id] = {"nombre": nu_nom, "clave": nu_pass, "rol": nu_rol}
                        guardar_usuarios(dict_usr)
                        st.session_state["editing_user_id"] = ""
                        st.success(f"Usuario '{nu_id}' guardado correctamente.")
                        st.rerun()
                    else: st.error("Complete todos los campos.")
                elif can_btn:
                    st.session_state["editing_user_id"] = ""
                    st.rerun()

            st.markdown("**Usuarios Registrados:**")
            for uk, uv in list(dict_usr.items()):
                c_u1, c_u2, c_u3 = st.columns([2.5, 1, 1])
                c_u1.write(f"• **`{uk}`** ({uv.get('rol')})  \n  _{uv.get('nombre')}_")
                
                if c_u2.button("✏️", key=f"btn_edit_usr_{uk}", help=f"Editar {uk}"):
                    st.session_state["editing_user_id"] = uk
                    st.rerun()
                    
                if uk != "admin":
                    if c_u3.button("🗑️", key=f"btn_del_usr_{uk}", help=f"Eliminar {uk}"):
                        del dict_usr[uk]
                        guardar_usuarios(dict_usr)
                        if st.session_state.get("editing_user_id") == uk:
                            st.session_state["editing_user_id"] = ""
                        st.success(f"Usuario '{uk}' eliminado.")
                        st.rerun()

    with st.sidebar.expander("💾 Copia de Seguridad"):
        st.markdown("**Respaldo de la Base de Datos**")
        db_path_file = os.path.join(BASE_DIR, "laboratorio.db")
        if os.path.exists(db_path_file):
            with open(db_path_file, "rb") as f_db:
                st.download_button(
                    label="📥 Descargar Base de Datos (.db)",
                    data=f_db.read(),
                    file_name=f"laboratorio_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                    mime="application/x-sqlite3"
                )

    with st.sidebar.expander("🖼️ Configuración Imágenes"):
        up_logo = st.file_uploader("Logo (Sup. Der.)", type=["png", "jpg"])
        if up_logo: 
            with open(LOGO_PATH, "wb") as f: f.write(up_logo.getbuffer())
            st.success("Logo guardado.")
        up_pie = st.file_uploader("Pie de Página", type=["png", "jpg"])
        if up_pie: 
            with open(PIE_PATH, "wb") as f: f.write(up_pie.getbuffer())
            st.success("Pie guardado.")
    with st.sidebar.expander("⚙️ Configuración Rendimientos"):
        render_config_rendimientos_ui("main")
    with st.sidebar.expander("⚙️ Configuración Rayen"):
        render_config_rayen_ui("main")
    with st.sidebar.expander("🔬 Equipamiento Rayen"):
        render_config_equipamiento_rayen_ui("main")
    with st.sidebar.expander("⚖️ Control de Equipos"):
        st.session_state.fecha_control_pesaje = st.date_input("Fecha Control Pesaje", st.session_state.fecha_control_pesaje, format="DD/MM/YYYY")

    if st.sidebar.button("🔒 Cerrar Sesión"): 
        st.session_state.auth = False
        st.session_state.usuario_actual = None
        st.session_state.nombre_usuario = None
        st.session_state.rol_actual = None
        st.rerun()

    if st.session_state.get("modo_armador_rayen"):
        armar_protocolo_rayen_ui()
    elif menu == "Inicio":
        render_dashboard_inicio_ui()
    elif menu in ["AFS", "MF", "Fracking", "Tamaño Efectivo de Part."]:
        tipo = menu; st.title(f"📥 Registro {tipo}")
        with st.form("carga"):
            c1, c2, c3 = st.columns(3); num = c1.text_input("Número Análisis"); f_v = c2.date_input("Fecha Viaje", format="DD/MM/YYYY"); cli = c3.text_input("Cliente")
            c4, c5, c6 = st.columns(3); ori = c4.text_input("Origen"); cla = c5.text_input("Clasificación"); pro = c6.text_input("Producto")
            c7, c8 = st.columns(2); sil = c7.text_input("Silo"); obs = c8.text_input("Observaciones")
            
            if tipo == "Tamaño Efectivo de Part.":
                st.subheader("Configuración de Tamices y Parámetros del Reporte")
                c_lim1, c_lim2 = st.columns(2)
                val_x = c_lim1.number_input("Límite Superior X (mm) - Max 1% Retenido Acumulado", value=1.40, step=0.01)
                val_y = c_lim2.number_input("Límite Inferior Y (mm) - Max 1% Que Pasa", value=0.70, step=0.01)
                
                df_ed = pd.DataFrame({
                    "Tamiz N°": ["#4", "#8", "#10", "#16", "#18", "#20", "#30", "#40", "#50", "#100", "#200", "Fdo."],
                    "Abertura (mm)": [4.75, 2.36, 2.00, 1.18, 1.00, 0.85, 0.60, 0.425, 0.30, 0.15, 0.075, 0.00],
                    "Neto Grs": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                })
                st.write("Indique las aberturas de mallas (mm) y los pesos netos obtenidos:")
                ed = st.data_editor(df_ed, hide_index=True, use_container_width=True, disabled=["Tamiz N°", "Abertura (mm)"])
            else:
                tam = TAMICES_AFS if tipo == "AFS" else (TAMICES_FRACKING if tipo == "Fracking" else TAMICES_MF)
                df_ed = pd.DataFrame({"Tamiz N°": tam, "Neto Grs": [0.0]*len(tam)})
                if tipo == "MF": df_ed.insert(1, "Abertura (mm)", ABERTURAS_MF)
                ed = st.data_editor(df_ed, hide_index=True, use_container_width=True, disabled=["Tamiz N°", "Abertura (mm)"])
                
            if st.form_submit_button("Guardar"):
                fe_c = datetime.now().strftime("%d/%m/%Y %H:%M"); fe_v_s = f_v.strftime("%d/%m/%Y")
                u_act = st.session_state.get("nombre_usuario") or st.session_state.get("usuario_actual", "admin")
                conn = sqlite3.connect('laboratorio.db'); c = conn.cursor()
                
                if tipo == "Tamaño Efectivo de Part.":
                    datos_dict = ed.to_dict(orient="records")
                    json_datos = json.dumps(datos_dict)
                    json_limites = json.dumps({"val_x": val_x, "val_y": val_y})
                    c.execute('''INSERT INTO analisis (tipo, num_analisis, fecha_carga, fecha_viaje, cliente, origen, clasificacion, producto, silo, observaciones, dominio, d10_json_datos, d10_limites_json, creado_por, modificado_por, fecha_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                              ("Tamaño Efectivo", num, fe_c, fe_v_s, cli, ori, cla, pro, sil, obs, obs, json_datos, json_limites, u_act, u_act, fe_c))
                else:
                    p = ed["Neto Grs"].tolist()
                    if tipo == "AFS": c.execute('''INSERT INTO analisis (tipo, num_analisis, fecha_carga, fecha_viaje, cliente, origen, clasificacion, producto, silo, observaciones, dominio, t8, t12, t20, t30, t40, t50, t70, t100, t140, t200, t270, tfdo, creado_por, modificado_por, fecha_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (tipo, num, fe_c, fe_v_s, cli, ori, cla, pro, sil, obs, obs, *p, u_act, u_act, fe_c))
                    elif tipo == "Fracking": c.execute('''INSERT INTO analisis (tipo, num_analisis, fecha_carga, fecha_viaje, cliente, origen, clasificacion, producto, silo, observaciones, dominio, t20, t30, t40, t50, t60, t70, t100, t140, tfdo, creado_por, modificado_por, fecha_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (tipo, num, fe_c, fe_v_s, cli, ori, cla, pro, sil, obs, obs, *p, u_act, u_act, fe_c))
                    else: c.execute('''INSERT INTO analisis (tipo, num_analisis, fecha_carga, fecha_viaje, cliente, origen, clasificacion, producto, silo, observaciones, dominio, mf4, mf8, mf18, mf30, mf50, mf100, tfdo, creado_por, modificado_por, fecha_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (tipo, num, fe_c, fe_v_s, cli, ori, cla, pro, sil, obs, obs, *p, u_act, u_act, fe_c))
                
                conn.commit(); conn.close()
                st.cache_data.clear()
                try:
                    import gdrive_sync
                    gdrive_sync.realizar_copia_seguridad_local()
                except: pass
                st.success("Guardado correctamente")

    elif menu == "Ver Reportes":
        df_hist = obtener_historial_calculado()
        if df_hist.empty:
            st.title("📜 Historial de Reportes")
            st.warning("No hay reportes cargados.")
        else:
            st.title("📜 Historial de Reportes")
            
            with st.expander("🔍 Filtros de Búsqueda Avanzada", expanded=False):
                col_f1, col_f2, col_f3 = st.columns(3)
                f_cliente = col_f1.text_input("Cliente / Producto")
                f_tipo = col_f2.multiselect("Tipo de Análisis", ["AFS", "Fracking", "MF", "Tamaño Efectivo", "Rayen"], default=["AFS", "Fracking", "MF", "Tamaño Efectivo", "Rayen"])
                col_f4, col_f5 = st.columns(2)
                r_afs = col_f4.slider("Rango AFS", 0.0, 150.0, (0.0, 150.0))
                r_mf = col_f5.slider("Rango Módulo Finura (MF)", 0.0, 6.0, (0.0, 6.0))
                
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                r_3070 = col_r1.slider("Rend. #30/70 (%)", 0.0, 100.0, 0.0)
                r_4070 = col_r2.slider("Rend. #40/70 (%)", 0.0, 100.0, 0.0)
                r_50140 = col_r3.slider("Rend. #50/140 (%)", 0.0, 100.0, 0.0)
                r_30140 = col_r4.slider("Rend. #30/140 (%)", 0.0, 100.0, 0.0)
                
            df_filtro = df_hist[df_hist['Tipo'].isin(f_tipo)]
            if f_cliente:
                df_filtro = df_filtro[df_filtro['Cliente'].str.contains(f_cliente, case=False) | df_filtro['Producto'].str.contains(f_cliente, case=False)]
            df_filtro = df_filtro[(df_filtro['AFS'] >= r_afs[0]) & (df_filtro['AFS'] <= r_afs[1]) & (df_filtro['MF'] >= r_mf[0]) & (df_filtro['MF'] <= r_mf[1])]
            df_filtro = df_filtro[(df_filtro['R_30/70'] >= r_3070) & (df_filtro['R_40/70'] >= r_4070) & (df_filtro['R_50/140'] >= r_50140) & (df_filtro['R_30/140'] >= r_30140)]
            
            # Crear columna con link de reporte directo
            df_filtro["Ver"] = df_filtro["ID"].apply(lambda x: f"/?report_id={x}")
            
            # Reordenar columnas para poner ID y el link al principio
            cols = ["ID", "Ver", "Tipo", "Análisis", "Fecha", "Cliente", "Producto", "creado_por", "AFS", "MF", "R_30/70", "R_40/70", "R_50/140", "R_30/140", "d10", "d60", "CU"]
            cols_existentes = [c for c in cols if c in df_filtro.columns]
            df_display = df_filtro[cols_existentes]
            
            column_config = {
                "ID": st.column_config.NumberColumn(
                    "ID",
                    format="%d"
                ),
                "Ver": st.column_config.LinkColumn(
                    "Ver Reporte",
                    display_text="📄 Abrir",
                    help="Abrir el reporte en una nueva pestaña"
                ),
                "creado_por": st.column_config.TextColumn(
                    "👤 Registrado Por",
                    help="Usuario que cargó la muestra"
                )
            }
            
            st.dataframe(
                df_display,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                height=550
            )

    elif menu == "📊 Métricas Tamiz #8":
        st.title("📊 Control y Métricas de Tamiz N° 8 (#8)")
        st.info("💡 **Criterio de Control de Calidad:** La presencia de material retenido en el Tamiz #8 es condición de rechazo de lote por partículas gruesas fuera de especificación.")
        
        df_hist = obtener_historial_calculado()
        if df_hist.empty:
            st.warning("No hay datos de análisis disponibles para generar métricas.")
        else:
            df_afs = df_hist[df_hist["Tipo"] == "AFS"].copy()
            if df_afs.empty:
                st.warning("No hay reportes de tipo AFS registrados aún.")
            else:
                # Normalizar columnas de texto para filtros sin perder muestras sin cliente o producto
                df_afs["Cliente_clean"] = df_afs["Cliente"].fillna("").astype(str).str.strip().replace(["", "-"], "(Sin Cliente)")
                df_afs["Producto_clean"] = df_afs["Producto"].fillna("").astype(str).str.strip().replace(["", "-"], "(Sin Producto)")
                
                # --- FILTROS DE BÚSQUEDA ---
                with st.expander("🔍 Filtros de Búsqueda y Control", expanded=True):
                    c_f1, c_f2, c_f3 = st.columns(3)
                    productos_unicos = sorted(df_afs["Producto_clean"].unique().tolist())
                    sel_prod = c_f1.multiselect("Filtrar por Producto:", productos_unicos, default=productos_unicos)
                    
                    clientes_unicos = sorted(df_afs["Cliente_clean"].unique().tolist())
                    sel_cli = c_f2.multiselect("Filtrar por Cliente:", clientes_unicos, default=clientes_unicos)
                    
                    solo_rechazos = c_f3.checkbox("Mostrar únicamente muestras con retenido (> 0 g) en #8", value=False)
                
                # Aplicar filtros
                df_filtered = df_afs.copy()
                if sel_prod:
                    df_filtered = df_filtered[df_filtered["Producto_clean"].isin(sel_prod)]
                if sel_cli:
                    df_filtered = df_filtered[df_filtered["Cliente_clean"].isin(sel_cli)]
                if solo_rechazos:
                    df_filtered = df_filtered[df_filtered["t8"] > 0]
                
                # --- KPI CARDS ---
                total_muestras = len(df_filtered)
                muestras_rechazadas = len(df_filtered[df_filtered["t8"] > 0])
                muestras_conformes = total_muestras - muestras_rechazadas
                pct_rechazo = (muestras_rechazadas / total_muestras * 100) if total_muestras > 0 else 0.0
                max_t8 = df_filtered["t8"].max() if not df_filtered.empty else 0.0
                
                col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
                col_kpi1.metric("Total Muestras AFS", f"{total_muestras}")
                col_kpi2.metric("Conformes (0g #8)", f"{muestras_conformes}", delta=f"{(100 - pct_rechazo):.1f}%", delta_color="normal")
                col_kpi3.metric("🚨 Con Retenido (>0g #8)", f"{muestras_rechazadas}", delta=f"{pct_rechazo:.1f}% Alerta", delta_color="inverse")
                col_kpi4.metric("Tasa de Rechazo", f"{pct_rechazo:.1f}%")
                col_kpi5.metric("Máx Retenido en #8", f"{max_t8:.2f} g")
                
                st.divider()
                
                # --- GRÁFICOS INTERACTIVOS PLOTLY ---
                tab_g1, tab_g2, tab_g3 = st.tabs(["📈 Control Temporal (#8 vs Análisis)", "🔵 Retenido #8 vs Número AFS", "📊 Rechazos por Producto / Silo"])
                
                with tab_g1:
                    st.subheader("1. Control de Calidad Temporal: Gramos Retenidos en Tamiz #8")
                    df_plot1 = df_filtered.sort_values(by="ID").copy()
                    
                    if df_plot1.empty:
                        st.info("No hay muestras para mostrar en el gráfico.")
                    else:
                        # Etiqueta secuencial clara para el eje X
                        df_plot1["Etiqueta_X"] = df_plot1.apply(lambda r: f"N° {r['Análisis']}<br>({r['Fecha'] or '-'})", axis=1)
                        colores_barras = ['#dc3545' if v > 0 else '#28a745' for v in df_plot1["t8"]]
                        
                        fig1 = go.Figure()
                        fig1.add_trace(go.Bar(
                            x=df_plot1["Etiqueta_X"],
                            y=df_plot1["t8"],
                            marker_color=colores_barras,
                            text=[f"{v:.2f}g (RECHAZO)" if v > 0 else "0.00g (OK)" for v in df_plot1["t8"]],
                            textposition='outside',
                            customdata=np.stack((df_plot1["Cliente_clean"], df_plot1["Producto_clean"], df_plot1["AFS"]), axis=-1),
                            hovertemplate="<b>%{x}</b><br>Retenido #8: <b>%{y:.2f} g</b><br>Cliente: %{customdata[0]}<br>Producto: %{customdata[1]}<br>Número AFS: %{customdata[2]}<extra></extra>"
                        ))
                        
                        fig1.update_layout(
                            xaxis_title="Muestras Analizadas (Orden Cronológico)",
                            yaxis_title="Retenido en Tamiz #8 (Gramos)",
                            xaxis=dict(type='category'),
                            yaxis=dict(rangemode='tozero'),
                            height=480,
                            margin=dict(t=30, b=50)
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                
                with tab_g2:
                    st.subheader("2. Correlación: Retenido en Tamiz #8 vs. Número AFS")
                    df_plot2 = df_filtered.copy()
                    fig2 = go.Figure()
                    for prod_name in df_plot2["Producto_clean"].unique():
                        sub_df = df_plot2[df_plot2["Producto_clean"] == prod_name]
                        fig2.add_trace(go.Scatter(
                            x=sub_df["AFS"], y=sub_df["t8"],
                            mode='markers', name=str(prod_name),
                            marker=dict(size=9),
                            text=sub_df.apply(lambda r: f"Análisis: {r['Análisis']}<br>AFS: {r['AFS']}<br>Retenido #8: {r['t8']:.2f}g", axis=1),
                            hoverinfo='text'
                        ))
                    fig2.update_layout(xaxis_title="Número AFS", yaxis_title="Retenido Tamiz #8 (Gramos)", height=450)
                    st.plotly_chart(fig2, use_container_width=True)
                
                with tab_g3:
                    st.subheader("3. Tasa de Conformidad / Rechazo por Producto")
                    if not df_filtered.empty:
                        df_g3 = df_filtered.groupby(["Producto_clean"]).apply(
                            lambda g: pd.Series({
                                "Conformes": (g["t8"] == 0).sum(),
                                "Rechazados": (g["t8"] > 0).sum()
                            })
                        ).reset_index()
                        
                        fig3 = go.Figure()
                        fig3.add_trace(go.Bar(x=df_g3["Producto_clean"], y=df_g3["Conformes"], name="Conformes (0g)", marker_color="green"))
                        fig3.add_trace(go.Bar(x=df_g3["Producto_clean"], y=df_g3["Rechazados"], name="Rechazados (>0g)", marker_color="red"))
                        fig3.update_layout(barmode='stack', xaxis_title="Producto", yaxis_title="Cantidad de Muestras", height=450)
                        st.plotly_chart(fig3, use_container_width=True)
                
                # --- TABLA DE AUDITORÍA Y DETALLE DE RECHAZOS ---
                st.divider()
                st.subheader("📋 Auditoría de Muestras Analizadas en Tamiz #8")
                
                df_audit = df_filtered.copy()
                df_audit["Estado #8"] = df_audit["t8"].apply(lambda x: "🚨 RECHAZO / ALERTA" if x > 0 else "✅ CONFORME")
                df_audit["Ver"] = df_audit["ID"].apply(lambda x: f"/?report_id={x}")
                
                cols_audit = ["ID", "Ver", "Estado #8", "Análisis", "Fecha", "Cliente", "Producto", "t8", "R_8", "AFS"]
                cols_audit_existentes = [c for c in cols_audit if c in df_audit.columns]
                
                column_config_audit = {
                    "ID": st.column_config.NumberColumn("ID", format="%d"),
                    "Ver": st.column_config.LinkColumn("Certificado", display_text="📄 Abrir"),
                    "t8": st.column_config.NumberColumn("Pesado #8 (g)", format="%.2f"),
                    "R_8": st.column_config.NumberColumn("% Retenido #8", format="%.2f%%"),
                    "AFS": st.column_config.NumberColumn("Número AFS", format="%.2f")
                }
                
                st.dataframe(
                    df_audit[cols_audit_existentes],
                    column_config=column_config_audit,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )

    elif menu == "📈 Control de Calidad #50/#100":
        st.title("📈 Control de Calidad: Requisito #50 / #100")
        st.info("💡 **Especificación de Control de Calidad:**  \n- Tamiz **#50**: Mínimo **10%** y Máximo **40%** Retenido.  \n- Tamiz **#100**: Mínimo **15%** Retenido.")
        
        df_hist = obtener_historial_calculado()
        if df_hist.empty:
            st.warning("No hay datos de análisis disponibles para generar métricas.")
        else:
            df_afs = df_hist[df_hist["Tipo"] == "AFS"].copy()
            if df_afs.empty:
                st.warning("No hay reportes de tipo AFS registrados aún.")
            else:
                # Normalizar columnas de texto para filtros sin perder muestras sin cliente o producto
                df_afs["Cliente_clean"] = df_afs["Cliente"].fillna("").astype(str).str.strip().replace(["", "-"], "(Sin Cliente)")
                df_afs["Producto_clean"] = df_afs["Producto"].fillna("").astype(str).str.strip().replace(["", "-"], "(Sin Producto)")
                
                # --- FILTROS DE BÚSQUEDA ---
                with st.expander("🔍 Filtros de Búsqueda y Control", expanded=True):
                    c_f1, c_f2, c_f3 = st.columns(3)
                    productos_unicos = sorted(df_afs["Producto_clean"].unique().tolist())
                    sel_prod = c_f1.multiselect("Filtrar por Producto:", productos_unicos, default=productos_unicos, key="qc_prod_sel")
                    
                    clientes_unicos = sorted(df_afs["Cliente_clean"].unique().tolist())
                    sel_cli = c_f2.multiselect("Filtrar por Cliente:", clientes_unicos, default=clientes_unicos, key="qc_cli_sel")
                    
                    # Filtro de período por mes/año
                    filtro_periodo_qc = c_f3.radio("Período:", ["Histórico Completo", "Filtrar por Mes/Año"], horizontal=True, key="qc_period_radio")
                    
                    if filtro_periodo_qc == "Filtrar por Mes/Año":
                        col_m_qc, col_a_qc = st.columns(2)
                        mes_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                        mes_sel_qc = col_m_qc.selectbox("Mes:", mes_nombres, index=datetime.now().month-1, key="qc_mes_sel")
                        mes_num_qc = mes_nombres.index(mes_sel_qc) + 1
                        anio_sel_qc = col_a_qc.selectbox("Año:", [2024, 2025, 2026], index=2, key="qc_anio_sel")
                
                # Aplicar filtros
                df_filtered = df_afs.copy()
                if sel_prod:
                    df_filtered = df_filtered[df_filtered["Producto_clean"].isin(sel_prod)]
                if sel_cli:
                    df_filtered = df_filtered[df_filtered["Cliente_clean"].isin(sel_cli)]
                    
                if filtro_periodo_qc == "Filtrar por Mes/Año":
                    try:
                        df_filtered['fecha_dt'] = pd.to_datetime(df_filtered['Fecha'], format='%d/%m/%Y', errors='coerce')
                        df_filtered = df_filtered[(df_filtered['fecha_dt'].dt.month == mes_num_qc) & (df_filtered['fecha_dt'].dt.year == anio_sel_qc)]
                    except:
                        pass
                
                # --- KPI CARDS ---
                total_muestras = len(df_filtered)
                muestras_conformes = len(df_filtered[df_filtered["Cumple_Req"] == 1])
                muestras_rechazadas = total_muestras - muestras_conformes
                pct_conformidad = (muestras_conformes / total_muestras * 100) if total_muestras > 0 else 0.0
                
                col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                col_kpi1.metric("Total Muestras Filtradas", f"{total_muestras}")
                col_kpi2.metric("✅ Conformes", f"{muestras_conformes}", delta=f"{pct_conformidad:.1f}%", delta_color="normal")
                col_kpi3.metric("🚨 No Conformes", f"{muestras_rechazadas}", delta=f"{(100.0 - pct_conformidad):.1f}%", delta_color="inverse")
                col_kpi4.metric("Tasa de Conformidad", f"{pct_conformidad:.1f}%")
                
                st.divider()
                
                # --- GRÁFICOS INTERACTIVOS PLOTLY ---
                tab_g1, tab_g2 = st.tabs(["📉 Control de Calidad: Tamiz #50 vs #100", "📊 Historial de Conformidad"])
                
                with tab_g1:
                    st.subheader("1. Gráfico de Control: Región de Conformidad #50 vs #100")
                    if df_filtered.empty:
                        st.info("No hay muestras para mostrar en el gráfico.")
                    else:
                        fig_scatter = go.Figure()
                        
                        # Caja de especificación (zona verde translúcida)
                        fig_scatter.add_shape(
                            type="rect",
                            x0=10.0, y0=15.0, x1=40.0, y1=100.0,
                            fillcolor="rgba(40, 167, 69, 0.15)",
                            line=dict(color="rgba(40, 167, 69, 0.5)", width=2),
                            name="Región Conforme"
                        )
                        
                        df_conf = df_filtered[df_filtered["Cumple_Req"] == 1]
                        df_nconf = df_filtered[df_filtered["Cumple_Req"] == 0]
                        
                        # Muestras Conformes
                        if not df_conf.empty:
                            fig_scatter.add_trace(go.Scatter(
                                x=df_conf["R_50"], y=df_conf["R_100"],
                                mode="markers",
                                name="Conformes (Cumplen)",
                                marker=dict(color="green", size=10, symbol="circle"),
                                text=df_conf.apply(lambda r: f"Análisis: {r['Análisis']}<br>Cliente: {r['Cliente_clean']}<br>#50: {r['R_50']}%<br>#100: {r['R_100']}%", axis=1),
                                hoverinfo="text"
                            ))
                        
                        # Muestras No Conformes
                        if not df_nconf.empty:
                            fig_scatter.add_trace(go.Scatter(
                                x=df_nconf["R_50"], y=df_nconf["R_100"],
                                mode="markers",
                                name="No Conformes (Rechazo)",
                                marker=dict(color="red", size=10, symbol="x"),
                                text=df_nconf.apply(lambda r: f"Análisis: {r['Análisis']}<br>Cliente: {r['Cliente_clean']}<br>#50: {r['R_50']}%<br>#100: {r['R_100']}%", axis=1),
                                hoverinfo="text"
                            ))
                        
                        fig_scatter.update_layout(
                            xaxis_title="Retenido en Tamiz #50 (%)",
                            yaxis_title="Retenido en Tamiz #100 (%)",
                            xaxis=dict(range=[0, 70]),
                            yaxis=dict(range=[0, 70]),
                            height=500
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        st.caption("💡 Muestras dentro de la zona verde cumplen con los dos requisitos: #50 entre 10% y 40%, y #100 mayor o igual al 15%.")
                        
                with tab_g2:
                    st.subheader("2. Historial de Conformidad Cronológico")
                    df_time = df_filtered.sort_values(by="ID").copy()
                    if df_time.empty:
                        st.info("No hay muestras para graficar.")
                    else:
                        df_time["Etiqueta_X"] = df_time.apply(lambda r: f"N° {r['Análisis']}<br>({r['Fecha'] or '-'})", axis=1)
                        df_time["Color"] = df_time["Cumple_Req"].apply(lambda x: "green" if x == 1 else "red")
                        
                        fig_time = go.Figure()
                        fig_time.add_trace(go.Scatter(
                            x=df_time["Etiqueta_X"], y=df_time["R_50"],
                            mode="lines+markers",
                            name="Tamiz #50",
                            line=dict(color="#10b981", width=2),
                            marker=dict(color=df_time["Color"], size=8)
                        ))
                        fig_time.add_trace(go.Scatter(
                            x=df_time["Etiqueta_X"], y=df_time["R_100"],
                            mode="lines+markers",
                            name="Tamiz #100",
                            line=dict(color="#3b82f6", width=2),
                            marker=dict(color=df_time["Color"], size=8)
                        ))
                        # Líneas de referencia
                        fig_time.add_hline(y=10.0, line_dash="dash", line_color="green", annotation_text="Min #50 (10%)")
                        fig_time.add_hline(y=40.0, line_dash="dash", line_color="green", annotation_text="Máx #50 (40%)")
                        fig_time.add_hline(y=15.0, line_dash="dash", line_color="blue", annotation_text="Min #100 (15%)")
                        
                        fig_time.update_layout(xaxis=dict(type="category"), yaxis=dict(title="Retenido (%)"), height=480)
                        st.plotly_chart(fig_time, use_container_width=True)
                
                # --- TABLA DE AUDITORÍA Y DESCARGA ---
                st.divider()
                st.subheader("📋 Detalle de Conformidad de Ensayos")
                
                df_audit = df_filtered.copy()
                df_audit["Estado Requisito"] = df_audit["Cumple_Req"].apply(lambda x: "✅ CUMPLE" if x == 1 else "🚨 NO CUMPLE")
                df_audit["Ver"] = df_audit["ID"].apply(lambda x: f"/?report_id={x}")
                
                # Columnas finales de la tabla
                cols_display = ["ID", "Ver", "Estado Requisito", "Análisis", "Fecha", "Cliente", "Producto", "R_50", "R_100"]
                df_display = df_audit[cols_display].copy()
                
                # Cambiar nombres de columna para presentación
                df_display.columns = ["ID", "Certificado", "Estado Requisito", "Análisis", "Fecha", "Cliente", "Producto", "Retenido #50 (%)", "Retenido #100 (%)"]
                
                st.dataframe(
                    df_display,
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", format="%d"),
                        "Certificado": st.column_config.LinkColumn("Certificado", display_text="📄 Abrir"),
                        "Retenido #50 (%)": st.column_config.NumberColumn("Ret. #50 (%)", format="%.2f"),
                        "Retenido #100 (%)": st.column_config.NumberColumn("Ret. #100 (%)", format="%.2f")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Descargas
                csv_data = df_display.to_csv(index=False, encoding='utf-8-sig')
                
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_display.to_excel(writer, index=False, sheet_name='Control de Calidad')
                excel_data = excel_buffer.getvalue()
                
                c_d1, c_d2 = st.columns(2)
                c_d1.download_button(
                    label="📥 Descargar Reporte (CSV)",
                    data=csv_data,
                    file_name="Reporte_Cumplimiento_50_100.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                c_d2.download_button(
                    label="📥 Descargar Reporte (Excel)",
                    data=excel_data,
                    file_name="Reporte_Cumplimiento_50_100.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )