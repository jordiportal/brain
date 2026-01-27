"""
Brain 2.0 Advanced Benchmark - Test Cases Avanzados

Este módulo contiene tests más complejos y realistas para evaluar
las capacidades del agente en tareas de desarrollo profesional.

Categorías:
- Shell & System Admin: Instalación de paquetes, configuración de sistema
- Agentic Coding: Debugging, refactoring, feature development
- Database Operations: Queries, migraciones, optimización
- API Development: Endpoints, auth, validación
- DevOps: Docker, CI/CD, monitoring
- Security: Vulnerabilidades, auditoría
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable
from .test_cases import TestCase, TestCategory, ExpectedComplexity


# =============================================================================
# NUEVAS CATEGORÍAS AVANZADAS
# =============================================================================

class AdvancedTestCategory(Enum):
    """Categorías de tests avanzados"""
    SHELL_ADMIN = "shell_admin"
    AGENTIC_CODING = "agentic_coding"
    DATABASE_OPS = "database_ops"
    API_DEVELOPMENT = "api_development"
    DEVOPS = "devops"
    SECURITY = "security"
    DATA_PROCESSING = "data_processing"
    CODE_QUALITY = "code_quality"


# =============================================================================
# 1. SHELL & SYSTEM ADMINISTRATION
# =============================================================================

SHELL_ADMIN_TESTS = [
    TestCase(
        id="sh_1_install_package",
        name="Install System Package",
        description="Instalar paquete del sistema y verificar",
        query="""Instala el paquete 'curl' usando el gestor de paquetes del sistema (apt-get o apk).
        Luego verifica que está instalado ejecutando 'curl --version'.
        Guarda el resultado de la versión en /workspace/curl_version.txt""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=120,
        tags=["shell", "install", "package", "advanced"],
    ),
    TestCase(
        id="sh_2_python_venv",
        name="Create Python Virtual Environment",
        description="Crear entorno virtual e instalar dependencias",
        query="""1. Crea un entorno virtual Python en /workspace/test_venv
        2. Actívalo e instala los paquetes: requests, beautifulsoup4
        3. Lista los paquetes instalados con pip freeze
        4. Guarda la lista en /workspace/requirements_installed.txt""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=180,
        tags=["shell", "python", "venv", "pip", "advanced"],
    ),
    TestCase(
        id="sh_3_system_info",
        name="System Information Report",
        description="Recopilar información del sistema",
        query="""Genera un reporte completo del sistema que incluya:
        1. Información del OS (uname -a)
        2. Uso de memoria (free -h o similar)
        3. Uso de disco (df -h)
        4. Procesos más pesados (top/ps)
        5. Variables de entorno relevantes
        
        Guarda el reporte en formato JSON en /workspace/system_report.json""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "python", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["shell", "system", "monitoring", "advanced"],
    ),
    TestCase(
        id="sh_4_docker_status",
        name="Docker Environment Check",
        description="Verificar estado de Docker",
        query="""Verifica el estado del entorno Docker:
        1. Lista todos los contenedores (corriendo y parados)
        2. Lista todas las imágenes
        3. Lista los volúmenes
        4. Lista las redes
        5. Genera un resumen con el conteo de cada recurso
        
        Guarda el resumen en /workspace/docker_status.json""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "python", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=90,
        tags=["shell", "docker", "status", "advanced"],
    ),
    TestCase(
        id="sh_5_file_operations",
        name="Batch File Operations",
        description="Operaciones masivas con archivos",
        query="""1. Crea el directorio /workspace/batch_test con 3 subdirectorios: logs, data, config
        2. Genera 5 archivos .log en logs/ con timestamps diferentes
        3. Genera 3 archivos .json en data/ con datos de ejemplo
        4. Crea un archivo config.yaml en config/ con configuración básica
        5. Lista recursivamente toda la estructura creada
        6. Comprime todo en /workspace/batch_test.tar.gz""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["shell", "files", "batch", "advanced"],
    ),
    TestCase(
        id="sh_6_network_check",
        name="Network Connectivity Test",
        description="Verificar conectividad de red",
        query="""Realiza un diagnóstico de conectividad de red:
        1. Verifica conexión a internet (ping a 8.8.8.8)
        2. Resuelve DNS de google.com
        3. Lista puertos en uso (netstat o ss)
        4. Verifica conectividad HTTP a https://httpbin.org/get
        
        Genera un reporte de estado en /workspace/network_report.txt""",
        category=TestCategory.INTEGRATION,
        expected_tools=["shell", "web_fetch", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=90,
        tags=["shell", "network", "diagnostic", "advanced"],
    ),
    TestCase(
        id="sh_7_log_analysis",
        name="Log File Analysis",
        description="Analizar archivos de log",
        query="""1. Primero genera un archivo de log simulado en /workspace/app.log con 50 líneas
           que incluyan: timestamps, niveles (INFO, WARNING, ERROR), y mensajes variados
        2. Analiza el log y cuenta ocurrencias por nivel
        3. Extrae todas las líneas de ERROR
        4. Encuentra los patrones más frecuentes
        5. Genera un resumen en /workspace/log_analysis.json""",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "shell", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["shell", "logs", "analysis", "advanced"],
    ),
    TestCase(
        id="sh_8_scheduled_task",
        name="Create Scheduled Script",
        description="Crear script con programación",
        query="""Crea un sistema de backup automatizado:
        1. Escribe un script /workspace/backup.sh que:
           - Cree un directorio con timestamp
           - Copie archivos .txt de /workspace/ a ese directorio
           - Genere un manifest.json con lista de archivos copiados
        2. Haz el script ejecutable
        3. Ejecútalo una vez para probar
        4. Verifica que el backup se creó correctamente""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "shell"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["shell", "backup", "script", "advanced"],
    ),
]


# =============================================================================
# 2. AGENTIC CODING
# =============================================================================

AGENTIC_CODING_TESTS = [
    TestCase(
        id="ac_1_bug_fix",
        name="Debug and Fix Bug",
        description="Identificar y corregir bug en código",
        query="""El siguiente código tiene un bug. Créalo en /workspace/buggy.py, identifica el error, corrígelo, y verifica:

```python
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

# Este código falla con lista vacía
result = calculate_average([])
print(f"Average: {result}")
```

1. Crea el archivo con el código buggy
2. Ejecuta para ver el error
3. Analiza y corrige el bug
4. Ejecuta de nuevo para verificar que funciona
5. Explica qué causaba el error""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "edit", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["coding", "debug", "fix", "advanced"],
    ),
    TestCase(
        id="ac_2_refactor",
        name="Refactor Function",
        description="Refactorizar código para mejorar calidad",
        query="""Refactoriza este código para hacerlo más limpio y eficiente. Créalo en /workspace/refactor_me.py:

```python
def process_data(d):
    r = []
    for i in range(len(d)):
        if d[i] > 0:
            if d[i] % 2 == 0:
                r.append(d[i] * 2)
            else:
                r.append(d[i] * 3)
    return r
```

1. Crea el archivo original
2. Analiza problemas del código (nombres, estilo, eficiencia)
3. Refactoriza usando buenas prácticas Python
4. Añade type hints y docstring
5. Guarda versión mejorada en /workspace/refactored.py
6. Verifica que produce el mismo resultado""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["coding", "refactor", "quality", "advanced"],
    ),
    TestCase(
        id="ac_3_add_feature",
        name="Add Feature to Existing Code",
        description="Añadir funcionalidad a código existente",
        query="""Crea una clase User básica y añádele funcionalidad:

1. Crea /workspace/user.py con clase User(name, email)
2. Añade validación de email (debe contener @ y .)
3. Añade método to_dict() que retorne diccionario
4. Añade método from_dict(data) como classmethod
5. Añade método __repr__ para debugging
6. Crea tests básicos que verifiquen toda la funcionalidad
7. Ejecuta los tests para verificar""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["coding", "feature", "oop", "advanced"],
    ),
    TestCase(
        id="ac_4_write_tests",
        name="Generate Unit Tests",
        description="Generar tests unitarios para código",
        query="""Crea una calculadora y genera tests completos:

1. Crea /workspace/calculator.py con clase Calculator:
   - add(a, b)
   - subtract(a, b)  
   - multiply(a, b)
   - divide(a, b) - debe manejar división por cero
   
2. Crea /workspace/test_calculator.py con tests usando unittest:
   - Tests para cada operación
   - Tests de edge cases (números negativos, cero, floats)
   - Test de división por cero
   
3. Ejecuta los tests y verifica que pasan""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["coding", "testing", "unittest", "advanced"],
    ),
    TestCase(
        id="ac_5_api_endpoint",
        name="Create REST Endpoint",
        description="Crear endpoint REST completo",
        query="""Crea un mini-servidor API REST:

1. Crea /workspace/api_server.py con un servidor usando http.server:
   - GET /health -> {"status": "ok"}
   - GET /info -> {"version": "1.0", "name": "test-api"}
   - POST /echo -> devuelve el body recibido
   
2. Crea /workspace/test_api.py que:
   - Inicie el servidor en background
   - Pruebe cada endpoint
   - Verifique las respuestas
   - Pare el servidor
   
3. Ejecuta los tests""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "shell", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=180,
        tags=["coding", "api", "rest", "advanced"],
    ),
]


