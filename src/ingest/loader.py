import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from schema.validators import (
    Block,
    DocumentBlocks,
    make_block_id,
    validate_document,
)


class NoiseCleaner:
    @staticmethod
    def clean_lines(lines: List[str]) -> List[str]:
        cleaned: List[str] = []
        footer_pattern = re.compile(r"page \d+", re.IGNORECASE)
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if footer_pattern.search(stripped):
                continue
            cleaned.append(stripped)
        return cleaned


class DocumentBuilder:
    def __init__(self, source_type: str, title: Optional[str] = None) -> None:
        self.source_type = source_type
        self.title = title
        self.blocks: List[Block] = []

    def add_block(
        self,
        doc_id: str,
        btype: str,
        text: Optional[str],
        order: int,
        level: Optional[int] = None,
        parent_id: Optional[str] = None,
        page_no: Optional[int] = None,
        bbox: Optional[List[float]] = None,
        table_json: Optional[Dict] = None,
        table_summary: Optional[str] = None,
        figure_caption: Optional[str] = None,
        figure_alt: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        block_id = make_block_id(doc_id, order, text)
        block = Block(
            block_id=block_id,
            type=btype,
            text=text,
            rich_text=text,
            level=level,
            parent_id=parent_id,
            order=order,
            page_no=page_no,
            bbox=bbox,
            table_json=table_json,
            table_summary=table_summary,
            figure_caption=figure_caption,
            figure_alt=figure_alt,
            tags=tags,
            created_at=None,
            updated_at=None,
        )
        self.blocks.append(block)

    def build(self, doc_id: str) -> DocumentBlocks:
        doc = DocumentBlocks(
            doc_id=doc_id, source_type=self.source_type, title=self.title, blocks=self.blocks
        )
        return validate_document(doc)


def compute_doc_id(path: Path, content: str) -> str:
    import hashlib

    base = f"{path.name}-{len(content)}-{path.stat().st_mtime}" if path.exists() else f"{path.name}-{len(content)}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def read_content(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() in {".json"}:
        return json.dumps(json.load(open(path)))
    return path.read_text(encoding="utf-8")


def choose_parser(extension: str):
    from ingest import markdown_html, pdf, docx, pptx

    mapping = {
        ".pdf": pdf.parse_pdf,
        ".md": markdown_html.parse_markdown,
        ".markdown": markdown_html.parse_markdown,
        ".html": markdown_html.parse_html,
        ".htm": markdown_html.parse_html,
        ".docx": docx.parse_docx,
        ".doc": docx.parse_doc,
        ".pptx": pptx.parse_pptx,
        ".ppt": pptx.parse_ppt,
    }
    return mapping.get(extension.lower())


def load_document(path: str) -> DocumentBlocks:
    p = Path(path)
    parser = choose_parser(p.suffix)
    if parser is None:
        raise ValueError(f"No parser for extension {p.suffix}")
    content = read_content(p)
    doc_id = compute_doc_id(p, content)
    doc_blocks = parser(content=content, path=p, doc_id=doc_id)
    return validate_document(doc_blocks)
