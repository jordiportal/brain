# 📚 Persistent Admin Execution Agent - Guía Completa

## 🎯 Visión General

El **Persistent Admin Execution Agent** es un agente especializado para tareas administrativas y de automatización que requieren:

- ✅ **Persistencia**: Scripts y datos se guardan en volumen permanente
- ✅ **Acceso a Red**: Puede descargar archivos y conectarse a APIs
- ✅ **Long-running**: Timeouts más largos (5 minutos vs 30 segundos)
- ✅ **Estado**: Mantiene archivos, logs y datos entre ejecuciones

---

## 🆚 Diferencias con Code Execution Agent

| Aspecto | Code Execution | Persistent Admin |
|---------|---------------|------------------|
| **Contenedor** | Efímero (`docker run --rm`) | Permanente (named container) |
| **Volumen** | No | Sí (`/workspace` persistente) |
| **Red** | Deshabilitada (`--network=none`) | Habilitada (acceso completo) |
| **Duración** | 30 segundos | 300 segundos (5 min) |
| **Scripts** | No se guardan | Se guardan por defecto |
| **Uso** | Cálculos aislados | Tareas administrativas |
| **Reintentos** | 3 | 2 |
| **Bibliotecas** | Básicas | Extendidas (web, schedule, DB) |

---

## 📁 Estructura del Workspace

El contenedor persistente tiene la siguiente estructura:

```
/workspace/
├── scripts/          # Scripts Python guardados
│   ├── download_files_20260123.py
│   ├── monitor_api_20260123.py
│   └── backup_db_20260123.py
├── downloads/        # Archivos descargados
│   ├── report.pdf
│   └── data.csv
├── data/             # Datos persistentes
│   ├── state.json
│   └── cache.db
└── logs/             # Logs de ejecuciones
    ├── 2026-01-23.log
    └── errors.log
```

---

## 🎯 Casos de Uso

### 1. **Descargar Archivos Automáticamente**

```python
# Ejemplo: Descargar PDF diariamente
import requests
from pathlib import Path
from datetime import datetime

url = "https://example.com/daily-report.pdf"
filename = Path("/workspace/downloads") / f"report_{datetime.now().strftime('%Y%m%d')}.pdf"

response = requests.get(url, timeout=60)
response.raise_for_status()
filename.write_bytes(response.content)

print(f"✅ Descargado: {filename}")
```

**Petición al agente**:
> "Descarga el PDF de https://example.com/daily-report.pdf y guárdalo en downloads con la fecha de hoy"

---

### 2. **Monitorear Cambios en una API**

```python
# Ejemplo: Detectar cambios en API y notificar
import requests
import json
from pathlib import Path

STATE_FILE = Path("/workspace/data/api_state.json")
API_URL = "https://api.example.com/data"

# Cargar estado anterior
if STATE_FILE.exists():
    old_data = json.loads(STATE_FILE.read_text())
else:
    old_data = None

# Obtener datos actuales
new_data = requests.get(API_URL, timeout=30).json()

# Detectar cambios
if new_data != old_data:
    print(f"🔔 CAMBIO DETECTADO:")
    print(json.dumps(new_data, indent=2))
    STATE_FILE.write_text(json.dumps(new_data))
else:
    print("✅ Sin cambios")
```

**Petición al agente**:
> "Monitorea https://api.example.com/data y notifícame si cambia algo"

---

### 3. **Programar Ejecución de Cadenas Brain**

```python
# Ejemplo: Ejecutar una cadena Brain cada hora
import requests
import schedule
import time
import os

API_URL = os.getenv("API_URL", "http://api:8000")
CHAIN_ID = "rag"  # O cualquier otra cadena

def ejecutar_cadena():
    print(f"🚀 Ejecutando cadena {CHAIN_ID}...")
    response = requests.post(
        f"{API_URL}/api/v1/chains/{CHAIN_ID}/invoke",
        json={"message": "Busca documentos actualizados"},
        timeout=60
    )
    print(f"✅ Respuesta: {response.json()}")

# Programar cada hora
schedule.every().hour.do(ejecutar_cadena)

# Ejecutar 3 veces para testing (en producción sería while True)
for i in range(3):
    schedule.run_pending()
    time.sleep(3600)  # 1 hora
```

