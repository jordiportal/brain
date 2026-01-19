#!/usr/bin/env python3
"""
Script de prueba para la búsqueda web con DuckDuckGo
"""

import asyncio
import sys
import os

# Agregar el path de src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services/api/src'))

from tools.tool_registry import tool_registry


async def test_web_search():
    """Prueba la búsqueda web"""
    
    print("=" * 60)
    print("🧪 TEST: Búsqueda Web con DuckDuckGo")
    print("=" * 60)
    
    # Registrar herramientas builtin
    print("\n📦 Registrando herramientas builtin...")
    tool_registry.register_builtin_tools()
    
    # Verificar que web_search está registrada
    tool = tool_registry.get("web_search")
    if not tool:
        print("❌ ERROR: web_search no está registrada")
        return
    
    print(f"✅ Herramienta encontrada: {tool.name}")
    print(f"   Descripción: {tool.description}")
    print(f"   Tipo: {tool.type}")
    
    # Ejecutar búsqueda de prueba
    print("\n🔍 Ejecutando búsqueda: 'Python programming language'")
    print("-" * 60)
    
    result = await tool_registry.execute(
        "web_search",
        query="Python programming language",
        max_results=3
    )
    
    if result.get("success"):
        print(f"✅ Búsqueda exitosa - {result.get('count', 0)} resultados")
        print()
        
        for idx, item in enumerate(result.get("results", []), 1):
            print(f"\n📄 Resultado {idx}:")
            print(f"   Título: {item.get('title', 'N/A')}")
            print(f"   Snippet: {item.get('snippet', 'N/A')[:150]}...")
            print(f"   URL: {item.get('url', 'N/A')}")
    else:
        print(f"❌ Error en búsqueda: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("✅ Test completado")
    print("=" * 60)


async def test_multiple_searches():
    """Prueba múltiples búsquedas"""
    print("\n\n" + "=" * 60)
    print("🧪 TEST: Múltiples Búsquedas")
    print("=" * 60)
    
    queries = [
        "latest AI news",
        "weather Madrid",
        "Bitcoin price"
    ]
    
    tool_registry.register_builtin_tools()
    
    for query in queries:
        print(f"\n🔍 Buscando: '{query}'")
        result = await tool_registry.execute("web_search", query=query, max_results=2)
        
        if result.get("success"):
            print(f"   ✅ {result.get('count', 0)} resultados encontrados")
            if result.get("results"):
                first = result["results"][0]
                print(f"   📌 {first.get('title', 'N/A')[:60]}...")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown')}")


async def main():
    """Main test runner"""
    try:
        # Test básico
        await test_web_search()
        
        # Test múltiple
        await test_multiple_searches()
        
    except ImportError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Solución:")
        print("   cd services/api")
        print("   pip install duckduckgo-search")
        print("   o ejecuta: docker compose restart api")
    except Exception as e:
        print(f"\n❌ ERROR inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
