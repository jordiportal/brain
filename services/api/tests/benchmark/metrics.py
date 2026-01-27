"""
Métricas y análisis de resultados del Benchmark
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path


class TestStatus(Enum):
    """Estado del test"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Resultado de un test individual"""
    test_id: str
    test_name: str
    category: str
    status: TestStatus
    duration_ms: int
    iterations: int
    tools_used: List[str]
    expected_tools: List[str]
    complexity_detected: str
    expected_complexity: str
    response: str
    error: Optional[str] = None
    
    # Métricas de validación
    tools_match: bool = False
    complexity_match: bool = False
    output_valid: bool = False
    
    # Timestamps
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        result = asdict(self)
        result["status"] = self.status.value
        return result
    
    @property
    def is_success(self) -> bool:
        """Verificar si el test pasó"""
        return self.status == TestStatus.PASSED
    
    @property
    def tools_coverage(self) -> float:
        """Porcentaje de tools esperadas que se usaron"""
        if not self.expected_tools:
            return 1.0
        used = set(self.tools_used)
        expected = set(self.expected_tools)
        if not expected:
            return 1.0
        matched = len(used.intersection(expected))
        return matched / len(expected)


@dataclass
class CategoryMetrics:
    """Métricas agregadas por categoría"""
    category: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    timeouts: int = 0
    skipped: int = 0
    total_duration_ms: int = 0
    avg_duration_ms: float = 0.0
    avg_iterations: float = 0.0
    tools_coverage: float = 0.0
    complexity_accuracy: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Tasa de éxito"""
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            "category": self.category,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "timeouts": self.timeouts,
            "skipped": self.skipped,
            "success_rate": round(self.success_rate * 100, 2),
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "avg_iterations": round(self.avg_iterations, 2),
            "tools_coverage": round(self.tools_coverage * 100, 2),
            "complexity_accuracy": round(self.complexity_accuracy * 100, 2),
        }


@dataclass
class BenchmarkMetrics:
    """Métricas completas del benchmark"""
    results: List[TestResult] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    api_url: str = ""
    
    def add_result(self, result: TestResult):
        """Añadir resultado de test"""
        self.results.append(result)
    
    @property
    def total_tests(self) -> int:
        return len(self.results)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)
    
    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)
    
    @property
    def timeouts(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.TIMEOUT)
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests
    
    @property
    def total_duration_ms(self) -> int:
        return sum(r.duration_ms for r in self.results)
    
    @property
    def avg_duration_ms(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.total_duration_ms / self.total_tests
    
    @property
    def avg_iterations(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return sum(r.iterations for r in self.results) / self.total_tests
    
    @property
    def tools_coverage(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return sum(r.tools_coverage for r in self.results) / self.total_tests
    
    @property
    def complexity_accuracy(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return sum(1 for r in self.results if r.complexity_match) / self.total_tests
    
    def get_category_metrics(self) -> Dict[str, CategoryMetrics]:
        """Obtener métricas por categoría"""
        categories: Dict[str, CategoryMetrics] = {}
        
        for result in self.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = CategoryMetrics(category=cat)
            
            m = categories[cat]
            m.total_tests += 1
            m.total_duration_ms += result.duration_ms
            
            if result.status == TestStatus.PASSED:
                m.passed += 1
            elif result.status == TestStatus.FAILED:
                m.failed += 1
            elif result.status == TestStatus.ERROR:
                m.errors += 1
            elif result.status == TestStatus.TIMEOUT:
                m.timeouts += 1
            elif result.status == TestStatus.SKIPPED:
                m.skipped += 1
        
        # Calcular promedios
        for cat, m in categories.items():
            if m.total_tests > 0:
                cat_results = [r for r in self.results if r.category == cat]
                m.avg_duration_ms = m.total_duration_ms / m.total_tests
                m.avg_iterations = sum(r.iterations for r in cat_results) / m.total_tests
                m.tools_coverage = sum(r.tools_coverage for r in cat_results) / m.total_tests
                m.complexity_accuracy = sum(1 for r in cat_results if r.complexity_match) / m.total_tests
        
        return categories
    
    def get_tools_usage(self) -> Dict[str, int]:
        """Obtener uso de herramientas"""
        usage: Dict[str, int] = {}
        for result in self.results:
            for tool in result.tools_used:
                usage[tool] = usage.get(tool, 0) + 1
        return dict(sorted(usage.items(), key=lambda x: x[1], reverse=True))
    
    def get_failed_tests(self) -> List[TestResult]:
        """Obtener tests fallidos"""
        return [r for r in self.results if r.status != TestStatus.PASSED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario completo"""
        return {
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
                "timeouts": self.timeouts,
                "success_rate": round(self.success_rate * 100, 2),
                "total_duration_ms": self.total_duration_ms,
                "avg_duration_ms": round(self.avg_duration_ms, 2),
                "avg_iterations": round(self.avg_iterations, 2),
                "tools_coverage": round(self.tools_coverage * 100, 2),
                "complexity_accuracy": round(self.complexity_accuracy * 100, 2),
            },
            "by_category": {
                cat: m.to_dict() 
                for cat, m in self.get_category_metrics().items()
            },
            "tools_usage": self.get_tools_usage(),
            "results": [r.to_dict() for r in self.results],
            "metadata": {
                "api_url": self.api_url,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convertir a JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_report(self, output_path: str):
        """Guardar reporte en archivo JSON"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
    
    def print_summary(self):
        """Imprimir resumen en consola"""
        print("\n" + "=" * 70)
        print("📊 BRAIN 2.0 BENCHMARK RESULTS")
        print("=" * 70)
        
        # Resumen general
        print(f"\n🎯 OVERALL SUMMARY")
        print(f"   Total Tests:     {self.total_tests}")
        print(f"   ✅ Passed:       {self.passed}")
        print(f"   ❌ Failed:       {self.failed}")
        print(f"   ⚠️  Errors:       {self.errors}")
        print(f"   ⏱️  Timeouts:     {self.timeouts}")
        print(f"   Success Rate:    {self.success_rate * 100:.1f}%")
        print(f"   Total Duration:  {self.total_duration_ms / 1000:.1f}s")
        print(f"   Avg Duration:    {self.avg_duration_ms / 1000:.2f}s")
        print(f"   Avg Iterations:  {self.avg_iterations:.1f}")
        print(f"   Tools Coverage:  {self.tools_coverage * 100:.1f}%")
        
        # Por categoría
        print(f"\n📁 BY CATEGORY")
        print("-" * 70)
        categories = self.get_category_metrics()
        for cat, m in categories.items():
            status_icon = "✅" if m.success_rate == 1.0 else "⚠️" if m.success_rate >= 0.5 else "❌"
            print(f"   {status_icon} {cat:20} {m.passed}/{m.total_tests} passed ({m.success_rate * 100:.0f}%) "
                  f"avg: {m.avg_duration_ms/1000:.1f}s")
        
        # Uso de herramientas
        print(f"\n🔧 TOOLS USAGE")
        print("-" * 70)
        tools = self.get_tools_usage()
        for tool, count in list(tools.items())[:10]:
            bar = "█" * min(count, 20)
            print(f"   {tool:15} {bar} ({count})")
        
        # Tests fallidos
        failed = self.get_failed_tests()
        if failed:
            print(f"\n❌ FAILED TESTS ({len(failed)})")
            print("-" * 70)
            for r in failed[:5]:  # Mostrar máximo 5
                print(f"   • {r.test_id}: {r.test_name}")
                print(f"     Status: {r.status.value}")
                if r.error:
                    print(f"     Error: {r.error[:100]}...")
        
        print("\n" + "=" * 70)


def create_markdown_report(metrics: BenchmarkMetrics) -> str:
    """Generar reporte en formato Markdown"""
    md = []
    md.append("# Brain 2.0 Benchmark Report\n")
    md.append(f"**Generated:** {datetime.now().isoformat()}\n")
    md.append(f"**API URL:** {metrics.api_url}\n\n")
    
    # Resumen
    md.append("## Summary\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Total Tests | {metrics.total_tests} |")
    md.append(f"| Passed | {metrics.passed} |")
    md.append(f"| Failed | {metrics.failed} |")
    md.append(f"| Errors | {metrics.errors} |")
    md.append(f"| Success Rate | {metrics.success_rate * 100:.1f}% |")
    md.append(f"| Total Duration | {metrics.total_duration_ms / 1000:.1f}s |")
    md.append(f"| Avg Duration | {metrics.avg_duration_ms / 1000:.2f}s |")
    md.append(f"| Tools Coverage | {metrics.tools_coverage * 100:.1f}% |")
    md.append("")
    
    # Por categoría
    md.append("## Results by Category\n")
    md.append("| Category | Passed | Failed | Success Rate | Avg Duration |")
    md.append("|----------|--------|--------|--------------|--------------|")
    for cat, m in metrics.get_category_metrics().items():
        md.append(f"| {cat} | {m.passed}/{m.total_tests} | {m.failed} | {m.success_rate * 100:.0f}% | {m.avg_duration_ms/1000:.1f}s |")
    md.append("")
    
    # Uso de herramientas
    md.append("## Tools Usage\n")
    md.append("| Tool | Times Used |")
    md.append("|------|------------|")
    for tool, count in metrics.get_tools_usage().items():
        md.append(f"| {tool} | {count} |")
    md.append("")
    
    # Tests fallidos
    failed = metrics.get_failed_tests()
    if failed:
        md.append("## Failed Tests\n")
        for r in failed:
            md.append(f"### ❌ {r.test_name} (`{r.test_id}`)\n")
            md.append(f"- **Status:** {r.status.value}")
            md.append(f"- **Category:** {r.category}")
            md.append(f"- **Duration:** {r.duration_ms}ms")
            if r.error:
                md.append(f"- **Error:** `{r.error}`")
            md.append("")
    
    # Todos los resultados
    md.append("## All Test Results\n")
    md.append("| ID | Name | Status | Duration | Tools Used |")
    md.append("|----|------|--------|----------|------------|")
    for r in metrics.results:
        status_emoji = "✅" if r.status == TestStatus.PASSED else "❌"
        tools = ", ".join(r.tools_used[:3]) + ("..." if len(r.tools_used) > 3 else "")
        md.append(f"| {r.test_id} | {r.test_name} | {status_emoji} {r.status.value} | {r.duration_ms}ms | {tools} |")
    
    return "\n".join(md)
