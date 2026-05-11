# COES - Gestión de Insumos Odontológicos

![Django](https://img.shields.io/badge/Django-5.2-092e20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.12-3776ab?style=for-the-badge&logo=python)
![Celery](https://img.shields.io/badge/Celery-5.6-37814a?style=for-the-badge&logo=celery)
![Redis](https://img.shields.io/badge/Redis-6379-d82c20?style=for-the-badge&logo=redis)
![Ruff](https://img.shields.io/badge/Linter-Ruff-eb5023?style=for-the-badge)

**COES** es una solución integral diseñada para la administración y control de inventarios en el sector odontológico. El sistema permite gestionar el ciclo de vida de los insumos clínicos, desde su ingreso hasta su uso final, garantizando que el consultorio nunca se detenga por falta de stock o caducidad de materiales.

---

## 🚀 Características del Módulo

- **Control de Inventario:** Gestión detallada de resinas, anestesias, instrumental y descartables.
- **Trazabilidad de Caducidad:** Alertas automáticas para productos próximos a vencer.
- **Niveles de Stock Crítico:** Notificaciones inteligentes cuando el suministro baja de los niveles de seguridad.
- **Tareas Asíncronas:** Envío de reportes y notificaciones por correo mediante **Celery**.
- **Seguridad y Auditoría:** Registro histórico de todos los movimientos mediante `django-auditlog`.
- **Arquitectura Limpia:** Separación de entornos (Development/Production) y cumplimiento de estándares de código (PEP8).

---

## 🛠️ Stack Tecnológico

- **Lenguaje:** Python 3.12+
- **Framework:** Django 5.2 (MVT)
- **Base de Datos:** PostgreSQL (Producción) / SQLite (Desarrollo)
- **Cola de Tareas:** Celery & Redis
- **Estilo de Código:** Ruff (Linting & Formatting), Mypy (Static Typing)
- **Configuración:** Python-Decouple (Gestión de `.env`)

---

## 📂 Estructura del Proyecto

```text
COES/
├── apps/               # Aplicaciones del negocio (inventory, core, users)
├── cfg/                # Configuración central del proyecto
│   └── settings/       # Configuración por entornos (base, dev, prod)
├── requirements/       # Dependencias separadas por entorno
├── static/             # Archivos CSS, JS e imágenes del sistema
├── manage.py           # Script de gestión de Django
├── Makefile            # Comandos de automatización
└── pyproject.toml      # Configuración de Ruff, Black y Mypy
```

---

## 🔧 Instalación y Configuración (Ubuntu)

### 1. Clonar y preparar entorno

```bash
git clone [https://github.com/tu-usuario/COES.git](https://github.com/tu-usuario/COES.git)
cd COES
```

### 2. Crear entorno virtual e instalar dependencias

El proyecto utiliza un `Makefile` para simplificar la gestión:

```bash
make venv
source coes-env/bin/activate
make install-dev
```

### 3. Variables de Entorno

Copia el archivo de plantilla y configura tus credenciales (DB, Email, Redis):

```bash
cp template.env .env
```

### 4. Ejecutar el proyecto

```bash
make run-dev
```

*Este comando aplicará migraciones, creará un superusuario de desarrollo (`develop`) y levantará el servidor en `localhost:8000`.*

---

## 💡 Comandos de Automatización

Utiliza `make` para ejecutar tareas comunes de forma rápida:

| Comando | Descripción |
| --- | --- |
| `make run-dev` | Inicia el servidor de desarrollo y aplica migraciones. |
| `make celery` | Inicia el worker de Celery para tareas en segundo plano. |
| `make lint` | Ejecuta el análisis estático (Ruff, Pylint, Mypy). |
| `make format` | Formatea el código automáticamente con Ruff. |
| `make seed` | Puebla la base de datos con datos de prueba (Insumos/Categorías). |
| `make clean` | Elimina archivos temporales y caché de Python. |

---

## 🛡️ Calidad de Código

Para mantener el estándar de calidad en **COES**, antes de realizar un commit, asegúrate de pasar los linters:

```bash
make lint
```

*Nota: Ruff ignorará automáticamente la carpeta `coes-env/` gracias a la configuración en `pyproject.toml`.*

---

## 📄 Licencia

Propiedad privada. Prohibida su reproducción total o parcial sin autorización.

---

**Desarrollado con precisión para el sector salud.**