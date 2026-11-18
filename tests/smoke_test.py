"""End-to-end check of transcript loading, the demo package, export and the app. No API key needed.

Usage:  python tests/smoke_test.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from pipeline.export import load_demo_package, to_markdown, to_text  # noqa: E402
from pipeline.models import X_POST_LIMIT  # noqa: E402
from pipeline.transcript import TranscriptError, load_sample, read_upload  # noqa: E402

SRT = """1
00:00:01,000 --> 00:00:04,000
Welcome to the <i>show</i>.

2
00:00:04,500 --> 00:00:09,000
Today we talk about email lists.

3
00:00:41,000 --> 00:00:45,000
First, the clipboard.
"""


def check_transcripts() -> None:
    converted = read_upload("episode.srt", SRT.encode("utf-8"))
    assert converted == (
        "[00:01] Welcome to the show. Today we talk about email lists.\n\n[00:41] First, the clipboard."
    ), converted
    assert read_upload("notes.txt", "﻿Hello there".encode("utf-8")) == "Hello there"
    for name, data in [("empty.txt", b"   "), ("broken.srt", b"no cues here")]:
        try:
            read_upload(name, data)
            raise AssertionError(f"{name} should have been rejected")
        except TranscriptError:
            pass
    assert len(load_sample().split()) > 500
    print("  ok   .srt conversion, .txt loading, bad files rejected, sample transcript present")


def check_demo_package() -> None:
    package = load_demo_package()
    transcript = load_sample()
    assert len(package.titles) == 5 and all(len(t) <= 70 for t in package.titles), package.titles
    assert len(package.shorts) == 3 and all(80 <= len(s.script.split()) <= 110 for s in package.shorts)
    assert all(s.script.startswith(s.hook) for s in package.shorts), "each script should open with its hook"
    assert 5 <= len(package.x_thread) <= 8 and all(len(p) <= X_POST_LIMIT for p in package.x_thread)
    assert 120 <= len(package.linkedin_post.split()) <= 200, len(package.linkedin_post.split())

    # Every chapter timestamp in the description must exist in the transcript.
    stamps = re.findall(r"(?m)^(\d{2}:\d{2}) ", package.description)
    assert len(stamps) >= 5 and all(f"[{s}]" in transcript for s in stamps), stamps
    print(f"  ok   demo package: 5 titles, 3 shorts, {len(package.x_thread)} posts, {len(stamps)} chapters match the transcript")

    markdown, text = to_markdown(package), to_text(package)
    for section in ("YouTube Titles", "YouTube Description", "Short-Form Scripts", "LinkedIn Post", "X Thread"):
        assert f"## {section}" in markdown and section.upper() in text, section
    print("  ok   Markdown and text exports contain every section")


def check_app() -> None:
    from streamlit.testing.v1 import AppTest

    # Force Demo Mode regardless of what is in the local .env file.
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GOOGLE_API_KEY"] = ""

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception, app.exception
    next(b for b in app.button if b.label.startswith("Load sample")).click().run()
    next(b for b in app.button if b.label == "Generate Content Package").click().run()
    assert not app.exception, app.exception
    assert app.session_state["package"] is not None and len(app.tabs) == 5

    app.text_area[0].set_value("A different transcript about something else.").run()
    next(b for b in app.button if b.label == "Generate Content Package").click().run()
    assert not app.exception, app.exception
    assert app.session_state["package"] is None and app.warning, "own transcript in Demo Mode should explain itself"
    print("  ok   app: sample generates the package; other text in Demo Mode shows the API key notice")


if __name__ == "__main__":
    check_transcripts()
    check_demo_package()
    check_app()
    print("All checks passed.")
