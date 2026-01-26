"""
Brain 2.0 Core Tools - Utils (1 tool)

- calculate: Evaluar expresiones matemáticas
"""

import math
from typing import Dict, Any
import structlog

logger = structlog.get_logger()


# ============================================
# Tool Handlers
# ============================================

async def calculate(
    expression: str
) -> Dict[str, Any]:
    """
    Evalúa una expresión matemática de forma segura.
    
    Soporta:
    - Operaciones básicas: +, -, *, /, **, %
    - Funciones: sqrt, pow, sin, cos, tan, log, log10, abs, round
    - Constantes: pi, e
    
    Args:
        expression: Expresión matemática a evaluar
    
    Returns:
        {"success": True, "result": number} o {"error": str}
    """
    # Funciones y constantes permitidas
    allowed = {
        # Funciones matemáticas
        'sqrt': math.sqrt,
        'pow': pow,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        'exp': math.exp,
        'abs': abs,
        'round': round,
        'floor': math.floor,
        'ceil': math.ceil,
        'min': min,
        'max': max,
        # Constantes
        'pi': math.pi,
        'e': math.e,
        'inf': math.inf,
    }
    
    try:
        logger.info(f"🔢 calculate: {expression}")
        
        # Evaluar expresión de forma segura (sin builtins)
        result = eval(expression, {"__builtins__": {}}, allowed)
        
        # Verificar que el resultado es un número
        if not isinstance(result, (int, float, complex)):
            return {
                "success": False,
                "error": f"Resultado no es un número: {type(result).__name__}",
                "expression": expression
            }
        
        # Manejar infinito y NaN
        if isinstance(result, float):
            if math.isnan(result):
                return {
                    "success": False,
                    "error": "El resultado es NaN (Not a Number)",
                    "expression": expression
                }
            if math.isinf(result):
                result = "Infinity" if result > 0 else "-Infinity"
        
        logger.info(f"✅ calculate result: {result}")
        
        return {
            "success": True,
            "result": result,
            "expression": expression
        }
        
    except ZeroDivisionError:
        return {
            "success": False,
            "error": "División por cero",
            "expression": expression
        }
    except ValueError as e:
        return {
            "success": False,
            "error": f"Error matemático: {str(e)}",
            "expression": expression
        }
    except SyntaxError:
        return {
            "success": False,
            "error": "Sintaxis inválida en la expresión",
            "expression": expression
        }
    except NameError as e:
        return {
            "success": False,
            "error": f"Función o variable no permitida: {str(e)}",
            "expression": expression,
            "allowed_functions": list(allowed.keys())
        }
    except Exception as e:
        logger.error(f"Error en calculate: {e}")
        return {
            "success": False,
            "error": str(e),
            "expression": expression
        }


# ============================================
# Tool Definitions for Registry
# ============================================

UTILS_TOOLS = {
    "calculate": {
        "id": "calculate",
        "name": "calculate",
        "description": "Evalúa expresiones matemáticas. Soporta +, -, *, /, **, sqrt, pow, sin, cos, tan, log, abs, round, pi, e.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expresión matemática (ej: '2 + 2', 'sqrt(16)', 'pow(2, 8)', 'sin(pi/2)')"
                }
            },
            "required": ["expression"]
        },
        "handler": calculate
    }
}
