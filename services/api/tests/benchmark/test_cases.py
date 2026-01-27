"""
Definición de casos de prueba para el Benchmark de Brain 2.0 Core Tools
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Any


class TestCategory(Enum):
    """Categorías de pruebas"""
    MULTI_TOOL = "multi_tool"
    REASONING = "reasoning"
    CODE_EXECUTION = "code_execution"
    ERROR_HANDLING = "error_handling"
    INTEGRATION = "integration"


class ExpectedComplexity(Enum):
    """Complejidad esperada de la tarea"""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class TestCase:
    """Definición de un caso de prueba"""
    id: str
    name: str
    description: str
    query: str
    category: TestCategory
    expected_tools: List[str]  # Tools que deberían usarse
    expected_complexity: ExpectedComplexity
    timeout_seconds: int = 120
    # Validación personalizada
    validate_response: Optional[Callable[[dict], bool]] = None
    validate_output: Optional[Callable[[str], bool]] = None
    # Configuración adicional
    setup_query: Optional[str] = None  # Query para preparar el test
    cleanup_query: Optional[str] = None  # Query para limpiar después
    tags: List[str] = field(default_factory=list)
    # Expectativas
    expect_error: bool = False
    min_iterations: int = 1
    max_iterations: int = 10


# =============================================================================
# 1. MULTI-TOOL WORKFLOW TESTS
# =============================================================================

MULTI_TOOL_TESTS = [
    TestCase(
        id="mt_1_research_save",
        name="Research & Save",
        description="Buscar información en web y guardar resumen en archivo",
        query="Busca información sobre Docker Compose en internet, resume los 3 puntos más importantes y guárdalo en /workspace/docker_summary.txt",
        category=TestCategory.MULTI_TOOL,
        expected_tools=["web_search", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=60,
        validate_output=lambda r: "docker" in r.lower() or "compose" in r.lower(),
        tags=["web", "file", "summary"],
    ),
    TestCase(
        id="mt_2_code_analysis",
        name="Code Analysis",
        description="Leer código, analizarlo y hacer cálculos",
        query="Lee el archivo /app/src/main.py, cuenta cuántas funciones 'def' tiene y calcula cuántas líneas tiene el archivo en total",
        category=TestCategory.MULTI_TOOL,
        expected_tools=["read", "calculate"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        tags=["read", "analyze", "calculate"],
    ),
    TestCase(
        id="mt_3_file_operations",
        name="File Operations Chain",
        description="Crear, leer, editar y verificar archivo",
        query="Crea un archivo /workspace/test_chain.txt con el texto 'Hello World', luego edítalo cambiando 'World' por 'Brain 2.0', y finalmente lee el archivo para confirmar el cambio",
        category=TestCategory.MULTI_TOOL,
        expected_tools=["write", "edit", "read"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=45,
        validate_output=lambda r: "brain 2.0" in r.lower() or "hello brain" in r.lower(),
        cleanup_query="Elimina el archivo /workspace/test_chain.txt usando shell: rm /workspace/test_chain.txt",
        tags=["write", "edit", "read", "chain"],
    ),
    TestCase(
        id="mt_4_search_report",
        name="Search & Report",
        description="Buscar en código y generar reporte",
        query="Busca todos los archivos que contengan 'router' en /app/src, cuenta cuántos hay y crea un archivo /workspace/router_report.txt con la lista",
        category=TestCategory.MULTI_TOOL,
        expected_tools=["search", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=45,
        tags=["search", "report", "write"],
    ),
    TestCase(
        id="mt_5_list_and_process",
        name="List & Process Files",
        description="Listar directorio y procesar información",
        query="Lista los archivos en /app/src/tools/core/, cuenta cuántos archivos .py hay y calcula el total de caracteres en los nombres de los archivos",
        category=TestCategory.MULTI_TOOL,
        expected_tools=["list", "calculate"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        tags=["list", "calculate", "process"],
    ),
]


# =============================================================================
# 2. REASONING CHAIN TESTS
# =============================================================================

REASONING_TESTS = [
    TestCase(
        id="rc_1_math_problem",
        name="Math Problem Solving",
        description="Resolver problema matemático con razonamiento",
        query="Un tren sale de Madrid a las 8:00 a 60km/h hacia Barcelona (620km). Otro tren sale de Barcelona a las 9:00 hacia Madrid a 80km/h. ¿A qué distancia de Madrid se cruzan? Usa plan para estructurar el problema y calculate para los cálculos",
        category=TestCategory.REASONING,
        expected_tools=["plan", "calculate"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=90,
        tags=["math", "reasoning", "plan"],
    ),
    TestCase(
        id="rc_2_code_review",
        name="Code Review & Analysis",
        description="Analizar código y proponer mejoras",
        query="Lee el archivo /app/src/tools/core/filesystem.py, analiza el código y usa reflect para evaluar si tiene buenas prácticas de manejo de errores. Resume tus conclusiones",
        category=TestCategory.REASONING,
        expected_tools=["read", "reflect"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=60,
        tags=["code", "review", "reflect"],
    ),
    TestCase(
        id="rc_3_decision_making",
        name="Decision Making",
        description="Investigar y tomar decisión con justificación",
        query="Necesito elegir entre SQLite y PostgreSQL para una aplicación con 1000 usuarios concurrentes. Usa think para analizar pros y contras, y da una recomendación justificada",
        category=TestCategory.REASONING,
        expected_tools=["think"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=45,
        tags=["decision", "think", "analysis"],
    ),
    TestCase(
        id="rc_4_planning_task",
        name="Task Planning",
        description="Crear plan detallado para tarea compleja",
        query="Usa plan para crear un plan de 5 pasos para migrar una aplicación de Flask a FastAPI, incluyendo qué archivos modificar y en qué orden",
        category=TestCategory.REASONING,
        expected_tools=["plan"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=60,
        tags=["plan", "migration", "steps"],
    ),
    TestCase(
        id="rc_5_reflection_chain",
        name="Multi-step Reflection",
        description="Reflexionar sobre proceso y mejorar",
        query="Primero usa think para proponer cómo optimizar un bucle que procesa 1 millón de elementos, luego usa reflect para evaluar si tu propuesta es correcta y mejorarla si es necesario",
        category=TestCategory.REASONING,
        expected_tools=["think", "reflect"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=60,
        tags=["think", "reflect", "optimize"],
    ),
]


# =============================================================================
# 3. CODE EXECUTION TESTS
# =============================================================================

CODE_EXECUTION_TESTS = [
    TestCase(
        id="ce_1_python_fibonacci",
        name="Python Fibonacci",
        description="Generar y ejecutar código Python",
        query="Escribe y ejecuta código Python que genere los primeros 15 números de Fibonacci y los imprima como lista",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["python"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=60,
        validate_output=lambda r: "1" in r and "89" in r,  # Fib(11)=89
        tags=["python", "fibonacci", "execute"],
    ),
    TestCase(
        id="ce_2_javascript_sort",
        name="JavaScript Object Sort",
        description="Ejecutar JavaScript con manipulación de datos",
        query="Ejecuta JavaScript que cree un array de 5 objetos con nombre y edad, los ordene por edad descendente, y muestre el resultado",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["javascript"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=60,
        tags=["javascript", "sort", "objects"],
    ),
    TestCase(
        id="ce_3_shell_pipeline",
        name="Shell Commands Pipeline",
        description="Ejecutar múltiples comandos shell",
        query="Usa shell para: 1) crear directorio /workspace/bench_test, 2) crear un archivo info.txt dentro con la fecha actual, 3) mostrar el contenido del archivo",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["shell"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        cleanup_query="Usa shell para eliminar /workspace/bench_test: rm -rf /workspace/bench_test",
        tags=["shell", "directory", "file"],
    ),
    TestCase(
        id="ce_4_python_json_processing",
        name="Python JSON Processing",
        description="Generar datos JSON y procesarlos",
        query="Ejecuta Python para: 1) crear un diccionario con 5 productos (nombre, precio), 2) calcular el precio total, 3) encontrar el producto más caro, 4) imprimir todo en formato JSON",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["python"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=60,
        validate_output=lambda r: "precio" in r.lower() or "price" in r.lower() or "{" in r,
        tags=["python", "json", "processing"],
    ),
    TestCase(
        id="ce_5_multi_language",
        name="Multi-language Execution",
        description="Ejecutar código en Python y JavaScript",
        query="Calcula el factorial de 10 usando Python, luego verifica el resultado ejecutando el mismo cálculo en JavaScript",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["python", "javascript"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=90,
        validate_output=lambda r: "3628800" in r,  # 10! = 3628800
        tags=["python", "javascript", "factorial", "verify"],
    ),
    TestCase(
        id="ce_6_code_and_save",
        name="Generate, Execute & Save",
        description="Generar código, ejecutarlo y guardar resultado",
        query="Ejecuta Python para generar una lista de los primeros 10 números primos, luego guarda el resultado en /workspace/primes.txt",
        category=TestCategory.CODE_EXECUTION,
        expected_tools=["python", "write"],
        expected_complexity=ExpectedComplexity.MODERATE,
        timeout_seconds=60,
        cleanup_query="Elimina /workspace/primes.txt",
        tags=["python", "primes", "write"],
    ),
]


# =============================================================================
# 4. ERROR HANDLING TESTS
# =============================================================================

ERROR_HANDLING_TESTS = [
    TestCase(
        id="eh_1_file_not_found",
        name="File Not Found",
        description="Manejar archivo inexistente gracefully",
        query="Lee el archivo /workspace/archivo_que_no_existe_xyz.txt",
        category=TestCategory.ERROR_HANDLING,
        expected_tools=["read"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        expect_error=False,  # Debe manejar el error, no fallar
        validate_output=lambda r: "no" in r.lower() or "error" in r.lower() or "existe" in r.lower() or "found" in r.lower(),
        tags=["error", "file", "graceful"],
    ),
    TestCase(
        id="eh_2_division_zero",
        name="Division by Zero",
        description="Manejar división por cero",
        query="Usa calculate para dividir 100 entre 0",
        category=TestCategory.ERROR_HANDLING,
        expected_tools=["calculate"],
        expected_complexity=ExpectedComplexity.TRIVIAL,
        timeout_seconds=30,
        expect_error=False,
        validate_output=lambda r: "error" in r.lower() or "infinit" in r.lower() or "division" in r.lower() or "cero" in r.lower(),
        tags=["error", "math", "division"],
    ),
    TestCase(
        id="eh_3_invalid_python",
        name="Invalid Python Syntax",
        description="Manejar error de sintaxis Python",
        query="Ejecuta este código Python con error de sintaxis: print('hello'",
        category=TestCategory.ERROR_HANDLING,
        expected_tools=["python"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        expect_error=False,
        validate_output=lambda r: "error" in r.lower() or "syntax" in r.lower(),
        tags=["error", "python", "syntax"],
    ),
    TestCase(
        id="eh_4_empty_search",
        name="Empty Search Results",
        description="Manejar búsqueda sin resultados",
        query="Busca archivos que contengan 'xyznotexistingpattern123456' en /app/src",
        category=TestCategory.ERROR_HANDLING,
        expected_tools=["search"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=30,
        expect_error=False,
        validate_output=lambda r: "no" in r.lower() or "0" in r or "ningún" in r.lower() or "encontr" in r.lower(),
        tags=["error", "search", "empty"],
    ),
    TestCase(
        id="eh_5_invalid_url",
        name="Invalid URL Fetch",
        description="Manejar URL inválida o timeout",
        query="Usa web_fetch para obtener el contenido de https://dominio-que-no-existe-xyz123.com/page",
        category=TestCategory.ERROR_HANDLING,
        expected_tools=["web_fetch"],
        expected_complexity=ExpectedComplexity.SIMPLE,
        timeout_seconds=45,
        expect_error=False,
        validate_output=lambda r: "error" in r.lower() or "no" in r.lower() or "failed" in r.lower(),
        tags=["error", "web", "fetch"],
    ),
]


# =============================================================================
# 5. INTEGRATION TESTS (Complex End-to-End)
# =============================================================================

INTEGRATION_TESTS = [
    TestCase(
        id="int_1_research_document",
        name="Full Research Task",
        description="Investigar, analizar y documentar",
        query="Investiga qué es FastAPI buscando en internet, luego lee /app/src/main.py para ver cómo se usa en este proyecto, y crea un documento /workspace/fastapi_analysis.txt con: 1) Qué es FastAPI (del web search), 2) Cómo se usa en este proyecto (del código)",
        category=TestCategory.INTEGRATION,
        expected_tools=["web_search", "read", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        cleanup_query="Elimina /workspace/fastapi_analysis.txt",
        tags=["research", "integration", "document"],
    ),
    TestCase(
        id="int_2_codebase_stats",
        name="Codebase Statistics",
        description="Analizar codebase y generar estadísticas",
        query="Lista los archivos en /app/src/tools/core/, lee cada archivo .py, cuenta las líneas de cada uno, y genera un reporte con las estadísticas (nombre archivo, líneas, total)",
        category=TestCategory.INTEGRATION,
        expected_tools=["list", "read", "calculate", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        tags=["stats", "codebase", "analysis"],
    ),
    TestCase(
        id="int_3_data_pipeline",
        name="Data Pipeline",
        description="Generar, procesar y guardar datos",
        query="1) Ejecuta Python para generar una lista de 10 números aleatorios entre 1-100, 2) Guárdala en /workspace/numbers.json, 3) Lee el archivo, 4) Calcula la media y el máximo, 5) Añade los resultados al archivo",
        category=TestCategory.INTEGRATION,
        expected_tools=["python", "write", "read", "calculate"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        cleanup_query="Elimina /workspace/numbers.json",
        tags=["pipeline", "data", "processing"],
    ),
    TestCase(
        id="int_4_automated_test",
        name="Automated Code Test",
        description="Leer código, generar test, ejecutar",
        query="Lee la función en /app/src/tools/core/utils.py, identifica la función 'calculate', genera un test simple en Python que la pruebe con sqrt(16) y 2+2, y ejecútalo",
        category=TestCategory.INTEGRATION,
        expected_tools=["read", "python"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=90,
        tags=["test", "code", "automated"],
    ),
    TestCase(
        id="int_5_full_workflow",
        name="Full Development Workflow",
        description="Workflow completo de desarrollo",
        query="Simula un workflow de desarrollo: 1) Usa plan para diseñar una función que calcule el área de un círculo, 2) Escribe el código Python, 3) Ejecútalo con radio=5, 4) Guarda el código y resultado en /workspace/circle_area.py",
        category=TestCategory.INTEGRATION,
        expected_tools=["plan", "python", "write"],
        expected_complexity=ExpectedComplexity.COMPLEX,
        timeout_seconds=120,
        validate_output=lambda r: "78" in r or "3.14" in r,  # π*5² ≈ 78.54
        cleanup_query="Elimina /workspace/circle_area.py",
        tags=["workflow", "development", "full"],
    ),
]


# =============================================================================
# ALL TESTS COMBINED
# =============================================================================

ALL_TESTS = (
    MULTI_TOOL_TESTS +
    REASONING_TESTS +
    CODE_EXECUTION_TESTS +
    ERROR_HANDLING_TESTS +
    INTEGRATION_TESTS
)


def get_tests_by_category(category: TestCategory) -> List[TestCase]:
    """Obtener tests por categoría"""
    return [t for t in ALL_TESTS if t.category == category]


def get_tests_by_tag(tag: str) -> List[TestCase]:
    """Obtener tests por tag"""
    return [t for t in ALL_TESTS if tag in t.tags]


def get_test_by_id(test_id: str) -> Optional[TestCase]:
    """Obtener test por ID"""
    for test in ALL_TESTS:
        if test.id == test_id:
            return test
    return None
