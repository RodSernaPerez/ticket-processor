#!/usr/bin/env python3
"""
Ticket Processor - Automatiza el procesamiento de tickets de supermercado
Integra Gmail, Google Sheets y Supabase
"""

import os
import re
import requests
import subprocess
import base64
from datetime import datetime

# Configuración desde variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xdhsgbpiksurtowbwnok.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SHEET_ID = os.environ.get("SHEET_ID", "1YHlD139TWtKctDMwbhU4BWg87YVdn8ZYv7NPbPjGnik")
GOG_ACCOUNT = os.environ.get("GOG_ACCOUNT", "rosepe94oclaw@gmail.com")
GOG_REFRESH_TOKEN = os.environ.get("GOG_REFRESH_TOKEN")
GOG_CLIENT_ID = os.environ.get("GOG_CLIENT_ID")
GOG_CLIENT_SECRET = os.environ.get("GOG_CLIENT_SECRET")

SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/spreadsheets"


def get_access_token():
    """Refresca el token OAuth"""
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


def gmail_search(query="has:attachment newer_than:30d"):
    """Busca emails en Gmail"""
    token = get_access_token()
    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages:batchQuery",
        headers={"Authorization": f"Bearer {token}"},
        json={"q": query}
    )
    return resp.json()


def get_email(message_id):
    """Obtiene un email completo"""
    token = get_access_token()
    resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.json()


def get_attachment(message_id, attachment_id):
    """Descarga un adjunto"""
    token = get_access_token()
    resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = resp.json()
    return base64.urlsafe_b64decode(data["data"])


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
    elif any(x in name for x in ["OREJA", "CARNE", "POLLO", "VACUNO", "CERDO", "POLLO"]):
        cat_n2 = "Carne"
    elif any(x in name for x in ["LANGOSTINO", "MERLUZA", "BACALAO", "SARDINA", "PESCADO", "ATÚN"]):
        cat_n2 = "Pescado"
    elif any(x in name for x in ["POTON", "JUDÍA", "LENTEJA", "GARBANZO", "LEGUMBRE", "ALUBIA"]):
        cat_n2 = "Legumbres"
    elif any(x in name for x in ["VINAGRE", "SAL", "AZÚCAR", "ESPECIA", "CONDIMENTO", "ACEITE"]):
        cat_n2 = "Condimentos"
    elif any(x in name for x in ["PLÁTANO", "MANZANA", "PERA", "FRUTA", "MANGO", "NARANJA", "MANDARINA"]):
        cat_n2 = "Frutas"
    elif any(x in name for x in ["CEREAL", "AVENA", "GALLETAS"]):
        cat_n2 = "Cereales"
    elif any(x in name for x in ["DETERSER", "CHAMPÚ", "PRODUCTO LIMPIEZA"]):
        cat_n2 = "Limpieza"
    else:
        cat_n2 = "Otros"
    
    cat_n1 = "Alimentación" if cat_n2 not in ["Limpieza", "Otros"] else "Otros"
    return cat_n1, cat_n2


def parse_ticket_text(text: str) -> list:
    """Parsea tickets de Mercadona (formato texto)"""
    products = []
    
    # Patrones comunes en tickets
    lines = text.split('\n')
    for line in lines:
        # Buscar líneas con formato: PRODUCTO CANTIDAD PRECIO
        match = re.match(r'(.+?)\s+(\d+[,.]\d+)(?:\s*(?:kg|uds|uds|ud|\.kg))?\s*([\d,]+)\s*€', line, re.IGNORECASE)
        if match:
            product = match.group(1).strip()
            quantity = match.group(2)
            price = match.group(3).replace(',', '.')
            
            cat_n1, cat_n2 = classify_product(product)
            products.append({
                "producto": product,
                "unidades": quantity,
                "precio_total": float(price),
                "categoria_n1": cat_n1,
                "categoria_n2": cat_n2
            })
    
    return products


def append_to_sheets(products: list, purchase_id: str, comercio: str, fecha: str):
    """Añade productos a Google Sheets"""
    token = get_access_token()
    
    rows = []
    for p in products:
        rows.append([
            fecha, comercio, purchase_id, p["producto"], 
            p["unidades"], "N/A", p["precio_total"],
            p["categoria_n1"], p["categoria_n2"]
        ])
    
    resp = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Hoja 1'!A:I:append",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "values": rows,
            "valueInputOption": "USER_ENTERED"
        }
    )
    return resp.status_code == 200


def insert_to_supabase(products: list, purchase_id: str, comercio: str, fecha: str):
    """Inserta productos en Supabase"""
    rows = []
    for p in products:
        rows.append({
            "fecha": fecha,
            "comercio": comercio,
            "id_compra": purchase_id,
            "producto": p["producto"],
            "unidades": p["unidades"],
            "precio_total": p["precio_total"],
            "categoria_n1": p["categoria_n1"],
            "categoria_n2": p["categoria_n2"]
        })
    
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/tickets_gastos",
        headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        },
        json=rows
    )
    return resp.status_code == 201


def label_email(message_id: str, add_label: str):
    """Añade etiqueta a email"""
    token = get_access_token()
    requests.post(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
        headers={"Authorization": f"Bearer {token}"},
        json={"addLabelIds": [add_label]}
    )


def main():
    """Proceso principal"""
    # Buscar emails sin procesar
    emails = gmail_search("has:attachment is:unread")
    
    if "messages" not in emails:
        print("No hay emails nuevos")
        return
    
    for msg in emails["messages"]:
        email = get_email(msg["id"])
        payload = email.get("payload", {})
        
        # Extraer información del asunto
        headers = payload.get("headers", [])
        subject = ""
        for h in headers:
            if h.get("name") == "Subject":
                subject = h.get("value", "")
        
        # Extraer fecha
        date_str = email.get("snippet", "")[:10]  # Simplificado
        fecha = datetime.now().strftime("%Y-%m-%d")
        
        # Extraer ID compra del asunto
        match = re.search(r'(\d{6,10})', subject)
        purchase_id = match.group(1) if match else "unknown"
        
        # Extraer comercio
        comercio = "Mercadona" if "mercadona" in subject.lower() else "Desconocido"
        
        # Procesar adjuntos
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("filename"):
                filename = part.get("filename", "")
                attachment_id = part.get("body", {}).get("attachmentId")
                
                if attachment_id:
                    content = get_attachment(msg["id"], attachment_id)
                    
                    if filename.lower().endswith('.pdf'):
                        # Usar pdftotext para extraer
                        text = subprocess.run(
                            ["pdftotext", "-", "-"], 
                            input=content, 
                            capture_output=True, 
                            text=True
                        ).stdout
                    else:
                        text = content.decode('utf-8', errors='ignore')
                    
                    products = parse_ticket_text(text)
                    
                    if products:
                        append_to_sheets(products, purchase_id, comercio, fecha)
                        insert_to_supabase(products, purchase_id, comercio, fecha)
                        label_email(msg["id"], "Procesado")  # Etiqueta "Procesado"
                        
                        print(f"Procesado ticket {purchase_id}: {len(products)} productos")


if __name__ == "__main__":
    main()