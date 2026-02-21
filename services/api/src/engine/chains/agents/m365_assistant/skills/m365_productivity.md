# Microsoft 365 Productivity - Skill de Dominio

## Herramientas Disponibles

### Correo (Outlook)
| Herramienta | Descripción | Parámetros clave |
|---|---|---|
| `m365_mail_list` | Lista correos | `folder`, `search`, `page`, `page_size` |
| `m365_mail_folders` | Lista carpetas | - |
| `m365_mail_send` | Envía correo | `subject`, `body`, `to_recipients`, `content_type` |

### Calendario
| Herramienta | Descripción | Parámetros clave |
|---|---|---|
| `m365_calendar_list` | Lista calendarios | - |
| `m365_calendar_events` | Lista eventos | `start_date_time`, `end_date_time`, `page`, `page_size` |
| `m365_calendar_create_event` | Crea evento | `subject`, `start`, `end`, `location`, `attendees` |

### OneDrive
| Herramienta | Descripción | Parámetros clave |
|---|---|---|
| `m365_onedrive_root` | Info raíz OneDrive | - |
| `m365_onedrive_list` | Lista archivos raíz | `page`, `page_size` |
| `m365_onedrive_search` | Busca archivos | `q` |

### Teams
| Herramienta | Descripción | Parámetros clave |
|---|---|---|
| `m365_teams_list` | Lista equipos | - |
| `m365_teams_chats` | Lista chats | - |
| `m365_teams_channels` | Canales de equipo | `team_id` |
| `m365_teams_members` | Miembros equipo | `team_id` |
| `m365_teams_channel_messages` | Mensajes canal | `team_id`, `channel_id` |
| `m365_teams_send_message` | Envía mensaje | `team_id`, `channel_id`, `content` |

### Directorio (Azure AD)
| Herramienta | Descripción | Parámetros clave |
|---|---|---|
| `m365_directory_users` | Busca usuarios | `search`, `page`, `page_size` |
| `m365_directory_groups` | Lista grupos | `page`, `page_size` |
| `m365_directory_group_members` | Miembros grupo | `group_id` |

## Patrones de Uso Comunes

### Correo - Buscar y Resumir
1. `m365_mail_list(search="presupuesto")` → Buscar correos sobre presupuesto
2. Presentar resultados con asunto, remitente y fecha
3. Si hay muchos, ofrecer paginación

### Correo - Enviar con Confirmación
1. Preparar borrador con formato HTML
2. Mostrar resumen al usuario: destinatarios, asunto, contenido
3. Tras confirmación: `m365_mail_send(subject=..., body=..., to_recipients=[...])`

### Calendario - Consulta Semanal
1. Calcular inicio y fin de la semana actual
2. `m365_calendar_events(start_date_time="...", end_date_time="...")`
3. Presentar agenda organizada por día

### Calendario - Crear Evento
1. Confirmar detalles: título, fecha, hora, duración, asistentes
2. Formato start/end: `{"dateTime": "2026-02-20T10:00:00", "timeZone": "Europe/Madrid"}`
3. `m365_calendar_create_event(subject=..., start=..., end=..., attendees=[...])`

### OneDrive - Buscar Documento
1. `m365_onedrive_search(q="presupuesto 2026")`
2. Mostrar nombre, tamaño y fecha de cada resultado

### Teams - Flujo Completo de Envío
1. `m365_teams_list()` → Identificar equipo
2. `m365_teams_channels(team_id=...)` → Identificar canal
3. Confirmar mensaje con el usuario
4. `m365_teams_send_message(team_id=..., channel_id=..., content=...)`

### Directorio - Buscar Persona
1. `m365_directory_users(search="García")` → Buscar por nombre
2. Mostrar nombre completo, email, departamento, cargo

## Formato HTML para Correos

```html
<div style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #333;">
  <p>Estimado/a [nombre],</p>
  <p>[contenido del mensaje]</p>
  <p>Saludos cordiales,</p>
</div>
```

## Notas Importantes

- Las carpetas de correo usan nombres internos: `Inbox`, `SentItems`, `Drafts`, `DeletedItems`, `Archive`
- Los IDs de equipos y canales de Teams son GUIDs (ej: "19:abc123@thread.tacv2")
- Para eventos recurrentes, crear cada instancia individual
- La búsqueda en OneDrive funciona por nombre de archivo y contenido indexado
- La zona horaria por defecto es "Europe/Madrid" para KH Lloreda
