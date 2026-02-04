"""Módulo compartido: templates, themes, events para presentaciones.

El DesignerAgent usa estos componentes. No hay agente slides independiente.
"""

from .templates import SlideOutline, PresentationOutline, generate_slide_html
from .themes import get_theme, generate_css, detect_theme_from_topic, create_custom_theme, THEMES, ThemeColors
from .events import thinking_event, action_event, artifact_event

__all__ = [
    "SlideOutline",
    "PresentationOutline",
    "generate_slide_html",
    "get_theme",
    "generate_css",
    "detect_theme_from_topic",
    "create_custom_theme",
    "THEMES",
    "ThemeColors",
    "thinking_event",
    "action_event",
    "artifact_event",
]
