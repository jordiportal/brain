# Materiales e Iluminación

## Crear materiales PBR

```python
def make_material(name, base_color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
    if bsdf:
        bsdf.inputs['Base Color'].default_value = base_color  # (R, G, B, A)
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
    return mat
```

## Paletas de colores por temática

### Naturaleza
- Hierba: (0.2, 0.45, 0.12, 1.0) roughness=0.85
- Tierra: (0.35, 0.22, 0.1, 1.0) roughness=0.95
- Piedra: (0.5, 0.48, 0.45, 1.0) roughness=0.9
- Agua: (0.1, 0.3, 0.5, 1.0) roughness=0.05, metallic=0.0
- Nieve: (0.95, 0.95, 0.97, 1.0) roughness=0.6

### Arquitectura
- Pared estucada: (0.9, 0.85, 0.78, 1.0) roughness=0.9
- Ladrillo: (0.55, 0.25, 0.15, 1.0) roughness=0.85
- Hormigón: (0.6, 0.58, 0.55, 1.0) roughness=0.95
- Madera clara: (0.7, 0.5, 0.3, 1.0) roughness=0.75
- Madera oscura: (0.3, 0.15, 0.05, 1.0) roughness=0.7
- Teja: (0.55, 0.22, 0.1, 1.0) roughness=0.7

### Metal y cristal
- Acero: (0.7, 0.7, 0.72, 1.0) metallic=1.0, roughness=0.3
- Oro: (1.0, 0.76, 0.33, 1.0) metallic=1.0, roughness=0.2
- Cristal: (0.8, 0.9, 0.95, 1.0) roughness=0.0, transmission=1.0

## Iluminación

### Setup exterior (sol)
```python
bpy.ops.object.light_add(type='SUN')
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(45), 0, math.radians(30))
sun.data.color = (1.0, 0.95, 0.9)  # Luz cálida
```

### Setup 3 puntos (interior)
1. **Key light**: luz principal, 45° lateral, intensidad alta
2. **Fill light**: opuesto al key, mitad de intensidad
3. **Back/rim light**: detrás del sujeto, para separar del fondo

### HDRI (via PolyHaven)
Buscar y aplicar un HDRI para iluminación ambiental realista:
- `search_polyhaven_assets(asset_type="hdris", categories="outdoor")`
- `download_polyhaven_asset(asset_id="...", asset_type="hdris", resolution="2k")`

## Viewport shading

Para ver materiales en el viewport:
```python
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces[0].shading.type = 'MATERIAL'
```