# =============================================================================
# 3. DATABASE OPERATIONS
# =============================================================================

DATABASE_OPS_TESTS = [
    TestCase(
        id="db_1_sqlite_crud",
        name="SQLite CRUD Operations",
        description="Operaciones CRUD con SQLite",
        query="""Crea una aplicación de gestión de tareas con SQLite:

1. Crea /workspace/todo_db.py que:
   - Cree BD SQLite en /workspace/todos.db
   - Cree tabla: tasks(id INTEGER PRIMARY KEY, title TEXT, done BOOLEAN, created_at TIMESTAMP)
   - Implemente funciones: add_task, get_tasks, mark_done, delete_task
   
2. Inserta 5 tareas de ejemplo
3. Marca 2 como completadas
4. Lista todas las tareas
5. Genera reporte en /workspace/tasks_report.json""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["database", "sqlite", "crud", "advanced"],
    ),
    TestCase(
        id="db_2_data_migration",
        name="Data Format Migration",
        description="Migrar datos entre formatos",
        query="""Realiza una migración de datos:

1. Crea /workspace/users.csv con 10 usuarios (id, name, email, age, city)
2. Crea script que:
   - Lea el CSV
   - Valide los datos (email válido, age > 0)
   - Transforme a JSON con estructura diferente: {users: [{...}], metadata: {count, generated_at}}
   - Guarde en /workspace/users_migrated.json
3. Verifica que la migración preservó todos los datos""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["database", "migration", "etl", "advanced"],
    ),
    TestCase(
        id="db_3_query_builder",
        name="Dynamic Query Builder",
        description="Construir queries dinámicamente",
        query="""Crea un query builder simple:

1. Crea /workspace/query_builder.py con clase QueryBuilder:
   - select(*columns)
   - from_table(table)
   - where(condition)
   - order_by(column, direction)
   - limit(n)
   - build() -> retorna string SQL
   
2. Debe soportar encadenamiento: QueryBuilder().select("*").from_table("users").where("age > 18").build()

3. Crea tests que verifiquen diferentes combinaciones
4. Ejecuta los tests""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["database", "sql", "builder", "advanced"],
    ),
    TestCase(
        id="db_4_json_db",
        name="JSON File Database",
        description="Implementar BD basada en JSON",
        query="""Implementa una mini base de datos JSON:

1. Crea /workspace/jsondb.py con clase JsonDB:
   - __init__(filepath): crea/carga archivo JSON
   - insert(collection, document): añade documento con ID auto
   - find(collection, query): busca documentos que coincidan
   - update(collection, id, data): actualiza documento
   - delete(collection, id): elimina documento
   - save(): persiste cambios
   
2. Crea tests que:
   - Creen BD en /workspace/test.jsondb
   - Inserten 5 productos
   - Busquen por precio > 100
   - Actualicen uno
   - Eliminen uno
   - Verifiquen persistencia

3. Ejecuta los tests""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["database", "json", "nosql", "advanced"],
    ),
]


