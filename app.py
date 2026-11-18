"""Content Repurposing Pipeline: one transcript in, a full publishing package out.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from pipeline.config import get_settings
from pipeline.export import load_demo_package, to_markdown, to_text
from pipeline.generator import GenerationError, generate_package
from pipeline.models import X_POST_LIMIT, ContentPackage
from pipeline.transcript import TranscriptError, load_sample, read_upload

st.set_page_config(page_title="Content Repurposing Pipeline", layout="wide")
settings = get_settings()

state = st.session_state
state.setdefault("transcript", "")
state.setdefault("package", None)
state.setdefault("input_error", None)
state.setdefault("demo_notice", False)


def use_sample() -> None:
    state.transcript = load_sample()
    state.input_error = None


def use_upload() -> None:
    uploaded = state.upload
    if uploaded is None:
        return
    try:
        state.transcript = read_upload(uploaded.name, uploaded.getvalue())
        state.input_error = None
    except TranscriptError as exc:
        state.input_error = str(exc)


def copyable(text: str) -> None:
    """Show text in a block with a copy button, wrapped so nothing runs off the side."""
    st.code(text, language=None, wrap_lines=True)


def show_package(package: ContentPackage) -> None:
    markdown_column, text_column = st.columns(2)
    markdown_column.download_button(
        "Download all as Markdown", to_markdown(package), file_name="content_package.md", mime="text/markdown", width="stretch"
    )
    text_column.download_button(
        "Download all as text", to_text(package), file_name="content_package.txt", mime="text/plain", width="stretch"
    )

    titles, description, shorts, linkedin, thread = st.tabs(
        ["Titles", "Description", "Shorts scripts", "LinkedIn post", "X thread"]
    )
    with titles:
        for title in package.titles:
            copyable(title)
            st.caption(f"{len(title)} characters")
    with description:
        copyable(package.description)
    with shorts:
        for number, short in enumerate(package.shorts, start=1):
            with st.container(border=True):
                st.markdown(f"**Short {number}: {short.title}**")
                st.caption(f"Hook: {short.hook}")
                copyable(short.script)
                st.caption(f"{len(short.script.split())} words · Caption: {short.caption}")
    with linkedin:
        copyable(package.linkedin_post)
        st.caption(f"{len(package.linkedin_post.split())} words")
    with thread:
        for number, post in enumerate(package.x_thread, start=1):
            copyable(post)
            over = " (over the limit, shorten before posting)" if len(post) > X_POST_LIMIT else ""
            st.caption(f"Post {number} of {len(package.x_thread)} · {len(post)}/{X_POST_LIMIT} characters{over}")


# ----------------------------------------------------------------- sidebar --
with st.sidebar:
    st.subheader("Generation engine")
    has_api_key = settings.provider is not None
    demo_mode = st.toggle(
        "Demo Mode (no API key)",
        value=not has_api_key,
        disabled=not has_api_key,
        help="Shows a saved example package for the sample transcript instead of calling an AI model.",
    )
    if demo_mode:
        st.caption(
            "Demo Mode is on: the sample transcript returns a saved example package. "
            "Add an API key to `.env` to generate from your own transcripts."
        )
    else:
        st.caption(f"AI Mode: {settings.provider.title()}, model `{settings.model}`.")

    st.divider()
    st.subheader("What you get")
    st.caption(
        "5 YouTube titles, a description with chapters, 3 Shorts scripts, "
        "a LinkedIn post and an X thread, all drawn from what was said in the video."
    )

# -------------------------------------------------------------------- main --
st.title("Content Repurposing Pipeline")
st.caption("Paste one transcript and get everything needed to publish and promote the video.")

input_column, output_column = st.columns([2, 3], gap="large")

with input_column:
    st.subheader("Transcript")
    st.button("Load sample podcast transcript", on_click=use_sample)
    st.file_uploader("Or upload a .txt or .srt file", type=["txt", "srt"], key="upload", on_change=use_upload)
    if state.input_error:
        st.error(state.input_error)
    st.text_area(
        "Video script or transcript",
        key="transcript",
        height=380,
        placeholder="Paste a video script or transcript here...",
    )
    word_count = len(state.transcript.split())
    st.caption(f"{word_count:,} words")
    generate = st.button("Generate Content Package", type="primary", disabled=word_count == 0)

if generate:
    state.demo_notice = False
    if demo_mode:
        if state.transcript.strip() == load_sample().strip():
            state.package = load_demo_package()
        else:
            state.package = None
            state.demo_notice = True
    else:
        try:
            with output_column, st.spinner("Writing the content package. This can take up to a minute."):
                state.package = generate_package(settings, state.transcript.strip())
        except GenerationError as exc:
            state.package = None
            output_column.error(str(exc))

with output_column:
    st.subheader("Content package")
    if state.demo_notice:
        st.warning(
            "Demo Mode only has an example for the sample transcript. To generate a package from this "
            "transcript, add an Anthropic, OpenAI or Gemini API key to the `.env` file and restart the app."
        )
    if state.package is not None:
        if demo_mode:
            st.caption("Saved example output for the sample transcript.")
        show_package(state.package)
    elif not state.demo_notice:
        st.caption("Nothing generated yet. Load the sample transcript or paste your own, then click Generate Content Package.")
