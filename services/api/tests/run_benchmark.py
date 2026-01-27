#!/usr/bin/env python3
"""
Brain 2.0 Benchmark Runner

Script para ejecutar el benchmark completo de Core Tools.

Uso:
    # Ejecutar todos los tests
    python run_benchmark.py
    
    # Ejecutar con opciones
    python run_benchmark.py --api-url http://localhost:8000 --verbose
    
    # Solo una categoría
    python run_benchmark.py --category multi_tool
    
    # Tests específicos
    python run_benchmark.py --test-id mt_1_research_save --test-id ce_1_python_fibonacci
    
    # Ejecutar tests rápidos (1 por categoría)
    python run_benchmark.py --quick
    
    # Guardar reportes
    python run_benchmark.py --output-json results.json --output-markdown report.md
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Añadir el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark import (
    BenchmarkRunner,
    RunnerConfig,
    TestCategory,
    ALL_TESTS,
    MULTI_TOOL_TESTS,
    REASONING_TESTS,
    CODE_EXECUTION_TESTS,
    ERROR_HANDLING_TESTS,
    INTEGRATION_TESTS,
    # Advanced tests
    ADVANCED_TESTS,
    SHELL_ADMIN_TESTS,
    AGENTIC_CODING_TESTS,
    DATABASE_OPS_TESTS,
    DATA_PROCESSING_TESTS,
    CODE_QUALITY_TESTS,
)
from benchmark.runner import run_benchmark
from benchmark.metrics import create_markdown_report


def parse_args():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Brain 2.0 Core Tools Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Benchmark Básico (26 tests):
  - multi_tool       Tests de múltiples herramientas encadenadas
  - reasoning        Tests de cadenas de razonamiento
  - code_execution   Tests de ejecución de código
  - error_handling   Tests de manejo de errores
  - integration      Tests de integración complejos

Benchmark Avanzado (23 tests) - usar --advanced:
  - shell_admin      Instalación de paquetes, configuración de sistema
  - agentic_coding   Debugging, refactoring, feature development
  - database_ops     SQLite, migraciones, query building
  - data_processing  CSV, JSON, text processing, ETL
  - code_quality     Documentación, error handling

Ejemplos:
  %(prog)s --quick                          # Test rápido (1 por categoría)
  %(prog)s --advanced                       # Básico + Avanzado (49 tests)
  %(prog)s --advanced-only                  # Solo avanzados (23 tests)
  %(prog)s --tag advanced                   # Tests con tag 'advanced'
  %(prog)s --category reasoning             # Solo tests de razonamiento
  %(prog)s -o results.json -m report.md     # Guardar reportes
        """
    )
    
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="URL de la API de Brain (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--category", "-c",
        action="append",
        choices=["multi_tool", "reasoning", "code_execution", "error_handling", "integration"],
        help="Categoría(s) a ejecutar (puede repetirse)"
    )
    
    parser.add_argument(
        "--test-id", "-t",
        action="append",
        help="ID(s) de test específico a ejecutar (puede repetirse)"
    )
    
    parser.add_argument(
        "--tag",
        action="append",
        help="Tag(s) para filtrar tests (puede repetirse)"
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Ejecutar test rápido (1 test por categoría)"
    )
    
    # Advanced benchmark options
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Incluir tests avanzados (shell admin, agentic coding, database, etc.)"
    )
    
    parser.add_argument(
        "--advanced-only",
        action="store_true",
        help="Ejecutar SOLO tests avanzados (sin los básicos)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout por defecto en segundos (default: 120)"
    )
    
    # LLM Provider arguments
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "openai", "anthropic", "gemini", "groq"],
        default="ollama",
        help="Proveedor de LLM (default: ollama)"
    )
    
    parser.add_argument(
        "--llm-url",
        help="URL del proveedor LLM (ej: https://api.openai.com/v1)"
    )
    
    parser.add_argument(
        "--llm-api-key",
        help="API key del proveedor LLM"
    )
    
    parser.add_argument(
        "--llm-model",
        help="Modelo a usar (ej: gpt-4.1, claude-3-opus)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Mostrar progreso detallado (default: True)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Modo silencioso (sin output)"
    )
    
    parser.add_argument(
        "--output-json", "-o",
        help="Guardar reporte JSON en archivo"
    )
    
    parser.add_argument(
        "--output-markdown", "-m",
        help="Guardar reporte Markdown en archivo"
    )
    
    parser.add_argument(
        "--list-tests", "-l",
        action="store_true",
        help="Listar todos los tests disponibles y salir"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="No ejecutar queries de cleanup después de tests"
    )
    
    return parser.parse_args()


