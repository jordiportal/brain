"""
Runner del Benchmark para Brain 2.0 Core Tools
"""

import asyncio
import httpx
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .test_cases import (
    TestCase,
    TestCategory,
    ALL_TESTS,
    get_tests_by_category,
    get_test_by_id,
)
from .test_cases_advanced import ADVANCED_TESTS
from .metrics import (
    BenchmarkMetrics,
    TestResult,
    TestStatus,
    create_markdown_report,
)


@dataclass
class RunnerConfig:
    """Configuración del runner"""
    api_url: str = "http://localhost:8000"
    timeout_default: int = 120
    parallel_tests: int = 1  # Tests en paralelo (1 = secuencial)
    retry_on_error: int = 0  # Reintentos en caso de error
    verbose: bool = True
    run_cleanup: bool = True
    categories: Optional[List[TestCategory]] = None  # None = todas
    test_ids: Optional[List[str]] = None  # None = todos
    tags: Optional[List[str]] = None  # Filtrar por tags
    # LLM Provider config
    llm_provider_type: str = "ollama"  # "ollama", "openai", "anthropic", "gemini"
    llm_provider_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    # Benchmark type
    use_advanced: bool = False  # True = usar tests avanzados
    include_basic: bool = True  # True = incluir tests básicos cuando use_advanced=True


