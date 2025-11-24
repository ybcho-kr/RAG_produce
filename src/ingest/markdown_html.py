import re
from pathlib import Path
from typing import Optional

from ingest.loader import DocumentBuilder, NoiseCleaner
from schema.validators import DocumentBlocks


HEADING_RE = re.compile(r"^(?P<level>#+)\s+(?P<text>.+)")
LIST_RE = re.compile(r"^[-*+]\s+")
TABLE_RE = re.compile(r"\|.+\|")
CODE_FENCE = "```"


def _parse_common(content: str, doc_id: str, source_type: str, title: Optional[str]) -> DocumentBlocks:
    lines = NoiseCleaner.clean_lines(content.splitlines())
    builder = DocumentBuilder(source_type=source_type, title=title)
    in_code = False
    buffer: list[str] = []
    order = 0
    code_start = None
    for line in lines:
        if line.strip().startswith(CODE_FENCE):
            if in_code:
                order += 1
                builder.add_block(
                    doc_id=doc_id,
                    btype="code",
                    text="\n".join(buffer),
                    order=order,
                )
                buffer = []
                in_code = False
                continue
            else:
                in_code = True
                buffer = []
                code_start = order
                continue
        if in_code:
            buffer.append(line)
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match:
            order += 1
            level = len(heading_match.group("level"))
            text = heading_match.group("text").strip()
            builder.add_block(doc_id, "heading", text, order, level=level)
            continue
        if TABLE_RE.search(line):
            order += 1
            builder.add_block(doc_id, "table", line, order, table_json={"rows": [line.split("|")]})
            continue
        if LIST_RE.match(line):
            order += 1
            builder.add_block(doc_id, "list_item", line, order)
            continue
        if line.startswith("!["):
            order += 1
            builder.add_block(doc_id, "figure", None, order, figure_caption=line)
            continue
        if "$" in line:
            order += 1
            builder.add_block(doc_id, "equation", line, order)
            continue
        if line:
            order += 1
            builder.add_block(doc_id, "paragraph", line, order)
    return builder.build(doc_id)


def parse_markdown(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    doc_id = doc_id or (path.stem if path else "md")
    title = content.splitlines()[0].lstrip("# ") if content.strip() else None
    return _parse_common(content, doc_id, "md", title)


def parse_html(content: str, path: Optional[Path] = None, doc_id: Optional[str] = None) -> DocumentBlocks:
    doc_id = doc_id or (path.stem if path else "html")
    # 단순화: 태그를 제거하고 마크다운 로직을 재사용
    text = re.sub(r"<[^>]+>", lambda m: "\n" if m.group(0) in {"<p>", "</p>", "<br>"} else " ", content)
    return _parse_common(text, doc_id, "html", None)
