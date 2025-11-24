from pathlib import Path
from typing import Optional

from ingest.loader import DocumentBuilder, NoiseCleaner
from schema.validators import DocumentBlocks


def parse_pdf(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    doc_id = doc_id or (path.stem if path else "pdf")
    lines = NoiseCleaner.clean_lines(content.splitlines())
    builder = DocumentBuilder(source_type="pdf", title=None)
    order = 0
    for idx, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        if text.upper() == text and len(text.split()) <= 6:
            order += 1
            builder.add_block(doc_id, "heading", text, order, level=1, page_no=idx + 1)
            continue
        if "|" in text:
            order += 1
            builder.add_block(
                doc_id,
                "table",
                text,
                order,
                table_json={"rows": [text.split("|")]},
                page_no=idx + 1,
            )
            continue
        if text.startswith("Code:"):
            order += 1
            builder.add_block(doc_id, "code", text.replace("Code:", "").strip(), order, page_no=idx + 1)
            continue
        if text.lower().startswith("figure"):
            order += 1
            builder.add_block(doc_id, "figure", None, order, page_no=idx + 1, figure_caption=text)
            continue
        if "$" in text:
            order += 1
            builder.add_block(doc_id, "equation", text, order, page_no=idx + 1)
            continue
        order += 1
        builder.add_block(doc_id, "paragraph", text, order, page_no=idx + 1)
    return builder.build(doc_id)