# =============================================================================
# 4. DATA PROCESSING
# =============================================================================

DATA_PROCESSING_TESTS = [
    TestCase(
        id="dp_1_csv_analysis",
        name="CSV Data Analysis",
        description="Analizar datos CSV",
        query="""Genera y analiza un dataset de ventas:

1. Crea /workspace/sales.csv con 100 registros:
   - date, product, category, quantity, price, region
   - Datos realistas y variados
   
2. Analiza los datos:
   - Total de ventas por categoría
   - Producto más vendido
   - Región con más ingresos
   - Tendencia por mes
   
3. Guarda análisis en /workspace/sales_analysis.json
4. Genera resumen en /workspace/sales_summary.txt""",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["data", "csv", "analysis", "advanced"],
    ),
    TestCase(
        id="dp_2_json_transform",
        name="JSON Data Transformation",
        description="Transformar estructura JSON compleja",
        query="""Transforma datos JSON anidados:

1. Crea /workspace/nested_data.json con estructura:
   {
     "company": "Tech Corp",
     "departments": [
       {"name": "Engineering", "employees": [{"name": "...", "salary": ...}]},
       {"name": "Sales", "employees": [...]}
     ]
   }
   Con al menos 3 departamentos y 5 empleados cada uno.

2. Transforma a estructura plana:
   - Lista de empleados con department_name incluido
   - Calcula total de salarios por departamento
   - Encuentra el empleado mejor pagado
   
3. Guarda en /workspace/flat_employees.json""",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["data", "json", "transform", "advanced"],
    ),
    TestCase(
        id="dp_3_text_processing",
        name="Text File Processing",
        description="Procesar y analizar texto",
        query="""Procesa un archivo de texto:

1. Crea /workspace/article.txt con un artículo de ~500 palabras sobre tecnología

2. Analiza el texto:
   - Cuenta palabras totales
   - Cuenta palabras únicas
   - Encuentra las 10 palabras más frecuentes (ignorando stopwords comunes)
   - Cuenta oraciones
   - Calcula longitud promedio de oraciones
   
3. Guarda estadísticas en /workspace/text_stats.json
4. Genera un resumen del artículo en /workspace/article_summary.txt""",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "write", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["data", "text", "nlp", "advanced"],
    ),
    TestCase(
        id="dp_4_data_validation",
        name="Data Validation Pipeline",
        description="Pipeline de validación de datos",
        query="""Crea un pipeline de validación de datos:

1. Crea /workspace/raw_users.json con 20 usuarios:
   - Incluye datos válidos e inválidos
   - Emails mal formados, edades negativas, nombres vacíos
   
2. Crea /workspace/validator.py con:
   - Validadores para cada campo
   - Función que procese todos los registros
   - Separe válidos de inválidos
   - Genere reporte de errores
   
3. Ejecuta y genera:
   - /workspace/valid_users.json
   - /workspace/invalid_users.json  
   - /workspace/validation_report.json con estadísticas""",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "write", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["data", "validation", "pipeline", "advanced"],
    ),
]


