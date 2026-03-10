# Patrones Blender Python

## Limpiar escena
```python
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
# Limpiar datos huérfanos
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)
```

## Crear objeto con material
```python
import bpy

# Crear cubo
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
obj = bpy.context.active_object
obj.name = "MiObjeto"
obj.scale = (2, 1, 1)
bpy.ops.object.transform_apply(scale=True)

# Crear y asignar material
mat = bpy.data.materials.new("MiMaterial")
mat.use_nodes = True
for n in mat.node_tree.nodes:
    if n.type == 'BSDF_PRINCIPLED':
        n.inputs['Base Color'].default_value = (0.8, 0.2, 0.2, 1.0)
        n.inputs['Roughness'].default_value = 0.5
        break
obj.data.materials.append(mat)
```

## Geometría con bmesh (tejados, formas complejas)
```python
import bpy
import bmesh

mesh = bpy.data.meshes.new("GableMesh")
bm = bmesh.new()

# Definir vértices
v0 = bm.verts.new((-1, -1, 0))
v1 = bm.verts.new(( 1, -1, 0))
v2 = bm.verts.new(( 1,  1, 0))
v3 = bm.verts.new((-1,  1, 0))
v4 = bm.verts.new(( 0, -1, 1))  # pico
v5 = bm.verts.new(( 0,  1, 1))

# Crear caras
bm.faces.new([v0, v1, v4])  # triángulo frontal
bm.faces.new([v2, v3, v5])  # triángulo trasero
bm.faces.new([v0, v4, v5, v3])  # pendiente izq
bm.faces.new([v1, v2, v5, v4])  # pendiente der

bm.to_mesh(mesh)
bm.free()

obj = bpy.data.objects.new("Gable", mesh)
bpy.context.collection.objects.link(obj)
```

## Configurar render
```python
import bpy
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'  # NO usar BLENDER_EEVEE_NEXT
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.film_transparent = False
```

## Configurar cámara
```python
import bpy
import math

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 35  # focal length mm
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam_obj)
cam_obj.location = (10, -10, 6)

# Apuntar a un punto
from mathutils import Vector
direction = Vector((0, 0, 1)) - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

bpy.context.scene.camera = cam_obj
```

## Duplicar objetos (eficiente para repeticiones)
```python
import bpy
src = bpy.data.objects["ArbolBase"]
for i in range(10):
    copy = src.copy()
    copy.data = src.data.copy()  # copia independiente del mesh
    copy.name = f"Arbol_{i}"
    copy.location = (i * 3, 0, 0)
    bpy.context.collection.objects.link(copy)
```

## Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `Principled BSDF` no encontrado | Blender en español | Buscar por `n.type == 'BSDF_PRINCIPLED'` |
| `BLENDER_EEVEE_NEXT` no existe | Versión de Blender | Usar `BLENDER_EEVEE` |
| Screenshot negro | Sin display activo | scrot ya soluciona esto |
| Permission denied en filepath | Path del host vs container | Usar `/tmp/` dentro del container |
| Context error en operador | Llamada desde hilo incorrecto | Usar `bpy.context.temp_override` |
