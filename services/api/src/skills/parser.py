"""
Parser for SKILL.md files following the Agent Skills standard (agentskills.io).

Extracts YAML frontmatter and markdown body from SKILL.md files and converts
them to Brain's internal skill format {id, name, description, content}.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
import structlog

logger = structlog.get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class ParsedSkill:
    """Parsed representation of a SKILL.md file."""
    name: str
    description: str
    content: str
    display_name: str = ""
    agent: str = ""
    version: str = "1.0"
    metadata: dict = field(default_factory=dict)
    source_path: Optional[str] = None

    @property
    def brain_id(self) -> str:
        """Convert hyphenated name to snake_case for Brain's internal ID."""
        return self.name.replace("-", "_")


class SkillParseError(Exception):
    """Raised when a SKILL.md file cannot be parsed."""


def parse_skill_md(text: str, source_path: Optional[str] = None) -> ParsedSkill:
    """Parse a SKILL.md string into a ParsedSkill."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillParseError(
            f"Missing YAML frontmatter in {source_path or 'SKILL.md'}"
        )

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SkillParseError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(fm, dict):
        raise SkillParseError("Frontmatter must be a YAML mapping")

    name = fm.get("name", "").strip()
    if not name:
        raise SkillParseError("Frontmatter missing required field 'name'")
    if len(name) > 64:
        raise SkillParseError(f"Name exceeds 64 characters: {name!r}")
    if not _NAME_RE.match(name):
        raise SkillParseError(
            f"Name must be lowercase alphanumeric with hyphens: {name!r}"
        )

    description = fm.get("description", "").strip()
    if not description:
        raise SkillParseError("Frontmatter missing required field 'description'")
    if len(description) > 1024:
        raise SkillParseError(
            f"Description exceeds 1024 characters ({len(description)})"
        )

    body = text[match.end():].strip()

    meta = fm.get("metadata", {}) or {}
    display_name = meta.get("display-name", name)
    agent = meta.get("agent", "")
    version = meta.get("version", "1.0")

    return ParsedSkill(
        name=name,
        description=description,
        content=body,
        display_name=display_name,
        agent=agent,
        version=version,
        metadata=meta,
        source_path=source_path,
    )


def parse_skill_file(path: Path) -> ParsedSkill:
    """Read and parse a SKILL.md from disk."""
    text = path.read_text(encoding="utf-8")
    return parse_skill_md(text, source_path=str(path))


def parse_agents_yaml(path: Path) -> dict[str, list[str]]:
    """Parse agents.yaml returning {agent_id: [skill-name, ...]}."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "agents" not in data:
        return {}

    result: dict[str, list[str]] = {}
    for agent_id, cfg in data["agents"].items():
        skills = cfg.get("skills", []) if isinstance(cfg, dict) else []
        result[agent_id] = [str(s) for s in skills]
    return result


def discover_skills(repo_root: Path) -> list[ParsedSkill]:
    """Discover and parse all SKILL.md files under repo_root/skills/."""
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        logger.warning("skills/ directory not found", path=str(repo_root))
        return []

    parsed: list[ParsedSkill] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.debug("Skipping directory without SKILL.md", dir=skill_dir.name)
            continue
        try:
            skill = parse_skill_file(skill_md)
            if skill.name != skill_dir.name:
                logger.warning(
                    "Skill name mismatch",
                    frontmatter_name=skill.name,
                    directory_name=skill_dir.name,
                )
            parsed.append(skill)
        except SkillParseError as exc:
            logger.error("Failed to parse skill", path=str(skill_md), error=str(exc))

    return parsed
