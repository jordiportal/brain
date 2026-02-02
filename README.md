# Brain - Sistema de Gestión de Cadenas de Pensamiento con IA

Brain es una plataforma para diseñar, ejecutar y monitorizar flujos de procesamiento con IA utilizando LangChain y LangGraph. Proporciona una interfaz visual para gestionar conexiones con LLMs, configurar cadenas de pensamiento y visualizar ejecuciones en tiempo real.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                          │
├─────────────┬─────────────┬──────────────┬───────────┬─────────┤
│   Angular   │   FastAPI   │  PostgreSQL  │   Redis   │ Browser │
│    GUI      │    API      │  + pgvector  │   Cache   │ Service │
│   :4200     │   :8000     │    :5432     │   :6379   │  :6080  │
└──────┬──────┴──────┬──────┴──────┬───────┴─────┬─────┴────┬────┘
       │             │             │             │          │
       └─────────────┴─────────────┴─────────────┴──────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Servicios LLM    │
                    │  (Ollama, OpenAI, │
                    │   Gemini, etc.)   │
                    └───────────────────┘
```

## Características

- **Gestión de LLMs**: Configura múltiples proveedores (Ollama, OpenAI, Gemini, Anthropic, Azure, Groq)
- **Conexiones MCP**: Integración con servidores Model Context Protocol
- **Cadenas de Pensamiento**: Define y visualiza flujos con LangGraph
- **RAG**: Base de datos vectorial con pgvector para Retrieval Augmented Generation
- **Testing en Tiempo Real**: Chat con streaming y renderizado Markdown
- **Ejecución de Código**: Contenedores aislados para Python y JavaScript
- **Browser Automation**: Navegador Chrome con VNC para automatización web

## Requisitos

- Docker y Docker Compose
- Git
- (Opcional) Ollama u otro servidor LLM

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/jordiportal/brain.git
cd brain
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` según tu configuración:

```env
# Puertos (opcionales, valores por defecto)
API_PORT=8000
GUI_PORT=4200

# PostgreSQL
POSTGRES_USER=brain
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_DB=brain_db

# Ollama (ajusta la IP a tu servidor)
OLLAMA_BASE_URL=http://localhost:11434

# JWT Secret (genera un valor único para producción)
JWT_SECRET=genera-un-secret-seguro
```

### 3. Levantar los servicios

```bash
# Primera vez (construye las imágenes)
docker compose up -d --build

# Siguientes veces
docker compose up -d
```

La primera ejecución tardará unos minutos mientras:
- Se descargan las imágenes base
- Se instalan las dependencias de cada servicio
- Se inicializa la base de datos

## Uso

### URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **GUI** | http://localhost:4200 | Interfaz de usuario principal |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger de la API |
| **Browser VNC** | http://localhost:6080 | Navegador Chrome visual |

### Flujo de Trabajo

1. **Configurar LLM**: Ve a Configuración > Proveedores LLM y añade tu servidor Ollama u otro proveedor
2. **Probar Conexión**: En Testing LLM, verifica que la conexión funciona
3. **Crear Cadenas**: Define tus flujos de procesamiento en la sección Cadenas
4. **Monitorizar**: Revisa las ejecuciones y métricas en Monitorización

## Estructura del Proyecto

```
brain/
├── docker-compose.yml          # Orquestación de servicios
├── .env.example                 # Template de configuración
│
├── services/
│   ├── api/                     # API Python (FastAPI)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── main.py          # Entry point FastAPI
│   │       ├── config.py        # Configuración
│   │       ├── db/              # Acceso a PostgreSQL
│   │       ├── engine/          # Motor de agentes
│   │       ├── tools/           # Herramientas del agente
│   │       ├── rag/             # RAG con pgvector
│   │       └── mcp/             # Integración MCP
│   │
│   ├── gui/                     # Frontend Angular
│   │   ├── Dockerfile
│   │   └── src/app/
│   │       ├── core/            # Servicios, guards, modelos
│   │       ├── features/        # Componentes por funcionalidad
│   │       └── layouts/         # Layout principal
│   │
│   ├── browser-service/         # Chrome + noVNC
│   │
│   └── code-runners/            # Contenedores de ejecución de código
│
└── database/
    └── init/
        ├── 01-init-pgvector.sql # Inicialización PostgreSQL + pgvector
        └── 02-monitoring.sql    # Tablas de monitorización
```

## Comandos Útiles

```bash
# Ver estado de los servicios
docker compose ps

# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f api

# Reiniciar un servicio
docker compose restart api

# Parar todo
docker compose down

# Parar y eliminar volúmenes (reset completo)
docker compose down -v

# Reconstruir un servicio
docker compose build api && docker compose up -d api
```

## Desarrollo

### API Python

Los cambios en `services/api/src/` se recargan automáticamente gracias a uvicorn con `--reload`.

### GUI Angular

Los cambios en `services/gui/src/` se recompilan automáticamente con hot-reload.

## Tecnologías

- **Backend**: Python 3.11, FastAPI, LangChain, LangGraph
- **Frontend**: Angular 17, Angular Material
- **Base de Datos**: PostgreSQL 16 + pgvector (acceso directo)
- **Cache**: Redis 7
- **Contenedores**: Docker, Docker Compose

## Roadmap

- [ ] Editor visual de grafos LangGraph
- [ ] Integración completa con RAG
- [ ] WebSocket para ejecuciones en tiempo real
- [ ] Exportar/Importar configuraciones
- [ ] Métricas y dashboards avanzados
- [ ] Soporte multi-tenant

## Licencia

MIT

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir cambios mayores antes de crear un PR.
