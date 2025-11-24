import re
from typing import Dict, List, Optional, Tuple

from metadata.enrich import enrich_child_metadata, enrich_parent_metadata
from schema.validators import ChildChunk, DocumentBlocks, ParentChunk, make_chunk_id, make_parent_id, token_count


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> List[str]:
    parts = [p.strip() for p in SENTENCE_SPLIT.split(text) if p.strip()]
    return parts if parts else [text]


def build_parents(doc: DocumentBlocks) -> List[ParentChunk]:
    parents: List[ParentChunk] = []
    current_blocks: List[str] = []
    current_text: List[str] = []
    current_section: List[str] = []
    page_range: List[int] = []
    parent_anchor = "root"
    for block in doc.blocks:
        if block.type == "heading" and block.level in {1, 2}:
            if current_blocks:
                parents.append(
                    enrich_parent_metadata(
                        doc,
                        block_ids=current_blocks,
                        text="\n".join(current_text),
                        section_path=current_section,
                        page_range=(min(page_range), max(page_range)) if page_range else None,
                        anchor=parent_anchor,
                    )
                )
                current_blocks, current_text, page_range = [], [], []
            current_section = current_section[: block.level - 1] + [block.text or ""]
            parent_anchor = block.text or f"section-{len(parents)+1}"
            continue
        current_blocks.append(block.block_id)
        page_range.append(block.page_no or 1)
        if block.text:
            current_text.append(block.text)
    if current_blocks:
        parents.append(
            enrich_parent_metadata(
                doc,
                block_ids=current_blocks,
                text="\n".join(current_text),
                section_path=current_section,
                page_range=(min(page_range), max(page_range)) if page_range else None,
                anchor=parent_anchor,
            )
        )
    return parents


def _chunk_text_blocks(text_blocks: List[Tuple[str, str]], target_min: int = 200, target_max: int = 500) -> List[List[Tuple[str, str]]]:
    chunks: List[List[Tuple[str, str]]] = []
    current: List[Tuple[str, str]] = []
    current_tokens = 0
    for block_id, text in text_blocks:
        block_tokens = token_count(text)
        if not current:
            current.append((block_id, text))
            current_tokens = block_tokens
            continue
        if current_tokens + block_tokens <= target_max:
            current.append((block_id, text))
            current_tokens += block_tokens
        else:
            if current_tokens < target_min:
                current.append((block_id, text))
                current_tokens += block_tokens
            else:
                chunks.append(current)
                current = [(block_id, text)]
                current_tokens = block_tokens
    if current:
        chunks.append(current)
    return chunks


def build_children(
    doc: DocumentBlocks,
    parents: List[ParentChunk],
    *,
    target_min_tokens: int = 200,
    target_max_tokens: int = 500,
    late_chunking: bool = False,
    semantic_chunking: bool = False,
) -> List[ChildChunk]:
    children: List[ChildChunk] = []
    for parent in parents:
        text_blocks: List[Tuple[str, str]] = []
        for block in doc.blocks:
            if block.block_id in parent.block_ids and block.text:
                text_blocks.append((block.block_id, block.text))
        if semantic_chunking:
            text_blocks = _semantic_reorder(text_blocks)
        block_groups = _chunk_text_blocks(text_blocks, target_min_tokens, target_max_tokens)
        for order, group in enumerate(block_groups):
            text = " ".join([g[1] for g in group])
            chunk_id = make_chunk_id(parent.parent_id, order, text)
            child = enrich_child_metadata(
                doc,
                parent=parent,
                text=text,
                start_block=group[0][0],
                end_block=group[-1][0],
                order=order,
                chunk_id=chunk_id,
                late_chunking=late_chunking,
                semantic_chunking=semantic_chunking,
            )
            children.append(child)
    return children


def _semantic_reorder(blocks: List[Tuple[str, str]]):
    # heuristic: longer sentences first to simulate semantic grouping
    return sorted(blocks, key=lambda x: -len(x[1]))


def chunk_document(
    doc: DocumentBlocks,
    *,
    target_min_tokens: int = 200,
    target_max_tokens: int = 500,
    late_chunking: bool = False,
    semantic_chunking: bool = False,
) -> Tuple[List[ParentChunk], List[ChildChunk]]:
    parents = build_parents(doc)
    children = build_children(
        doc,
        parents,
        target_min_tokens=target_min_tokens,
        target_max_tokens=target_max_tokens,
        late_chunking=late_chunking,
        semantic_chunking=semantic_chunking,
    )
    return parents, children
