import sqlite3
import os
import uuid
from datetime import datetime
import json
import requests
import streamlit as st

DB_FILE = "finanzas_agencia.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla Ingresos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingresos (
        id TEXT PRIMARY KEY,
        sociedad TEXT,
        local TEXT,
        canal TEXT,
        monto REAL,
        fecha TEXT,
        notas TEXT,
        created_at TEXT
    )
    """)
    
    # Tabla Costos Fijos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS costos_fijos (
        id TEXT PRIMARY KEY,
        sociedad TEXT,
        local TEXT,
        categoria TEXT,
        monto REAL,
        fecha TEXT,
        notas TEXT,
        created_at TEXT
    )
    """)
    
    # Tabla Facturas SII (Con UNIQUE constraint para evitar duplicados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facturas_sii (
        id TEXT PRIMARY KEY,
        sociedad TEXT,
        rut_proveedor TEXT,
        nombre_proveedor TEXT,
        folio TEXT,
        monto_neto REAL,
        monto_iva REAL,
        monto_total REAL,
        fecha_emision TEXT,
        categoria_ia TEXT,
        created_at TEXT,
        UNIQUE(sociedad, rut_proveedor, folio)
    )
    """)
    
    conn.commit()
    conn.close()

# Inicializar tablas al cargar el módulo
init_db()

# ================= FUNCIONES DE INSERCIÓN =================

def registrar_ingreso(sociedad, local, canal, monto, fecha, notas=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    ingreso_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO ingresos (id, sociedad, local, canal, monto, fecha, notas, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ingreso_id, sociedad, local, canal, float(monto), fecha, notas, created_at))
    
    conn.commit()
    conn.close()
    return ingreso_id

def registrar_costo_fijo(sociedad, local, categoria, monto, fecha, notas=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    costo_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO costos_fijos (id, sociedad, local, categoria, monto, fecha, notas, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (costo_id, sociedad, local, categoria, float(monto), fecha, notas, created_at))
    
    conn.commit()
    conn.close()
    return costo_id

def registrar_factura_sii(sociedad, rut_proveedor, nombre_proveedor, folio, monto_neto, monto_iva, monto_total, fecha_emision, categoria_ia):
    """
    Intenta insertar una factura del SII.
    Retorna True si fue insertada exitosamente (nueva).
    Retorna False si ya existía en la base de datos (duplicada).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    factura_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    try:
        cursor.execute("""
        INSERT INTO facturas_sii (id, sociedad, rut_proveedor, nombre_proveedor, folio, monto_neto, monto_iva, monto_total, fecha_emision, categoria_ia, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (factura_id, sociedad, rut_proveedor, nombre_proveedor, str(folio), float(monto_neto), float(monto_iva), float(monto_total), fecha_emision, categoria_ia, created_at))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Colisión de UNIQUE constraint (Factura Duplicada)
        conn.close()
        return False

# ================= FUNCIONES DE CONSULTA =================

def obtener_ingresos(sociedad, fecha_inicio=None, fecha_fin=None):
    conn = get_db_connection()
    query = "SELECT * FROM ingresos WHERE sociedad = ?"
    params = [sociedad]
    
    if fecha_inicio and fecha_fin:
        query += " AND fecha BETWEEN ? AND ?"
        params.extend([fecha_inicio, fecha_fin])
        
    query += " ORDER BY fecha DESC"
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obtener_costos_fijos(sociedad, fecha_inicio=None, fecha_fin=None):
    conn = get_db_connection()
    query = "SELECT * FROM costos_fijos WHERE sociedad = ?"
    params = [sociedad]
    
    if fecha_inicio and fecha_fin:
        query += " AND fecha BETWEEN ? AND ?"
        params.extend([fecha_inicio, fecha_fin])
        
    query += " ORDER BY fecha DESC"
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obtener_facturas_sii(sociedad, fecha_inicio=None, fecha_fin=None):
    conn = get_db_connection()
    query = "SELECT * FROM facturas_sii WHERE sociedad = ?"
    params = [sociedad]
    
    if fecha_inicio and fecha_fin:
        query += " AND fecha_emision BETWEEN ? AND ?"
        params.extend([fecha_inicio, fecha_fin])
        
    query += " ORDER BY fecha_emision DESC"
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def eliminar_registro(tabla, registro_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {tabla} WHERE id = ?", (registro_id,))
    conn.commit()
    conn.close()

def eliminar_facturas_sociedad(sociedad):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facturas_sii")
    conn.commit()
    conn.close()