class BenchmarkRunner:
    """
    Ejecutor del Benchmark de Brain 2.0
    
    Ejemplo de uso:
        runner = BenchmarkRunner(config=RunnerConfig(api_url="http://localhost:8000"))
        metrics = await runner.run_all()
        metrics.print_summary()
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None):
        self.config = config or RunnerConfig()
        self.metrics = BenchmarkMetrics(api_url=self.config.api_url)
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout_default))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def _get_tests_to_run(self) -> List[TestCase]:
        """Obtener lista de tests a ejecutar según configuración"""
        # Seleccionar conjunto de tests base
        if self.config.use_advanced:
            if self.config.include_basic:
                tests = ALL_TESTS.copy() + ADVANCED_TESTS.copy()
            else:
                tests = ADVANCED_TESTS.copy()
        else:
            tests = ALL_TESTS.copy()
        
        # Filtrar por IDs específicos
        if self.config.test_ids:
            tests = [t for t in tests if t.id in self.config.test_ids]
        
        # Filtrar por categorías
        if self.config.categories:
            tests = [t for t in tests if t.category in self.config.categories]
        
        # Filtrar por tags
        if self.config.tags:
            tests = [t for t in tests if any(tag in t.tags for tag in self.config.tags)]
        
        return tests
    
    async def _invoke_agent(self, query: str, timeout: int) -> Dict[str, Any]:
        """Invocar el adaptive agent"""
        url = f"{self.config.api_url}/api/v1/chains/adaptive/invoke"
        payload = {
            "input": {"query": query}
        }
        
        # Añadir configuración de LLM si está especificada
        if self.config.llm_provider_type != "ollama":
            payload["llm_provider_type"] = self.config.llm_provider_type
        if self.config.llm_provider_url:
            payload["llm_provider_url"] = self.config.llm_provider_url
        if self.config.llm_api_key:
            payload["api_key"] = self.config.llm_api_key
        if self.config.llm_model:
            payload["model"] = self.config.llm_model
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout", "status": "timeout"}
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "status": "error", "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def _evaluate_result(
        self,
        test: TestCase,
        response: Dict[str, Any],
        duration_ms: int
    ) -> TestResult:
        """Evaluar resultado de un test"""
        
        # Extraer datos de la respuesta
        output = response.get("output", {})
        error = response.get("error")
        status_str = response.get("status", "unknown")
        
        # Determinar estado
        if status_str == "timeout":
            status = TestStatus.TIMEOUT
        elif error or status_str == "error":
            status = TestStatus.ERROR
        elif status_str == "completed":
            status = TestStatus.PASSED  # Asumimos passed, validamos después
        else:
            status = TestStatus.FAILED
        
        # Extraer métricas
        tools_used = output.get("tools_used", [])
        iterations = output.get("iterations", 0)
        complexity_detected = output.get("complexity", "unknown")
        response_text = output.get("response", "")
        
        # Validar tools match
        expected_tools_set = set(test.expected_tools)
        used_tools_set = set(tools_used)
        tools_match = expected_tools_set.issubset(used_tools_set) or \
                      len(expected_tools_set.intersection(used_tools_set)) > 0
        
        # Validar complexity match
        complexity_match = complexity_detected.lower() == test.expected_complexity.value.lower()
        
        # Validar output
        output_valid = True
        if test.validate_output and response_text:
            try:
                output_valid = test.validate_output(response_text)
            except Exception:
                output_valid = False
        
        # Validar response
        if test.validate_response:
            try:
                if not test.validate_response(response):
                    status = TestStatus.FAILED
            except Exception:
                status = TestStatus.FAILED
        
        # Si esperamos error y lo obtuvimos, es success
        if test.expect_error and status == TestStatus.ERROR:
            status = TestStatus.PASSED
        
        # Validaciones finales para PASSED
        if status == TestStatus.PASSED:
            # Verificar que usó al menos una tool esperada
            if test.expected_tools and not tools_match:
                status = TestStatus.FAILED
            # Verificar validación de output
            if test.validate_output and not output_valid:
                status = TestStatus.FAILED
            # Verificar iteraciones
            if iterations > test.max_iterations:
                status = TestStatus.FAILED
        
        return TestResult(
            test_id=test.id,
            test_name=test.name,
            category=test.category.value,
            status=status,
            duration_ms=duration_ms,
            iterations=iterations,
            tools_used=tools_used,
            expected_tools=test.expected_tools,
            complexity_detected=complexity_detected,
            expected_complexity=test.expected_complexity.value,
            response=response_text[:500] if response_text else "",
            error=str(error) if error else None,
            tools_match=tools_match,
            complexity_match=complexity_match,
            output_valid=output_valid,
            started_at=None,
            finished_at=None,
        )
    
    async def run_test(self, test: TestCase) -> TestResult:
        """Ejecutar un test individual"""
        if self.config.verbose:
            print(f"  🧪 Running: {test.id} - {test.name}...", end=" ", flush=True)
        
        started_at = datetime.now()
        
        # Ejecutar setup si existe
        if test.setup_query:
            await self._invoke_agent(test.setup_query, 30)
        
        # Ejecutar test principal
        start_time = time.time()
        response = await self._invoke_agent(test.query, test.timeout_seconds)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Evaluar resultado
        result = self._evaluate_result(test, response, duration_ms)
        result.started_at = started_at.isoformat()
        result.finished_at = datetime.now().isoformat()
        
        # Ejecutar cleanup si existe y está habilitado
        if self.config.run_cleanup and test.cleanup_query:
            await self._invoke_agent(test.cleanup_query, 30)
        
        if self.config.verbose:
            status_icon = {
                TestStatus.PASSED: "✅",
                TestStatus.FAILED: "❌",
                TestStatus.ERROR: "⚠️",
                TestStatus.TIMEOUT: "⏱️",
                TestStatus.SKIPPED: "⏭️",
            }.get(result.status, "❓")
            print(f"{status_icon} ({duration_ms}ms, {result.iterations} iters)")
        
        return result
    
    async def run_category(self, category: TestCategory) -> List[TestResult]:
        """Ejecutar todos los tests de una categoría"""
        tests = get_tests_by_category(category)
        results = []
        
        if self.config.verbose:
            print(f"\n📁 Category: {category.value} ({len(tests)} tests)")
            print("-" * 50)
        
        for test in tests:
            result = await self.run_test(test)
            results.append(result)
            self.metrics.add_result(result)
        
        return results
    
    async def run_all(self) -> BenchmarkMetrics:
        """Ejecutar todos los tests configurados"""
        tests = self._get_tests_to_run()
        
        if not tests:
            print("⚠️ No tests to run with current configuration")
            return self.metrics
        
        self.metrics.started_at = datetime.now().isoformat()
        
        if self.config.verbose:
            print("\n" + "=" * 60)
            print("🚀 BRAIN 2.0 BENCHMARK STARTING")
            print(f"   API URL: {self.config.api_url}")
            print(f"   Tests to run: {len(tests)}")
            print("=" * 60)
        
        # Agrupar tests por categoría para mejor organización
        categories_to_run = set(t.category for t in tests)
        
        for category in categories_to_run:
            category_tests = [t for t in tests if t.category == category]
            
            if self.config.verbose:
                print(f"\n📁 Category: {category.value} ({len(category_tests)} tests)")
                print("-" * 50)
            
            for test in category_tests:
                result = await self.run_test(test)
                self.metrics.add_result(result)
        
        self.metrics.finished_at = datetime.now().isoformat()
        
        return self.metrics
    
    async def run_quick(self) -> BenchmarkMetrics:
        """Ejecutar subset rápido de tests (1 por categoría)"""
        # Seleccionar primer test de cada categoría
        tests_to_run = []
        seen_categories = set()
        
        for test in ALL_TESTS:
            if test.category not in seen_categories:
                tests_to_run.append(test)
                seen_categories.add(test.category)
        
        self.config.test_ids = [t.id for t in tests_to_run]
        return await self.run_all()


async def run_benchmark(
    api_url: str = "http://localhost:8000",
    categories: Optional[List[str]] = None,
    test_ids: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    verbose: bool = True,
    output_json: Optional[str] = None,
    output_markdown: Optional[str] = None,
) -> BenchmarkMetrics:
    """
    Función de conveniencia para ejecutar el benchmark
    
    Args:
        api_url: URL de la API de Brain
        categories: Lista de categorías a ejecutar
        test_ids: Lista de IDs de tests específicos
        tags: Lista de tags para filtrar tests
        verbose: Mostrar progreso
        output_json: Ruta para guardar reporte JSON
        output_markdown: Ruta para guardar reporte Markdown
    
    Returns:
        BenchmarkMetrics con todos los resultados
    """
    config = RunnerConfig(
        api_url=api_url,
        verbose=verbose,
        categories=[TestCategory(c) for c in categories] if categories else None,
        test_ids=test_ids,
        tags=tags,
    )
    
    async with BenchmarkRunner(config) as runner:
        metrics = await runner.run_all()
    
    # Guardar reportes
    if output_json:
        metrics.save_report(output_json)
        if verbose:
            print(f"\n📄 JSON report saved to: {output_json}")
    
    if output_markdown:
        md_report = create_markdown_report(metrics)
        with open(output_markdown, "w", encoding="utf-8") as f:
            f.write(md_report)
        if verbose:
            print(f"📝 Markdown report saved to: {output_markdown}")
    
    # Mostrar resumen
    if verbose:
        metrics.print_summary()
    
    return metrics
