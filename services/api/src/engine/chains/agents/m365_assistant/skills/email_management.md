# Gestión de Correo Electrónico - Skill Específico

## Estrategias de Búsqueda

### Por contenido
- `m365_mail_list(search="factura")` → Correos que contengan "factura"
- `m365_mail_list(search="from:juan@khlloreda.com")` → De un remitente específico
- `m365_mail_list(search="subject:Reunión mensual")` → Por asunto

### Por carpeta
- `m365_mail_list(folder="Inbox")` → Bandeja de entrada
- `m365_mail_list(folder="SentItems")` → Enviados
- `m365_mail_list(folder="Drafts")` → Borradores

### Combinada
- `m365_mail_list(folder="Inbox", search="urgente", page_size=5)` → Últimos 5 urgentes en inbox

## Plantillas de Correo HTML

### Formal
```html
<div style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #333;">
  <p>Estimado/a [nombre],</p>
  <p>[contenido]</p>
  <p>Quedo a su disposición para cualquier consulta.</p>
  <p>Atentamente,</p>
</div>
```

### Convocatoria de Reunión
```html
<div style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #333;">
  <p>Hola equipo,</p>
  <p>Os convoco a una reunión:</p>
  <table style="border-collapse: collapse; margin: 10px 0;">
    <tr><td style="padding: 4px 12px; font-weight: bold;">Tema:</td><td style="padding: 4px 12px;">[tema]</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Fecha:</td><td style="padding: 4px 12px;">[fecha]</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Hora:</td><td style="padding: 4px 12px;">[hora]</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Lugar:</td><td style="padding: 4px 12px;">[lugar]</td></tr>
  </table>
  <p>Por favor, confirmad asistencia.</p>
  <p>Gracias,</p>
</div>
```

### Seguimiento
```html
<div style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #333;">
  <p>Hola [nombre],</p>
  <p>Hago seguimiento respecto a [tema]. ¿Hay novedades al respecto?</p>
  <p>Quedo pendiente de tu respuesta.</p>
  <p>Un saludo,</p>
</div>
```

## Reglas de Envío

1. SIEMPRE mostrar un resumen antes de enviar:
   - Destinatarios
   - Asunto
   - Vista previa del contenido
2. Pedir confirmación explícita del usuario
3. Usar `content_type="html"` para correos formateados
4. Validar que los emails tengan formato correcto (@)
