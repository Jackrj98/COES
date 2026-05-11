import multiprocessing

proc_name = "gunicorn_coes"  # 'name' no es válido, es 'proc_name'

loglevel = "info"

# Logs
errorlog  = "/var/log/gunicorn/error.log"   # 'error_log' → 'errorlog'
accesslog = "/var/log/gunicorn/access.log"

# Binding
bind = "unix:/tmp/gunicorn-coes.sock"

# Workers
workers      = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads      = 2

# Timeouts
timeout         = 120
graceful_timeout = 30
keepalive       = 5

# Requests
max_requests        = 1000
max_requests_jitter = 50

# Performance
preload_app = True