def list_tests():
    """Listar todos los tests disponibles"""
    print("\n📋 AVAILABLE TESTS")
    print("=" * 80)
    
    # Tests básicos
    print("\n" + "=" * 40)
    print("📦 BASIC BENCHMARK (26 tests)")
    print("=" * 40)
    
    basic_categories = {
        "multi_tool": ("🔗 Multi-Tool Workflows", MULTI_TOOL_TESTS),
        "reasoning": ("🧠 Reasoning Chains", REASONING_TESTS),
        "code_execution": ("💻 Code Execution", CODE_EXECUTION_TESTS),
        "error_handling": ("⚠️ Error Handling", ERROR_HANDLING_TESTS),
        "integration": ("🔄 Integration Tests", INTEGRATION_TESTS),
    }
    
    for cat_id, (cat_name, tests) in basic_categories.items():
        print(f"\n{cat_name} ({len(tests)} tests)")
        print("-" * 60)
        for test in tests:
            tags_str = ", ".join(test.tags[:3])
            print(f"  {test.id:25} {test.name}")
            print(f"  {'':25} Tools: {', '.join(test.expected_tools)}")
            print(f"  {'':25} Tags: {tags_str}")
            print()
    
    # Tests avanzados
    print("\n" + "=" * 40)
    print("🚀 ADVANCED BENCHMARK (23 tests)")
    print("=" * 40)
    
    advanced_categories = {
        "shell_admin": ("🖥️ Shell & System Admin", SHELL_ADMIN_TESTS),
        "agentic_coding": ("🛠️ Agentic Coding", AGENTIC_CODING_TESTS),
        "database_ops": ("🗄️ Database Operations", DATABASE_OPS_TESTS),
        "data_processing": ("📊 Data Processing", DATA_PROCESSING_TESTS),
        "code_quality": ("✨ Code Quality", CODE_QUALITY_TESTS),
    }
    
    for cat_id, (cat_name, tests) in advanced_categories.items():
        print(f"\n{cat_name} ({len(tests)} tests)")
        print("-" * 60)
        for test in tests:
            tags_str = ", ".join(test.tags[:3])
            print(f"  {test.id:25} {test.name}")
            print(f"  {'':25} Tools: {', '.join(test.expected_tools)}")
            print(f"  {'':25} Tags: {tags_str}")
            print()
    
    print(f"\nTotal: {len(ALL_TESTS)} basic + {len(ADVANCED_TESTS)} advanced = {len(ALL_TESTS) + len(ADVANCED_TESTS)} tests")


async def main():
    """Función principal"""
    args = parse_args()
    
    # Listar tests y salir
    if args.list_tests:
        list_tests()
        return 0
    
    # Configurar verbosidad
    verbose = not args.quiet and args.verbose
    
    # Ejecutar benchmark
    try:
        # Configuración base de LLM
        llm_config = {
            "llm_provider_type": args.llm_provider,
            "llm_provider_url": args.llm_url,
            "llm_api_key": args.llm_api_key,
            "llm_model": args.llm_model,
        }
        
        # Configuración de benchmark avanzado
        use_advanced = args.advanced or args.advanced_only
        include_basic = not args.advanced_only
        
        if args.quick:
            # Modo rápido: 1 test por categoría
            config = RunnerConfig(
                api_url=args.api_url,
                timeout_default=args.timeout,
                verbose=verbose,
                run_cleanup=not args.no_cleanup,
                use_advanced=use_advanced,
                include_basic=include_basic,
                **llm_config,
            )
            
            async with BenchmarkRunner(config) as runner:
                metrics = await runner.run_quick()
        else:
            # Modo normal con LLM config
            config = RunnerConfig(
                api_url=args.api_url,
                timeout_default=args.timeout,
                verbose=verbose,
                run_cleanup=not args.no_cleanup,
                categories=[TestCategory(c) for c in args.category] if args.category else None,
                test_ids=args.test_id,
                tags=args.tag,
                use_advanced=use_advanced,
                include_basic=include_basic,
                **llm_config,
            )
            
            async with BenchmarkRunner(config) as runner:
                metrics = await runner.run_all()
        
        # Guardar reportes si se especificaron
        if args.output_json:
            metrics.save_report(args.output_json)
            if verbose:
                print(f"\n📄 JSON report saved to: {args.output_json}")
        
        if args.output_markdown:
            md_report = create_markdown_report(metrics)
            with open(args.output_markdown, "w", encoding="utf-8") as f:
                f.write(md_report)
            if verbose:
                print(f"📝 Markdown report saved to: {args.output_markdown}")
        
        # Imprimir resumen final
        if verbose:
            metrics.print_summary()
        
        # Return code basado en éxito
        if metrics.success_rate >= 0.8:
            return 0  # Éxito
        elif metrics.success_rate >= 0.5:
            return 1  # Parcialmente exitoso
        else:
            return 2  # Fallo
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Benchmark interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error running benchmark: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
