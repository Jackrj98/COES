import multiprocessing
import os

# Nombre del proceso
proc_name = "gunicorn_coes"

# Nivel de log
loglevel = "info"

# Directorio de logs
log_dir = "/var/log/gunicorn"
os.makedirs(log_dir, exist_ok=True)

# Logs
errorlog = os.path.join(log_dir, "error.log")
accesslog = os.path.join(log_dir, "access.log")

# Binding - Usar TCP en lugar de socket Unix
bind = "0.0.0.0:8000"  # Cambiar de socket Unix a TCP

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Requests
max_requests = 1000
max_requests_jitter = 50

# Performance
preload_app = True

# Configuración adicional
worker_tmp_dir = "/dev/shm"

def post_fork(server, worker):
    """Configuración después de fork del worker"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )