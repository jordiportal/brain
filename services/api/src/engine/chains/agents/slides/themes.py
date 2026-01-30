"""
Temas dinámicos para presentaciones.

Cada tema define colores, gradientes y estilos que se aplican
al CSS generado.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ThemeColors:
    """Colores de un tema."""
    primary: str          # Color principal (títulos, acentos)
    secondary: str        # Color secundario
    background_start: str # Gradiente fondo inicio
    background_end: str   # Gradiente fondo fin
    text: str             # Color texto principal
    text_muted: str       # Color texto secundario
    badge_bg: str         # Fondo de badges
    badge_text: str       # Texto de badges


# Temas predefinidos
THEMES: Dict[str, ThemeColors] = {
    "dark": ThemeColors(
        primary="#e94560",
        secondary="#f39c12",
        background_start="#1a1a2e",
        background_end="#16213e",
        text="#ffffff",
        text_muted="#888888",
        badge_bg="rgba(233, 69, 96, 0.2)",
        badge_text="#e94560"
    ),
    
    "corporate": ThemeColors(
        primary="#2563eb",
        secondary="#3b82f6",
        background_start="#1e293b",
        background_end="#0f172a",
        text="#f1f5f9",
        text_muted="#94a3b8",
        badge_bg="rgba(37, 99, 235, 0.2)",
        badge_text="#60a5fa"
    ),
    
    "eco": ThemeColors(
        primary="#10b981",
        secondary="#34d399",
        background_start="#064e3b",
        background_end="#022c22",
        text="#ecfdf5",
        text_muted="#6ee7b7",
        badge_bg="rgba(16, 185, 129, 0.2)",
        badge_text="#34d399"
    ),
    
    "tech": ThemeColors(
        primary="#8b5cf6",
        secondary="#a78bfa",
        background_start="#1e1b4b",
        background_end="#0f0a1e",
        text="#f5f3ff",
        text_muted="#c4b5fd",
        badge_bg="rgba(139, 92, 246, 0.2)",
        badge_text="#a78bfa"
    ),
    
    "warm": ThemeColors(
        primary="#f97316",
        secondary="#fb923c",
        background_start="#431407",
        background_end="#1c0a00",
        text="#fff7ed",
        text_muted="#fdba74",
        badge_bg="rgba(249, 115, 22, 0.2)",
        badge_text="#fb923c"
    ),
    
    "minimal": ThemeColors(
        primary="#374151",
        secondary="#6b7280",
        background_start="#f9fafb",
        background_end="#f3f4f6",
        text="#111827",
        text_muted="#6b7280",
        badge_bg="rgba(55, 65, 81, 0.1)",
        badge_text="#374151"
    ),
    
    "ocean": ThemeColors(
        primary="#0891b2",
        secondary="#22d3ee",
        background_start="#164e63",
        background_end="#083344",
        text="#ecfeff",
        text_muted="#67e8f9",
        badge_bg="rgba(8, 145, 178, 0.2)",
        badge_text="#22d3ee"
    ),
}


def get_theme(name: str) -> ThemeColors:
    """Obtiene un tema por nombre. Por defecto retorna 'dark'."""
    return THEMES.get(name.lower(), THEMES["dark"])


def generate_css(theme: ThemeColors) -> str:
    """Genera CSS dinámico basado en el tema."""
    return f"""
<style>
.slide {{
  padding: 32px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, {theme.background_start} 0%, {theme.background_end} 100%);
  color: {theme.text};
  min-height: 400px;
}}
.slide h1 {{
  font-size: 2.2rem;
  margin-bottom: 16px;
  color: {theme.primary};
}}
.slide h2 {{
  font-size: 1.6rem;
  margin-bottom: 12px;
  background: linear-gradient(90deg, {theme.primary}, {theme.secondary});
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.slide p {{
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 12px;
}}
.slide ul, .slide ol {{
  margin-left: 24px;
  margin-bottom: 16px;
}}
.slide li {{
  margin-bottom: 8px;
  line-height: 1.5;
}}
.badge {{
  display: inline-block;
  padding: 4px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 20px;
  background: {theme.badge_bg};
  color: {theme.badge_text};
  margin-bottom: 12px;
}}
.highlight {{
  color: {theme.secondary};
  font-weight: 600;
}}
.stats {{
  display: flex;
  gap: 32px;
  margin: 24px 0;
}}
.stat-value {{
  font-size: 2.5rem;
  font-weight: 700;
  color: {theme.primary};
}}
.stat-label {{
  font-size: 0.9rem;
  color: {theme.text_muted};
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}}
.card {{
  background: rgba(255,255,255,0.05);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
}}
.card-title {{
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: {theme.primary};
}}
.card-desc {{
  font-size: 0.95rem;
  color: {theme.text_muted};
}}
.quote {{
  border-left: 4px solid {theme.primary};
  padding-left: 20px;
  font-style: italic;
  margin: 20px 0;
  color: {theme.text_muted};
}}
.code {{
  background: rgba(0,0,0,0.3);
  padding: 16px;
  border-radius: 8px;
  font-family: monospace;
  overflow-x: auto;
}}
.slide-image {{
  margin: 20px 0;
  text-align: center;
}}
.slide-image img {{
  max-width: 100%;
  max-height: 300px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}}
.image-caption {{
  font-size: 0.9rem;
  color: {theme.text_muted};
  margin-top: 12px;
  text-align: center;
  font-style: italic;
}}
.slide.with-image {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: center;
}}
.slide.with-image .slide-image {{
  margin: 0;
}}
</style>
"""


def detect_theme_from_topic(topic: str) -> str:
    """
    Detecta un tema apropiado basado en el tema de la presentación.
    """
    topic_lower = topic.lower()
    
    # Mapeo de palabras clave a temas
    keyword_themes = {
        "eco": ["energía", "renovable", "sostenib", "verde", "ecolog", "ambiente", "clima", "carbon"],
        "tech": ["tecnolog", "ia", "inteligencia artificial", "software", "digital", "innova", "futuro", "robot"],
        "corporate": ["negocio", "empresa", "corporat", "financ", "inversi", "estrateg", "mercado"],
        "ocean": ["agua", "mar", "océano", "marine", "azul"],
        "warm": ["energía", "fuego", "pasión", "creativ", "arte", "diseño"],
    }
    
    for theme, keywords in keyword_themes.items():
        if any(kw in topic_lower for kw in keywords):
            return theme
    
    return "dark"  # Tema por defecto
