# Configuración del servidor WSGI para Flask.
bind = "0.0.0.0:5000"  # Puerto interno del contenedor.
workers = 1  # Un proceso mantiene un único reintentador de correos.
threads = 4  # Atiende varias peticiones HTTP simultáneas.
accesslog = None  # Evita imprimir cada GET del panel.

def post_worker_init(worker):
    import threading  # Permite mantener los reintentos de correo existentes.
    from app import bucle_reintentos  # Recupera el proceso de correo original.
    threading.Thread(target=bucle_reintentos, daemon=True).start()  # Reintenta correos en segundo plano.
