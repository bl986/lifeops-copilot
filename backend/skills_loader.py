from pathlib import Path

def load_agent_skills() -> str:
    """Loads all markdown-based agent skills from the backend/skills directory."""
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.exists():
        return ""
    
    loaded_skills = ""
    for skill_file in skills_dir.glob("*.md"):
        content = skill_file.read_text(encoding="utf-8")
        loaded_skills += f"\n\n=== Active Skill: {skill_file.stem} ===\n{content}"
    
    return loaded_skills
