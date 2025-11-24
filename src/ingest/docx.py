from pathlib import Path
from typing import Optional

from ingest.loader import DocumentBuilder, NoiseCleaner
from schema.validators import DocumentBlocks


def parse_docx(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    doc_id = doc_id or (path.stem if path else "docx")
    lines = NoiseCleaner.clean_lines(content.splitlines())
    builder = DocumentBuilder(source_type="docx", title=None)
    order = 0
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("Heading:"):
            order += 1
            builder.add_block(doc_id, "heading", text.replace("Heading:", "").strip(), order, level=1)
            continue
        if text.startswith("List:"):
            order += 1
            builder.add_block(doc_id, "list_item", text.replace("List:", "").strip(), order)
            continue
        if text.startswith("Table:"):
            order += 1
            table_row = text.replace("Table:", "").strip()
            builder.add_block(doc_id, "table", table_row, order, table_json={"rows": [table_row.split(",")]})
            continue
        if text.startswith("Figure:"):
            order += 1
            builder.add_block(doc_id, "figure", None, order, figure_caption=text.replace("Figure:", "").strip())
            continue
        builder.add_block(doc_id, "paragraph", text, order := order + 1)
    return builder.build(doc_id)


def parse_doc(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    # doc 형식에서도 docx 로직을 재사용
    return parse_docx(content, path, doc_id or (path.stem if path else "doc"))
