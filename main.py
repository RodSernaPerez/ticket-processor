# Cloud Function entry point
from ticket_processor import process_webhook, get_access_token, init_gmail_watch

def gmail_webhook(request):
    """Endpoint para Gmail push notifications"""
    return process_webhook(request)

def setup_watch(request):
    """Configura la suscripción de webhook"""
    return init_gmail_watch()