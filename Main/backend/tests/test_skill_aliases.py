"""Phase 1 (P1.4) — skill alias expansion."""

from __future__ import annotations

import pytest

from app.utils.skill_normalization import normalize_skill


# Each entry: (input, expected canonical form)
EXISTING_ALIASES = [
    ("ml", "machine learning"),
    ("k8s", "kubernetes"),
    ("nodejs", "node.js"),
    ("powerbi", "power bi"),
    ("c++", "cpp"),
    ("c#", "csharp"),
]

NEW_ALIASES = [
    ("type script", "typescript"),
    ("java-script", "javascript"),
    ("html5", "html"),
    ("css3", "css"),
    ("es6", "javascript"),
    ("j2ee", "java"),
    ("nextjs", "next.js"),
    ("nestjs", "nest.js"),
    ("mssql", "sql server"),
    ("t-sql", "sql"),
    ("plsql", "sql"),
    ("no sql", "nosql"),
    ("asp.net", "dotnet"),
    (".net core", "dotnet"),
    ("apache spark", "spark"),
    ("py spark", "pyspark"),
    ("apache hadoop", "hadoop"),
    ("apache kafka", "kafka"),
    ("tensor-flow", "tensorflow"),
    ("tailwindcss", "tailwind css"),
    ("open ai", "openai"),
    ("lang chain", "langchain"),
    ("llm", "large language models"),
    ("rag", "retrieval augmented generation"),
    ("genai", "generative ai"),
    ("k8", "kubernetes"),
    ("elk", "elasticsearch"),
    ("amazon s3", "aws"),
    ("ddb", "dynamodb"),
]


@pytest.mark.parametrize("raw,expected", EXISTING_ALIASES)
def test_existing_aliases_still_resolve(raw: str, expected: str) -> None:
    assert normalize_skill(raw) == expected


@pytest.mark.parametrize("raw,expected", NEW_ALIASES)
def test_new_aliases_resolve(raw: str, expected: str) -> None:
    assert normalize_skill(raw) == expected


def test_unknown_skill_passes_through_lowercased(self=None) -> None:
    # Whatever the input, an unknown skill returns the lowercase strip.
    assert normalize_skill("Selenium") == "selenium"
    assert normalize_skill("  Rust  ") == "rust"
