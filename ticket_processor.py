#!/usr/bin/env python3
"""
Ticket Processor - Automatiza el procesamiento de tickets de supermercado
Integra Gmail, Google Sheets y Supabase
"""

import os
import json
import re
import requests
import subprocess
from datetime import datetime

# Configuración
SUPABASE_URL = "https://xdhsgbpiksurtowbwnok.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SHEET_ID = "1YHlD139TWtKctDMwbhU4BWg87YVdn8ZYv7NPbPjGnik"
GOG_ACCOUNT = "rosepe94oclaw@gmail.com"

# Refresh token para gog (usar variables de entorno)
GOG_REFRESH_TOKEN = os.environ.get("GOG_REFRESH_TOKEN")
GOG_CLIENT_ID = os.environ.get("GOG_CLIENT_ID")
GOG_CLIENT_SECRET = os.environ.get("GOG_CLIENT_SECRET")


def get_gog_access_token():
    """Refresca el token de gog"""
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "refresh_token": GOG_REFRESH_TOKEN,
            "client_id": GOG_CLIENT_ID,
            "client_secret": GOG_CLIENT_SECRET,
            "grant_type": "refresh_token"
        }
    )
    return resp.json().get("access_token")


def run_gog(*args):
    """Ejecuta un comando gog"""
    token = get_gog_access_token()
    cmd = ["gog", *args]
    env = os.environ.copy()
    env["GOG_ACCESS_TOKEN"] = token
    env["GOG_ACCOUNT"] = GOG_ACCOUNT
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout


def classify_product(product_name: str) -> tuple:
    """Clasifica un producto en dos niveles"""
    name = product_name.upper()
    
    # Categoría N2
    if any(x in name for x in ["YOGUR", "QUESO", "LECHE", "MANTEQUILLA"]):
        cat_n2 = "Lácteos"
    elif any(x in name for x in ["SÁNDWICH", "PAN", "BAGUETTE", "HORNEADO"]):
        cat_n2 = "Panadería"
    elif any(x in name for x in ["CEBOLLA", "PIMIENTO", "TOMATE", "AJO", "LECHUGA", "PATATA"]):
        cat_n2 = "Verduras"
    elif any(x in name for x in ["OREJA", "CARNE", "POLLO", "VACUNO", "CERDO"]):
        cat_n2 = "Carne"
    elif any(x in name for x in ["LANGOSTINO", "MERLUZA", "BACALAO", "SARDINA", "PESCADO"]):
        cat_n2 = "Pescado"
    elif any(x in name for x in ["POTON", "JUDÍA", "LENTEJA", "GARBANZO", "LEGUMBRE"]):
        cat_n2 = "Legumbres"
    elif any(x in name for x in ["VINAGRE", "SAL", "AZÚCAR", "ESPECIA", "CONDIMENTO"]):
        cat_n2 = "Condimentos"
    elif any(x in name for x in ["PLÁTANO", "MANZANA", "PERA", "FRUTA", "MANGO"]):
        cat_n2 = "Frutas"
    else:
        cat_n2 = "Otros"
    
    cat_n1 = "Alimentación"
    return cat_n1, cat_n2


def insert_to_supabase(product: dict):
    """Inserta un producto en Supabase"""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/tickets_gastos",
        headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        },
        json=product
    )
    return resp.status_code == 201


def process_ticket_from_email(message_id: str):
    """Procesa un ticket desde un email"""
    # Obtener el email
    email_data = run_gog("gmail", "get", message_id)
    
    # Extraer comercio del asunto
    match = re.search(r'(\d{8})\s+(\w+)', email_data)
    if match:
        date_str = match.group(1)
        comercio = match.group(2)
    
    # Si hay adjunto PDF, descargar y procesar
    # ... lógica de parsing del PDF
    
    # Añadir a Sheets
    run_gog("sheets", "append", SHEET_ID, "Hoja 1!A:I", ...)
    
    # Añadir a Supabase
    # ...


if __name__ == "__main__":
    print("Ticket Processor listo")
    # Implementar polling de emails o webhook