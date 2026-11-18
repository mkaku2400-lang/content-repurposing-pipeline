"""The content package produced from one transcript."""

from __future__ import annotations

from pydantic import BaseModel, Field

X_POST_LIMIT = 280


class ShortScript(BaseModel):
    title: str = Field(description="Working title of the short, for the editor.")
    hook: str = Field(description="The first line spoken, which must make sense with no context.")
    script: str = Field(description="The full spoken script including the hook, 80 to 110 words (30 to 45 seconds).")
    caption: str = Field(description="The post caption, one or two sentences.")


class ContentPackage(BaseModel):
    titles: list[str] = Field(description="Exactly 5 YouTube titles, each 70 characters or fewer.")
    description: str = Field(
        description="YouTube description: a two or three sentence summary that leads with the main search terms, "
        "then the chapters, then the key points. Plain text with line breaks."
    )
    shorts: list[ShortScript] = Field(description="Exactly 3 short-form scripts, each built on a different moment.")
    linkedin_post: str = Field(description="A LinkedIn post of 120 to 200 words, plain text with line breaks.")
    x_thread: list[str] = Field(description="An X thread of 5 to 8 posts, each 280 characters or fewer.")
