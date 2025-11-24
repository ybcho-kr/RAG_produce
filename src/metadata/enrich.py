import re
from typing import List, Optional

from schema.validators import ChildChunk, DocumentBlocks, Metadata, ParentChunk, validate_child, validate_parent


TAG_RE = re.compile(r"\b(finance|legal|engineering|research)\b", re.IGNORECASE)


def _extract_title(doc: DocumentBlocks) -> Optional[str]:
    if doc.title:
        return doc.title
    for block in doc.blocks:
        if block.type == "heading" and block.level == 1:
            return block.text
    return None


def _section_path(section_path: List[str]) -> List[str]:
    return [s for s in section_path if s]


def _domain_tags(text: str) -> Optional[List[str]]:
    matches = TAG_RE.findall(text)
    if matches:
        unique = []
        for m in matches:
            val = m.lower()
            if val not in unique:
                unique.append(val)
        return unique
    return None


def enrich_parent_metadata(
    doc: DocumentBlocks,
    *,
    block_ids: List[str],
    text: str,
    section_path: List[str],
    page_range: Optional[tuple],
    anchor: str,
) -> ParentChunk:
    parent_id = doc.doc_id if anchor == "root" else f"{doc.doc_id}-{anchor}"
    metadata = Metadata(
        doc_id=doc.doc_id,
        parent_id=None,
        chunk_id=None,
        source_type=doc.source_type,
        title=_extract_title(doc),
        section_path=_section_path(section_path),
        chunk_role="parent",
        page_no=page_range[0] if page_range else None,
        slide_no=page_range[0] if (page_range and doc.source_type in {"ppt", "pptx"}) else None,
        bbox=None,
        created_at=None,
        updated_at=None,
        version=None,
        domain_tags=_domain_tags(text) or _domain_tags(doc.title or ""),
        page_range=page_range,
    )
    parent = ParentChunk(
        parent_id=parent_id,
        doc_id=doc.doc_id,
        title=_extract_title(doc),
        section_path=_section_path(section_path),
        text=text,
        block_ids=block_ids,
        page_range=page_range,
        metadata=metadata,
    )
    return validate_parent(parent)


def enrich_child_metadata(
    doc: DocumentBlocks,
    *,
    parent: ParentChunk,
    text: str,
    start_block: str,
    end_block: str,
    order: int,
    chunk_id: str,
    late_chunking: bool,
    semantic_chunking: bool,
) -> ChildChunk:
    metadata = Metadata(
        doc_id=doc.doc_id,
        parent_id=parent.parent_id,
        chunk_id=chunk_id,
        source_type=doc.source_type,
        title=_extract_title(doc),
        section_path=parent.section_path,
        chunk_role="child",
        page_no=parent.metadata.page_no,
        slide_no=parent.metadata.slide_no,
        bbox=None,
        created_at=None,
        updated_at=None,
        version=None,
        domain_tags=_domain_tags(text),
        page_range=parent.metadata.page_range,
    )
    # 출처를 보존하기 위해 태그에 플래그를 인코딩
    if metadata.domain_tags is None:
        metadata.domain_tags = []
    metadata.domain_tags.extend(
        [flag for flag, active in [("late_chunking", late_chunking), ("semantic_chunking", semantic_chunking)] if active]
    )
    child = ChildChunk(
        chunk_id=chunk_id,
        parent_id=parent.parent_id,
        doc_id=doc.doc_id,
        text=text,
        start_block=start_block,
        end_block=end_block,
        order=order,
        metadata=metadata,
    )
    return validate_child(child)
