"""Export a content package as one Markdown or plain-text file."""

from __future__ import annotations

from pathlib import Path

from .models import ContentPackage

DEMO_PACKAGE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "demo_package.json"


def load_demo_package() -> ContentPackage:
    """The saved example output for the sample transcript, shown in Demo Mode."""
    return ContentPackage.model_validate_json(DEMO_PACKAGE_PATH.read_text(encoding="utf-8"))


def to_markdown(package: ContentPackage) -> str:
    parts = ["# Content Package", "## YouTube Titles"]
    parts.append("\n".join(f"{i}. {title}" for i, title in enumerate(package.titles, start=1)))
    parts += ["## YouTube Description", package.description, "## Short-Form Scripts"]
    for i, short in enumerate(package.shorts, start=1):
        parts.append(f"### Short {i}: {short.title}\n\n**Hook:** {short.hook}\n\n{short.script}\n\n**Caption:** {short.caption}")
    parts += ["## LinkedIn Post", package.linkedin_post, "## X Thread"]
    parts.append("\n\n".join(f"**{i}/{len(package.x_thread)}**\n\n{post}" for i, post in enumerate(package.x_thread, start=1)))
    return "\n\n".join(parts) + "\n"


def to_text(package: ContentPackage) -> str:
    def heading(text: str) -> str:
        return f"{text.upper()}\n{'=' * len(text)}"

    parts = [heading("YouTube Titles")]
    parts.append("\n".join(f"{i}. {title}" for i, title in enumerate(package.titles, start=1)))
    parts += [heading("YouTube Description"), package.description, heading("Short-Form Scripts")]
    for i, short in enumerate(package.shorts, start=1):
        parts.append(f"Short {i}: {short.title}\n\n{short.script}\n\nCaption: {short.caption}")
    parts += [heading("LinkedIn Post"), package.linkedin_post, heading("X Thread")]
    parts.append("\n\n".join(f"{i}/{len(package.x_thread)}\n{post}" for i, post in enumerate(package.x_thread, start=1)))
    return "\n\n".join(parts) + "\n"
