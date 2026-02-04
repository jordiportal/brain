"""
Temas dinámicos para presentaciones.

Cada tema define colores, gradientes y estilos que se aplican
al CSS generado. Soporta tanto temas predefinidos como colores
personalizados definidos por el diseñador.
"""

import re
from dataclasses import dataclass
from typing import Dict, Optional, Any


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


def is_valid_color(color: str) -> bool:
    """Valida que un string sea un color hex válido o rgba."""
    if not color:
        return False
    # Hex color
    if re.match(r'^#[0-9A-Fa-f]{3,8}$', color):
        return True
    # rgba
    if color.startswith('rgba(') and color.endswith(')'):
        return True
    return False


def create_custom_theme(colors: Dict[str, str], base_theme: str = "dark") -> ThemeColors:
    """
    Crea un tema personalizado a partir de colores proporcionados.
    
    Args:
        colors: Diccionario con colores personalizados. Campos opcionales:
            - primary: Color principal
            - secondary: Color secundario  
            - background_start: Inicio del gradiente de fondo
            - background_end: Fin del gradiente de fondo
            - text: Color de texto principal
            - text_muted: Color de texto secundario
        base_theme: Tema base del que heredar colores no especificados
    
    Returns:
        ThemeColors con los colores personalizados aplicados
    """
    base = THEMES.get(base_theme, THEMES["dark"])
    
    # Extraer colores válidos
    primary = colors.get("primary", base.primary)
    secondary = colors.get("secondary", base.secondary)
    bg_start = colors.get("background_start", colors.get("bg_start", base.background_start))
    bg_end = colors.get("background_end", colors.get("bg_end", base.background_end))
    text = colors.get("text", base.text)
    text_muted = colors.get("text_muted", base.text_muted)
    
    # Validar colores
    if not is_valid_color(primary):
        primary = base.primary
    if not is_valid_color(secondary):
        secondary = base.secondary
    if not is_valid_color(bg_start):
        bg_start = base.background_start
    if not is_valid_color(bg_end):
        bg_end = base.background_end
    if not is_valid_color(text):
        text = base.text
    if not is_valid_color(text_muted):
        text_muted = base.text_muted
    
    # Generar badge colors basados en primary
    badge_bg = f"rgba({_hex_to_rgb(primary)}, 0.2)" if is_valid_color(primary) else base.badge_bg
    badge_text = secondary if is_valid_color(secondary) else base.badge_text
    
    return ThemeColors(
        primary=primary,
        secondary=secondary,
        background_start=bg_start,
        background_end=bg_end,
        text=text,
        text_muted=text_muted,
        badge_bg=badge_bg,
        badge_text=badge_text
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convierte #RRGGBB a 'R, G, B'."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except:
        return "233, 69, 96"  # Fallback


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
    """Genera CSS dinámico basado en el tema con layouts modernos."""
    return f"""
<style>
/* === RESET Y BASE === */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

/* === SLIDE BASE === */
.slide {{
  padding: 60px;
  margin-bottom: 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, {theme.background_start} 0%, {theme.background_end} 100%);
  color: {theme.text};
  min-height: 500px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}}

/* Fondo con gradiente sutil */
.slide::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse at top right, rgba({_hex_to_rgb(theme.primary)}, 0.15), transparent 50%),
              radial-gradient(ellipse at bottom left, rgba({_hex_to_rgb(theme.secondary)}, 0.1), transparent 50%);
  pointer-events: none;
}}

.slide > * {{ position: relative; z-index: 1; }}

/* === TIPOGRAFÍA === */
.slide h1 {{
  font-size: 3rem;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-bottom: 20px;
  background: linear-gradient(135deg, {theme.text} 0%, {theme.text_muted} 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

.slide h2 {{
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 24px;
  color: {theme.text};
}}

.slide h3 {{
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: {theme.text};
}}

.slide p {{
  font-size: 1.1rem;
  line-height: 1.7;
  color: {theme.text_muted};
  max-width: 600px;
}}

.subtitle {{
  font-size: 1.4rem;
  color: {theme.text_muted};
  margin-top: 12px;
}}

/* === BADGE === */
.badge {{
  display: inline-block;
  padding: 8px 16px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  background: linear-gradient(135deg, {theme.primary}, {theme.secondary});
  color: white;
  border-radius: 100px;
  margin-bottom: 20px;
}}

/* === SLIDE TITLE (PORTADA) === */
.slide-title {{
  text-align: center;
  align-items: center;
}}

.slide-title h1 {{
  font-size: 3.5rem;
}}

.slide-title .title-image {{
  margin-top: 32px;
}}

.slide-title .title-image img {{
  max-height: 200px;
  border-radius: 16px;
}}

/* === SLIDE SPLIT === */
.slide-split {{
  flex-direction: row;
  gap: 60px;
  padding: 40px 60px;
}}

.split-content {{
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}

.split-visual {{
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.split-visual img {{
  max-width: 100%;
  max-height: 400px;
  object-fit: cover;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4);
}}

/* === FEATURES/BULLETS === */
.features {{
  list-style: none;
  margin-top: 24px;
}}

.features li {{
  font-size: 1.05rem;
  color: {theme.text};
  padding: 12px 0;
  padding-left: 28px;
  position: relative;
  line-height: 1.5;
}}

.features li::before {{
  content: '→';
  position: absolute;
  left: 0;
  color: {theme.primary};
  font-weight: bold;
}}

/* === CARDS === */
.slide-cards {{
  padding: 50px 60px;
}}

.cards-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
  margin-top: 32px;
}}

.card {{
  background: rgba(255,255,255,0.05);
  padding: 32px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.1);
  transition: all 0.3s ease;
}}

.card:hover {{
  transform: translateY(-4px);
  border-color: {theme.primary};
  box-shadow: 0 20px 40px rgba({_hex_to_rgb(theme.primary)}, 0.15);
}}

.card-icon {{
  font-size: 2.5rem;
  margin-bottom: 16px;
}}

.card h3 {{
  font-size: 1.2rem;
  margin-bottom: 8px;
  color: {theme.text};
}}

.card p {{
  font-size: 0.95rem;
  color: {theme.text_muted};
  max-width: none;
}}

/* === STATS === */
.slide-stats {{
  text-align: center;
}}

.stats-grid {{
  display: flex;
  justify-content: center;
  gap: 60px;
  margin-top: 40px;
}}

.stat {{
  text-align: center;
}}

.stat-number {{
  display: block;
  font-size: 3.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, {theme.primary}, {theme.secondary});
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}}

.stat-label {{
  display: block;
  font-size: 1rem;
  color: {theme.text_muted};
  margin-top: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}}

/* === QUOTE === */
.slide-quote {{
  text-align: center;
  padding: 80px;
}}

.slide-quote blockquote {{
  max-width: 800px;
  margin: 0 auto;
}}

.slide-quote p {{
  font-size: 1.8rem;
  font-style: italic;
  line-height: 1.5;
  color: {theme.text};
  max-width: none;
}}

.slide-quote footer {{
  margin-top: 32px;
}}

.slide-quote cite {{
  display: block;
  font-size: 1.2rem;
  font-weight: 600;
  font-style: normal;
  color: {theme.text};
}}

/* === TIMELINE === */
.timeline {{
  display: flex;
  justify-content: space-between;
  margin-top: 48px;
  position: relative;
}}

.timeline::before {{
  content: '';
  position: absolute;
  top: 20px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, {theme.primary}, {theme.secondary});
}}

.timeline-item {{
  flex: 1;
  text-align: center;
  padding: 0 16px;
}}

.timeline-year {{
  display: inline-block;
  padding: 10px 20px;
  background: {theme.primary};
  color: white;
  font-weight: 700;
  border-radius: 100px;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}}

.timeline-item h3 {{
  font-size: 1.1rem;
  margin-bottom: 8px;
}}

.timeline-item p {{
  font-size: 0.9rem;
  max-width: none;
}}

/* === IMAGEN EN SLIDE === */
.slide-image {{
  margin: 24px 0;
  text-align: center;
}}

.slide-image img {{
  max-width: 100%;
  max-height: 300px;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.3);
}}

/* === ANIMACIONES === */
@keyframes fadeInUp {{
  from {{ opacity: 0; transform: translateY(20px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.slide h1, .slide h2 {{ animation: fadeInUp 0.6s ease-out; }}
.slide p, .slide .badge {{ animation: fadeInUp 0.6s ease-out 0.1s both; }}
.card {{ animation: fadeInUp 0.5s ease-out; }}
.card:nth-child(2) {{ animation-delay: 0.1s; }}
.card:nth-child(3) {{ animation-delay: 0.2s; }}
.stat {{ animation: fadeInUp 0.6s ease-out; }}
.stat:nth-child(2) {{ animation-delay: 0.1s; }}
.stat:nth-child(3) {{ animation-delay: 0.2s; }}
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
