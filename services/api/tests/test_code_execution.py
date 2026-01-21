"""
Tests para el Code Execution Agent
"""

import pytest
import asyncio
from src.code_executor import code_executor, Language, ExecutionStatus


class TestCodeExecutor:
    """Tests del ejecutor de código"""
    
    def test_health_check(self):
        """Verificar que Docker esté funcionando"""
        assert code_executor.health_check(), "Docker no está disponible"
    
    @pytest.mark.asyncio
    async def test_python_simple(self):
        """Test básico de ejecución Python"""
        code = """
print("Hello from Python!")
print(2 + 2)
"""
        result = await code_executor.execute_python(code)
        
        assert result.success is True
        assert "Hello from Python!" in result.stdout
        assert "4" in result.stdout
        assert result.exit_code == 0
        assert result.language == Language.PYTHON
    
    @pytest.mark.asyncio
    async def test_python_fibonacci(self):
        """Test Python con lógica"""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(fibonacci(i), end=' ')
"""
        result = await code_executor.execute_python(code)
        
        assert result.success is True
        assert "0 1 1 2 3 5 8 13 21 34" in result.stdout
    
    @pytest.mark.asyncio
    async def test_python_with_numpy(self):
        """Test Python con biblioteca numpy"""
        code = """
import numpy as np

arr = np.array([1, 2, 3, 4, 5])
print(f"Array: {arr}")
print(f"Mean: {np.mean(arr)}")
print(f"Sum: {np.sum(arr)}")
"""
        result = await code_executor.execute_python(code)
        
        assert result.success is True
        assert "Array:" in result.stdout
        assert "Mean: 3.0" in result.stdout
        assert "Sum: 15" in result.stdout
    
    @pytest.mark.asyncio
    async def test_python_error(self):
        """Test Python con error"""
        code = """
print("Start")
x = 1 / 0  # Division por cero
print("Never reached")
"""
        result = await code_executor.execute_python(code)
        
        assert result.success is False
        assert result.status == ExecutionStatus.ERROR
        assert result.exit_code != 0
    
    @pytest.mark.asyncio
    async def test_python_timeout(self):
        """Test Python con timeout"""
        code = """
import time
while True:
    time.sleep(1)
"""
        result = await code_executor.execute_python(code, timeout=3)
        
        assert result.success is False
        assert result.status == ExecutionStatus.TIMEOUT
        assert "timeout" in result.stderr.lower()
    
    @pytest.mark.asyncio
    async def test_javascript_simple(self):
        """Test básico de ejecución JavaScript"""
        code = """
console.log("Hello from Node.js!");
console.log(2 + 2);
"""
        result = await code_executor.execute_javascript(code)
        
        assert result.success is True
        assert "Hello from Node.js!" in result.stdout
        assert "4" in result.stdout
        assert result.exit_code == 0
        assert result.language == Language.JAVASCRIPT
    
    @pytest.mark.asyncio
    async def test_javascript_with_lodash(self):
        """Test JavaScript con biblioteca lodash"""
        code = """
const _ = require('lodash');

const arr = [1, 2, 3, 4, 5];
console.log("Array:", arr);
console.log("Sum:", _.sum(arr));
console.log("Mean:", _.mean(arr));
"""
        result = await code_executor.execute_javascript(code)
        
        assert result.success is True
        assert "Sum: 15" in result.stdout
        assert "Mean: 3" in result.stdout
    
    @pytest.mark.asyncio
    async def test_javascript_error(self):
        """Test JavaScript con error"""
        code = """
console.log("Start");
const x = undefined.property;  // Error
console.log("Never reached");
"""
        result = await code_executor.execute_javascript(code)
        
        assert result.success is False
        assert result.status == ExecutionStatus.ERROR


@pytest.mark.asyncio
async def test_concurrent_executions():
    """Test de ejecuciones concurrentes"""
    codes = [
        "print('Task 1')",
        "print('Task 2')",
        "print('Task 3')"
    ]
    
    tasks = [code_executor.execute_python(code) for code in codes]
    results = await asyncio.gather(*tasks)
    
    assert all(r.success for r in results)
    assert results[0].stdout.strip() == "Task 1"
    assert results[1].stdout.strip() == "Task 2"
    assert results[2].stdout.strip() == "Task 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
