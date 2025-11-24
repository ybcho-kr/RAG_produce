import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _hash_string(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _ensure_iso(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        datetime.fromisoformat(value)
        return value
    except ValueError:
        raise ValueError(f"Timestamp not ISO8601: {value}")


def _validate_bbox(value: Optional[List[float]]) -> Optional[List[float]]:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("bbox must be a list of four floats")
    if not all(isinstance(v, (int, float)) for v in value):
        raise ValueError("bbox values must be numeric")
    return [float(v) for v in value]


def token_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


@dataclass
class Block:
    block_id: str
    type: str
    text: Optional[str]
    rich_text: Optional[str]
    level: Optional[int]
    parent_id: Optional[str]
    order: int
    page_no: Optional[int]
    bbox: Optional[List[float]]
    table_json: Optional[Dict[str, Any]]
    table_summary: Optional[str]
    figure_caption: Optional[str]
    figure_alt: Optional[str]
    tags: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]

    def validate(self) -> None:
        if not self.block_id:
            raise ValueError("block_id required")
        if self.type not in {
            "heading",
            "paragraph",
            "list_item",
            "table",
            "figure",
            "code",
            "equation",
            "footnote",
        }:
            raise ValueError(f"Invalid block type: {self.type}")
        if not isinstance(self.order, int):
            raise ValueError("order must be int")
        _validate_bbox(self.bbox)
        _ensure_iso(self.created_at)
        _ensure_iso(self.updated_at)


@dataclass
class DocumentBlocks:
    doc_id: str
    source_type: str
    title: Optional[str]
    blocks: List[Block] = field(default_factory=list)

    def validate(self) -> None:
        if not self.doc_id:
            raise ValueError("doc_id required")
        if self.source_type not in {
            "pdf",
            "md",
            "html",
            "docx",
            "doc",
            "pptx",
            "ppt",
            "txt",
            "other",
        }:
            raise ValueError(f"Invalid source_type: {self.source_type}")
        for block in self.blocks:
            block.validate()
        orders = [b.order for b in self.blocks]
        if orders != sorted(orders):
            raise ValueError("blocks must be ordered")


@dataclass
class Metadata:
    doc_id: str
    parent_id: Optional[str]
    chunk_id: Optional[str]
    source_type: str
    title: Optional[str]
    section_path: List[str]
    chunk_role: str
    page_no: Optional[int]
    slide_no: Optional[int]
    bbox: Optional[List[float]]
    created_at: Optional[str]
    updated_at: Optional[str]
    version: Optional[str]
    domain_tags: Optional[List[str]]
    page_range: Optional[Tuple[int, int]] = None

    def validate(self) -> None:
        if not self.doc_id:
            raise ValueError("doc_id required")
        if self.chunk_role not in {"parent", "child", "note"}:
            raise ValueError("chunk_role must be parent, child, or note")
        if self.source_type not in {
            "pdf",
            "md",
            "html",
            "docx",
            "doc",
            "pptx",
            "ppt",
            "txt",
            "other",
        }:
            raise ValueError(f"Invalid source_type: {self.source_type}")
        if self.section_path is None:
            raise ValueError("section_path required")
        _validate_bbox(self.bbox)
        _ensure_iso(self.created_at)
        _ensure_iso(self.updated_at)


@dataclass
class ParentChunk:
    parent_id: str
    doc_id: str
    title: Optional[str]
    section_path: List[str]
    text: str
    block_ids: List[str]
    page_range: Optional[Tuple[int, int]]
    metadata: Metadata

    def validate(self) -> None:
        if not self.parent_id:
            raise ValueError("parent_id required")
        if not self.text:
            raise ValueError("parent text required")
        if not self.block_ids:
            raise ValueError("parent must include block_ids")
        if self.metadata.chunk_role != "parent":
            raise ValueError("parent metadata chunk_role must be parent")
        self.metadata.validate()


@dataclass
class ChildChunk:
    chunk_id: str
    parent_id: str
    doc_id: str
    text: str
    start_block: str
    end_block: str
    order: int
    metadata: Metadata

    def validate(self) -> None:
        if not self.chunk_id:
            raise ValueError("chunk_id required")
        if not self.text:
            raise ValueError("child text required")
        if token_count(self.text) < 20:
            raise ValueError("child chunk too small; must contain >=20 tokens to be meaningful")
        if self.metadata.chunk_role != "child":
            raise ValueError("child metadata chunk_role must be child")
        self.metadata.validate()


def validate_document(doc: DocumentBlocks) -> DocumentBlocks:
    doc.validate()
    return doc


def validate_parent(parent: ParentChunk) -> ParentChunk:
    parent.validate()
    return parent


def validate_child(child: ChildChunk) -> ChildChunk:
    child.validate()
    return child


def make_block_id(doc_id: str, order: int, text: Optional[str]) -> str:
    base = f"{doc_id}-{order}-{text or ''}"
    return _hash_string(base)


def make_parent_id(doc_id: str, anchor: str) -> str:
    return _hash_string(f"parent-{doc_id}-{anchor}")


def make_chunk_id(parent_id: str, order: int, text: str) -> str:
    return _hash_string(f"child-{parent_id}-{order}-{text[:64]}")
