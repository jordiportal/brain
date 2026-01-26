# Investigación: Descarga de Archivos de Archive.org

**Fecha**: 23 de Enero de 2026  
**Objetivo**: Implementar descarga automatizada de archivos desde Archive.org usando el Persistent Admin Agent

## Problema Identificado

La colección específica solicitada por el usuario (`sonyplaystationasiantscj20151103`) **está bloqueada o tiene restricciones de acceso**.

### Errores Encontrados

1. **Error 403 Forbidden**: Al intentar descargar archivos de la colección
   ```
   Status: 403
   Final URL: https://ia601903.us.archive.org/12/items/sonyplaystationasiantscj20151103/...
   Response: Item not available
   ```

2. **WebFetch también bloqueado**: La colección no es accesible públicamente
   ```
   Error fetching URL: Access is forbidden or source is unavailable
   ```

## Solución Técnica Implementada

### 1. Uso de la API de Metadata de Archive.org

En lugar de parsear HTML (que era el enfoque inicial), se implementó el uso de la **Metadata API** de Archive.org:

```python
# API de metadata (más confiable)
metadata_url = f"https://archive.org/metadata/{collection_id}"
response = requests.get(metadata_url, timeout=60)
metadata = response.json()

# Obtener archivos
all_files = metadata['files']
target_files = [f for f in all_files if f.get('name', '').endswith('.7z')]
```

**Ventajas**:
- Más confiable que scraping HTML
- Devuelve datos estructurados en JSON
- Incluye metadata completa (tamaño, formato, etc.)

### 2. Manejo de Restricciones de Acceso

Se implementó manejo explícito de errores de autenticación/autorización:

```python
if file_response.status_code == 403:
    log(f"❌ Error 403 Forbidden: El archivo no es accesible públicamente")
    log(f"   Posibles causas:")
    log(f"   - La colección requiere autenticación")
    log(f"   - El contenido tiene restricciones de copyright")
    log(f"   - Acceso geográfico bloqueado")
elif file_response.status_code == 401:
    log(f"❌ Error 401 Unauthorized: Se requiere autenticación")
```

### 3. Código de Ejemplo Actualizado en persistent_admin_agent.py

Se agregó un ejemplo completo en el system prompt del agente con:
- Uso de la Metadata API
- Manejo de errores 403/401
- Logging detallado
- Mensaje informativo al usuario sobre restricciones

## Autenticación en Archive.org (Para Futuras Implementaciones)

Según la documentación oficial de Archive.org, para acceder a contenido restringido se requiere:

### Opción 1: Cookies de Sesión
```python
cookies = {
    'logged-in-user': 'user%40example.com',
    'logged-in-sig': 'signature_string'
}
```

### Opción 2: Credenciales IA-S3
- Disponibles en: https://archive.org/account/s3.php
- Necesarios para operaciones de escritura y algunos downloads

### Opción 3: Biblioteca `internetarchive`
```python
from internetarchive import get_session, download

# Configurar sesión
session = get_session()
session.configure('email@example.com', 'password')

# Descargar
download('item_id', files=['filename.7z'])
```

## Pruebas Realizadas

### ✅ Colección Pública (Funciona)
```
Item: msdos_Oregon_Trail_The_1990
Archivo: 00_coverscreenshot.jpg
Status: 200 OK
Resultado: Descarga exitosa
```

### ❌ Colección del Usuario (Bloqueada)
```
Item: sonyplaystationasiantscj20151103
Archivo: '98 Koushien - Koukou Yakyuu Simulation (Japan).7z
Status: 403 Forbidden
Resultado: Item not available
```

## Estado Actual

### Implementado ✅
1. Uso de Metadata API en ejemplos del prompt
2. Manejo de errores 403/401 con mensajes informativos
3. Documentación clara de restricciones de acceso
4. Código de ejemplo robusto para descargas públicas

### Pendiente para Futuras Mejoras
1. Implementar autenticación de Archive.org (cookies o librería `internetarchive`)
2. Detectar automáticamente si una colección es privada antes de intentar descargar
3. Sugerir al usuario crear cuenta o proporcionar credenciales para colecciones restringidas

## Conclusión

La implementación técnica es correcta y funciona perfectamente con colecciones públicas de Archive.org. El problema específico con la colección `sonyplaystationasiantscj20151103` se debe a **restricciones de acceso a nivel de Archive.org**, no a problemas en nuestro código.

El agente ahora:
- ✅ Usa la API de metadata correctamente
- ✅ Descarga exitosamente de colecciones públicas
- ✅ Informa claramente al usuario cuando una colección tiene restricciones
- ✅ Sugiere posibles causas y soluciones

## Recomendación al Usuario

Para descargar archivos de colecciones restringidas como `sonyplaystationasiantscj20151103`, el usuario necesitaría:
1. Crear una cuenta en Archive.org
2. Verificar si la colección requiere permisos especiales
3. Proporcionar credenciales de autenticación al sistema
4. Alternativamente, buscar una colección pública similar
