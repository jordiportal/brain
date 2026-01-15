# Brain - Gestión de Cadenas de Pensamiento con IA

Proyecto para la gestión y visualización de flujos de IA utilizando LangChain, LangGraph y un stack moderno.

## Arquitectura

- **API:** Python 3.11 con FastAPI, LangChain y LangGraph.
- **GUI:** Angular 17+ con visualización de grafos (ngx-graph).
- **CMS:** Strapi con PostgreSQL para gestión de contenido y configuraciones.
- **Base de Datos:** PostgreSQL 16 con extensión `pgvector` para RAG.
- **Cache/Queue:** Redis 7.

## Requisitos Previos

- Docker y Docker Compose instalados.
- Ollama corriendo localmente (opcional, para LLM local).

## Inicio Rápido

1. **Configurar el entorno:**
   ```bash
   cp .env.example .env
   ```

2. **Arrancar el stack:**
   ```bash
   docker compose up --build
   ```

3. **Acceder a los servicios:**
   - **GUI (Angular):** [http://localhost:4200](http://localhost:4200)
   - **API (FastAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **CMS (Strapi):** [http://localhost:1337/admin](http://localhost:1337/admin)
   - **PostgreSQL:** `localhost:5432`

## Desarrollo

### Estructura de la API

Los grafos de pensamiento se definen en `services/api/src/graphs/`.
Las cadenas de LangChain se definen en `services/api/src/chains/`.
La lógica de RAG se encuentra en `services/api/src/rag/`.

### Visualización

El GUI utiliza WebSocket para recibir actualizaciones en tiempo real de las ejecuciones de los grafos y renderiza el flujo paso a paso para un fácil seguimiento.

## Notas de Strapi

En la primera ejecución, Strapi se inicializará automáticamente. Deberás crear el primer usuario administrador en la interfaz web.