**Petición al agente**:
> "Programa la cadena RAG para que se ejecute cada hora y busque documentos actualizados"

---

### 4. **Backup Automatizado de PostgreSQL**

```python
# Ejemplo: Exportar datos de PostgreSQL
import psycopg2
import json
from pathlib import Path
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
BACKUP_DIR = Path("/workspace/data/backups")
BACKUP_DIR.mkdir(exist_ok=True)

# Conectar y exportar
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("SELECT * FROM brain_chains")
chains = cursor.fetchall()

# Guardar backup
backup_file = BACKUP_DIR / f"chains_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup_file.write_text(json.dumps(chains, default=str, indent=2))

print(f"✅ Backup guardado: {backup_file}")

conn.close()
```

**Petición al agente**:
> "Exporta todas las cadenas de la base de datos a un archivo JSON con la fecha actual"

---

### 5. **Web Scraping con Detección de Novedades**

```python
# Ejemplo: Scraping de página web con detección de cambios
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import hashlib
import json

URL = "https://example.com/news"
STATE_FILE = Path("/workspace/data/scraping_state.json")
DOWNLOADS_DIR = Path("/workspace/downloads")

# Obtener contenido
response = requests.get(URL, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

# Extraer noticias
news = []
for article in soup.find_all('article', class_='news-item'):
    news.append({
        'title': article.find('h2').text,
        'url': article.find('a')['href'],
        'date': article.find('time').text
    })

# Calcular hash para detectar cambios
content_hash = hashlib.md5(json.dumps(news, sort_keys=True).encode()).hexdigest()

# Cargar estado anterior
if STATE_FILE.exists():
    old_state = json.loads(STATE_FILE.read_text())
    old_hash = old_state.get('hash')
else:
    old_hash = None

# Detectar novedades
if content_hash != old_hash:
    print(f"🆕 NOVEDADES DETECTADAS ({len(news)} noticias)")
    
    # Guardar novedades
    news_file = DOWNLOADS_DIR / f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    news_file.write_text(json.dumps(news, indent=2, ensure_ascii=False))
    
    # Actualizar estado
    STATE_FILE.write_text(json.dumps({'hash': content_hash, 'date': str(datetime.now())}))
    
    print(f"✅ Guardado en: {news_file}")
else:
    print("✅ Sin novedades")
```

**Petición al agente**:
> "Monitorea https://example.com/news y descarga las noticias cada vez que haya cambios"

---

## 📚 Bibliotecas Disponibles

El contenedor persistente incluye:

### Web & HTTP
- `requests` - HTTP client
- `httpx` - Async HTTP client
- `aiohttp` - Async HTTP/WebSocket
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML parser

### Scheduling
- `schedule` - Cron-like scheduling
- `apscheduler` - Advanced scheduling

### Database
- `psycopg2-binary` - PostgreSQL
- `redis` - Redis client

### Files
- `openpyxl` - Excel files
- `python-docx` - Word documents
- `PyPDF2` - PDF files

### Data Science
- `numpy` - Arrays y matemáticas
- `pandas` - DataFrames
- `matplotlib` - Gráficas

### Utils
- `python-dotenv` - .env files
- `pyyaml` - YAML files

---

## 🚀 Uso del Agente

### Desde la GUI

```
1. Ir a Chains
2. Seleccionar: persistent_admin
3. Escribir petición
4. Ejecutar
```

### Desde la API

```bash
curl -X POST 'http://localhost:8000/api/v1/chains/persistent_admin/invoke/stream' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Descarga el archivo de https://example.com/data.csv",
    "save_script": true,
    "script_name": "download_data.py"
  }'
```

