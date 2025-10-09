import re
from typing import List
from langchain_core.documents import Document

def process_pages(docs: List[Document]) -> List[Document]:
    """Clean Tavily documents by stripping links and noisy whitespace."""

    cleaned_docs: List[Document] = []
    for doc in docs:
        if not doc.page_content:
            continue
        text = doc.page_content
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)
        text = re.sub(r"\n{2,}", "\n\n", text)
        text = re.sub(r"[ \t\u00a0]{2,}", " ", text)
        text = text.replace("\r", "")
        text = text.strip()
        if len(text) > 50:
            doc.page_content = text
            cleaned_docs.append(doc)
    return cleaned_docs

