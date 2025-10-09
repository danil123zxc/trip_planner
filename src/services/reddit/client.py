"""Reddit search tooling wired up for asynchronous LangChain agents."""
from __future__ import annotations

import re
from typing import Any, List

from langchain_core.documents import Document


def parse_reddit_results(payload: Any) -> List[Document]:
    """Normalise the Reddit string payload into Documents for downstream tools."""

    post_pattern = re.compile(
        r"""
        Post\ Title:\s*(?P<title>.*?)\n
        \s*User:\s*(?P<user>.*?)\n
        \s*Subreddit:\s*(?P<subreddit>.*?)\s*:?\s*\n
        \s*Text\ body:\s*(?P<body>.*?)
        \s*Post\ URL:\s*(?P<url>\S+)\n
        \s*Post\ Category:\s*(?P<category>.*?)\.\s*\n
        \s*Score:\s*(?P<score>\d+)
        """,
        re.DOTALL | re.VERBOSE,
    )

    text = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload
    if not isinstance(text, str):
        return []

    documents: List[Document] = []
    for match in post_pattern.finditer(text):
        title = match.group("title").strip().strip("'\"")
        user = match.group("user").strip()
        subreddit = match.group("subreddit").strip().rstrip(":")
        body = match.group("body").strip()
        url = match.group("url").strip()
        category = match.group("category").strip()
        score = match.group("score").strip()

        page_content = f"{title}\n\n{body}".strip() or url
        page_content = re.sub(r"https?://\S+", "", page_content)

        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source": "reddit",
                    "title": title,
                    "url": url,
                    "subreddit": subreddit,
                    "author": user,
                    "category": category,
                    "score": int(score) if score.isdigit() else None,
                },
            )
        )
    return documents

