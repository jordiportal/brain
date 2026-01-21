"""
Code Executor Package
"""

from .models import (
    ExecutionResult,
    ExecutionConfig,
    ExecutionStatus,
    Language
)

# NO inicializar code_executor aquí (lazy loading)
# Se inicializará cuando se use por primera vez

def get_code_executor():
    """Get or create code executor instance (lazy loading)"""
    from .executor import CodeExecutor
    global _code_executor_instance
    if '_code_executor_instance' not in globals():
        _code_executor_instance = CodeExecutor()
    return _code_executor_instance


__all__ = [
    "get_code_executor",
    "ExecutionResult",
    "ExecutionConfig",
    "ExecutionStatus",
    "Language"
]

