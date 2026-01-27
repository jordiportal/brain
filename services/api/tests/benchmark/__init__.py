"""
Brain 2.0 Core Tools Benchmark Suite

Este módulo contiene pruebas de integración para validar
el funcionamiento de las 15 Core Tools a través del Adaptive Agent.

Incluye:
- Benchmark básico (26 tests): Tests fundamentales de cada herramienta
- Benchmark avanzado (23 tests): Tests complejos de desarrollo real
"""

from .test_cases import (
    TestCase,
    TestCategory,
    MULTI_TOOL_TESTS,
    REASONING_TESTS,
    CODE_EXECUTION_TESTS,
    ERROR_HANDLING_TESTS,
    INTEGRATION_TESTS,
    ALL_TESTS,
)
from .test_cases_advanced import (
    ADVANCED_TESTS,
    SHELL_ADMIN_TESTS,
    AGENTIC_CODING_TESTS,
    DATABASE_OPS_TESTS,
    DATA_PROCESSING_TESTS,
    CODE_QUALITY_TESTS,
    get_advanced_tests_by_category,
    get_all_advanced_test_ids,
)
from .runner import BenchmarkRunner, RunnerConfig
from .metrics import BenchmarkMetrics, TestResult

__all__ = [
    # Core test cases
    "TestCase",
    "TestCategory",
    "MULTI_TOOL_TESTS",
    "REASONING_TESTS",
    "CODE_EXECUTION_TESTS",
    "ERROR_HANDLING_TESTS",
    "INTEGRATION_TESTS",
    "ALL_TESTS",
    # Advanced test cases
    "ADVANCED_TESTS",
    "SHELL_ADMIN_TESTS",
    "AGENTIC_CODING_TESTS",
    "DATABASE_OPS_TESTS",
    "DATA_PROCESSING_TESTS",
    "CODE_QUALITY_TESTS",
    "get_advanced_tests_by_category",
    "get_all_advanced_test_ids",
    # Runner & metrics
    "BenchmarkRunner",
    "RunnerConfig",
    "BenchmarkMetrics",
    "TestResult",
]
