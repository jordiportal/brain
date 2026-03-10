# Flujo de Trabajo con Assets Externos

## Estrategia de selección de fuente

### 1. Sketchfab (modelos realistas)
- Mejor para: modelos específicos y detallados (muebles, vehículos, personajes)
- Flujo: `search_sketchfab_models` → `get_sketchfab_model_preview` → `download_sketchfab_model`
- Siempre especificar `target_size` en metros al descargar

Tamaños de referencia para `target_size`:
- Silla: 1.0
- Mesa: 0.75
- Coche: 4.5
- Persona: 1.7
- Objeto pequeño (taza, teléfono): 0.1-0.3
- Árbol: 5.0-8.0

### 2. PolyHaven (texturas, HDRIs, modelos genéricos)
- Mejor para: texturas PBR, iluminación HDRI, modelos básicos
- Texturas: `search_polyhaven_assets(asset_type="textures")` → `download_polyhaven_asset` → `set_texture`
- HDRIs: `search_polyhaven_assets(asset_type="hdris")` → `download_polyhaven_asset`
- Modelos: `search_polyhaven_assets(asset_type="models")` → `download_polyhaven_asset`

### 3. Hyper3D Rodin (generación IA)
- Mejor para: objetos únicos que no existen en librerías
- Flujo: `generate_hyper3d_model_via_text` → `poll_rodin_job_status` (polling) → `import_generated_asset`
- No usar para: escenas completas, terrenos, partes separadas de un objeto

### 4. Hunyuan3D (generación IA alternativa)
- Similar a Hyper3D, alternativa si la otra no está disponible
- Flujo: `generate_hunyuan3d_model` → `poll_hunyuan_job_status` (polling) → `import_generated_asset_hunyuan`

### 5. Código Python (primitivas)
- Usar para: formas geométricas básicas, combinaciones de primitivas
- `bpy.ops.mesh.primitive_cube_add()`, `primitive_uv_sphere_add()`, `primitive_cylinder_add()`, etc.
- Mejor para: paredes, suelos, formas procedurales con `bmesh`

## Post-importación

Después de importar cualquier asset:
1. Verificar dimensiones con `get_object_info`
2. Ajustar posición, rotación y escala
3. Verificar que no hay clipping con otros objetos
4. Tomar screenshot para confirmar visualmente

## Verificación de disponibilidad

Antes de usar integraciones, verificar estado:
- `get_polyhaven_status` → PolyHaven habilitado?
- `get_sketchfab_status` → Sketchfab habilitado?
- `get_hyper3d_status` → Hyper3D habilitado?
- `get_hunyuan3d_status` → Hunyuan3D habilitado?