### Parámetros Opcionales

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `message` | string | - | Petición del usuario |
| `save_script` | boolean | `true` | Guardar script en /workspace/scripts |
| `script_name` | string | auto | Nombre del script (auto-generado si no se proporciona) |
| `max_retries` | int | `2` | Número de reintentos en caso de error |

---

## 🔧 Gestión de Scripts Guardados

### Listar Scripts

```python
from code_executor.persistent_executor import get_persistent_executor

executor = get_persistent_executor()
scripts = executor.list_scripts()
print(scripts)
# ['download_data.py', 'monitor_api.py', 'backup_db.py']
```

### Leer un Script

```python
content = executor.read_file("scripts/download_data.py")
print(content)
```

### Ejecutar un Script Existente

```python
result = await executor.execute_python(
    code=content,
    script_name="download_data.py",
    save_script=False  # No sobrescribir
)
```

### Eliminar un Script

```python
success = executor.delete_file("scripts/old_script.py")
```

---

## 🧪 Testing

### Build del Contenedor

```bash
cd /Users/jordip/cursor/brain
docker compose build persistent-runner
```

### Levantar el Servicio

```bash
docker compose up -d persistent-runner
```

### Verificar Estado

```bash
docker ps | grep persistent-runner
# Debe aparecer como "Up" y "healthy"
```

### Test Manual

```bash
# Ejecutar comando en el contenedor
docker exec brain-persistent-runner python -c "print('Hello from persistent container')"

# Ver workspace
docker exec brain-persistent-runner ls -la /workspace

# Ver scripts guardados
docker exec brain-persistent-runner ls -la /workspace/scripts
```

### Test del Agente

```bash
curl -X POST 'http://localhost:8000/api/v1/chains/persistent_admin/invoke' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Crea un script que imprima la fecha actual y guárdalo",
    "save_script": true
  }'
```

---

## 📊 Monitoreo

### Ver Logs del Contenedor

```bash
docker logs brain-persistent-runner -f
```

### Ver Archivos en Workspace

```bash
# Scripts
docker exec brain-persistent-runner ls -lh /workspace/scripts

# Downloads
docker exec brain-persistent-runner ls -lh /workspace/downloads

# Logs
docker exec brain-persistent-runner ls -lh /workspace/logs
```

### Inspeccionar Volumen

```bash
docker volume inspect brain-persistent-workspace
```

---

## ⚠️ Consideraciones de Seguridad

### ✅ Recomendaciones

1. **Red Aislada**: Aunque tiene red, está en `brain-network` interno
2. **Sin Privilegios**: No usa `--privileged`
3. **Límites de Recursos**: Configurar CPU y memoria limits
4. **Validación**: El LLM genera código, validar antes de producción
5. **Secrets**: No hardcodear credenciales, usar env vars

### 🔒 Variables de Entorno Disponibles

El contenedor tiene acceso a:
- `DATABASE_URL` - PostgreSQL del sistema
- `REDIS_URL` - Redis del sistema
- `API_URL` - API de Brain
- `WORKSPACE` - Path al workspace

---

## 🔄 Próximos Pasos / Mejoras Futuras

1. **Scheduler Integrado**: Añadir APScheduler dentro del contenedor
2. **API de Gestión**: Endpoints para listar/ejecutar/eliminar scripts
3. **Notificaciones**: Webhook/Email cuando se detectan cambios
4. **Dashboard**: GUI para ver scripts guardados y logs
5. **Cron Jobs**: Integración con cron del sistema
6. **Multi-Language**: Soporte para Node.js también

---

## 📝 Changelog

### v1.0.0 (2026-01-23)
- ✅ Implementación inicial
- ✅ Contenedor persistente con volumen
- ✅ Executor con métodos de gestión de archivos
- ✅ Agente completo con prompts especializados
- ✅ Documentación completa

---

**Autor**: Brain Development Team  
**Fecha**: 23 Enero 2026  
**Versión**: 1.0.0  
**Estado**: ✅ Listo para testing
