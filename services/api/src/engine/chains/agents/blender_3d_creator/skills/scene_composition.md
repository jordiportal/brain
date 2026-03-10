# Composición de Escenas 3D

## Planificación

Antes de crear cualquier escena:
1. Definir la escala y dimensiones del espacio
2. Identificar elementos principales vs. detalles
3. Decidir el punto de vista / cámara
4. Planificar la iluminación

## Escala de referencia (1 unidad = 1 metro)

| Objeto | Dimensiones típicas |
|--------|-------------------|
| Persona | 1.7m alto |
| Puerta | 0.9m ancho × 2.1m alto |
| Mesa escritorio | 1.2m × 0.6m × 0.75m alto |
| Silla | 0.5m × 0.5m × 0.9m alto |
| Coche | 4.5m × 1.8m × 1.5m |
| Árbol | 3-8m alto |
| Casa | 8-12m ancho × 6-8m alto |

## Orden de creación

1. **Terreno/suelo** — plano base, ground plane
2. **Elementos mayores** — edificios, montañas, estructuras
3. **Elementos medios** — árboles, vehículos, muebles
4. **Detalles** — flores, piedras, accesorios
5. **Iluminación** — sol/luces + ambiente
6. **Cámara** — posición y encuadre

## Jerarquía de objetos

Usa nombres descriptivos con prefijo por categoría:
- `Ground`, `Terrain_*`
- `Building_*`, `House_*`
- `Tree_*`, `Rock_*`, `Flower_*`
- `Furniture_*`, `Prop_*`
- `Light_*`, `Camera_*`

## Verificación anti-clipping

Después de posicionar objetos, verifica con `get_object_info` que los bounding boxes
no se solapan. Ajusta posiciones si es necesario.

## Cámara

- **Focal length 24-35mm**: vistas amplias, paisajes, arquitectura
- **Focal length 50mm**: vista natural, similar al ojo humano
- **Focal length 85-135mm**: retratos, detalles, compresión de perspectiva
- Altura de cámara: ~1.6m para vista a nivel de persona
