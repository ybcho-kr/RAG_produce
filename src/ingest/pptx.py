from pathlib import Path
from typing import Optional

from ingest.loader import DocumentBuilder, NoiseCleaner
from schema.validators import DocumentBlocks


SLIDE_DELIM = "--- slide ---"


def parse_pptx(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    doc_id = doc_id or (path.stem if path else "pptx")
    lines = NoiseCleaner.clean_lines(content.splitlines())
    builder = DocumentBuilder(source_type="pptx", title=None)
    order = 0
    slide_no = 0
    for line in lines:
        if line.strip().lower() == SLIDE_DELIM:
            slide_no += 1
            continue
        text = line.strip()
        if not text:
            continue
        if text.startswith("Title:"):
            order += 1
            builder.add_block(
                doc_id, "heading", text.replace("Title:", "").strip(), order, level=1, page_no=slide_no or 1
            )
            continue
        if text.startswith("Bullet:"):
            order += 1
            builder.add_block(doc_id, "list_item", text.replace("Bullet:", "").strip(), order, page_no=slide_no or 1)
            continue
        if text.startswith("Table:"):
            order += 1
            row = text.replace("Table:", "").strip()
            builder.add_block(
                doc_id,
                "table",
                row,
                order,
                table_json={"rows": [row.split(",")]},
                page_no=slide_no or 1,
            )
            continue
        builder.add_block(doc_id, "paragraph", text, order := order + 1, page_no=slide_no or 1)
    return builder.build(doc_id)


def parse_ppt(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    return parse_pptx(content, path, doc_id or (path.stem if path else "ppt"))