# =============================================================================
# 5. CODE QUALITY
# =============================================================================

CODE_QUALITY_TESTS = [
    TestCase(
        id="cq_1_documentation",
        name="Generate Documentation",
        description="Generar documentación de código",
        query="""Genera documentación para código existente:

1. Crea /workspace/utils.py con 5 funciones útiles:
   - format_date(date, format)
   - validate_email(email)
   - slugify(text)
   - truncate(text, length)
   - deep_merge(dict1, dict2)
   
2. Para cada función añade:
   - Docstring completo con descripción, args, returns, raises, examples
   - Type hints
   
3. Genera /workspace/utils_docs.md con documentación en formato Markdown:
   - Descripción del módulo
   - Lista de funciones con firma y descripción
   - Ejemplos de uso""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["quality", "documentation", "docstring", "advanced"],
    ),
    TestCase(
        id="cq_2_error_handling",
        name="Implement Error Handling",
        description="Añadir manejo de errores robusto",
        query="""Mejora el manejo de errores de este código. Créalo en /workspace/file_processor.py:

```python
def process_file(filepath):
    f = open(filepath)
    data = f.read()
    result = json.loads(data)
    return result['items']
```

1. Crea el archivo con el código original
2. Mejóralo con:
   - Context managers (with)
   - Try/except específicos para cada error posible
   - Logging de errores
   - Excepciones personalizadas
   - Retorno de errores estructurado
   
3. Crea tests que verifiquen el manejo de:
   - Archivo no existe
   - JSON inválido
   - Key 'items' no existe
   
4. Guarda versión mejorada en /workspace/file_processor_safe.py""",
        category=TestCategory.INTEGRATION,
        expected_tools=["write", "python", "think"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=150,
        tags=["quality", "errors", "exceptions", "advanced"],
    ),
]


# =============================================================================
# COMBINAR TODOS LOS TESTS AVANZADOS
# =============================================================================

ADVANCED_TESTS = (
    SHELL_ADMIN_TESTS +
    AGENTIC_CODING_TESTS +
    DATABASE_OPS_TESTS +
    DATA_PROCESSING_TESTS +
    CODE_QUALITY_TESTS
)


def get_advanced_tests_by_category(category_prefix: str) -> list:
    """Obtener tests avanzados por prefijo de categoría"""
    return [t for t in ADVANCED_TESTS if t.id.startswith(category_prefix)]


def get_all_advanced_test_ids() -> list:
    """Obtener IDs de todos los tests avanzados"""
    return [t.id for t in ADVANCED_TESTS]
