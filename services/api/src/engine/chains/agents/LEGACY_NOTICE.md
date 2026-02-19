# LEGACY: Carpetas de agentes individuales

Las carpetas `sap_analyst/`, `designer/`, `researcher/`, `communication/` y `rag/`
contienen las definiciones originales de agentes (prompts .txt y skills .md).

**Estas carpetas ya NO se usan en runtime.** Toda la configuración de agentes
se carga desde la tabla `agent_definitions` en PostgreSQL.

Las carpetas se mantienen temporalmente solo como fuente para el **seed inicial**
(`seed.py`). La primera vez que el sistema arranca con la tabla vacía, lee los
ficheros de estas carpetas y los inserta en BD.

**Se pueden eliminar de forma segura** una vez que el seed haya ejecutado al menos
una vez (es decir, la tabla `agent_definitions` tenga datos).
