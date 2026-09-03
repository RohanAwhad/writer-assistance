import { createElement, useMemo, useRef } from "react";
import type { ReactNode } from "react";
import {
  clipMarksToSpans,
  findMarkRange,
  parseMarkdown,
  type MarkRange,
  type ParsedDoc,
} from "../lib/md";
import type { InlineNode } from "../lib/md-inline";
import { parseInline } from "../lib/md-inline";

export interface SelectionResult {
  status: "ok" | "empty" | "error";
  text: string;
  start: number | null;
  end: number | null;
  message: string | null;
}

interface MarkedSeg {
  text: string;
  marked: boolean;
}

interface MarkViewProps {
  docText: string;
  markRanges: MarkRange[];
  onSelection?: (result: SelectionResult) => void;
}

function leafSegments(node: InlineNode, marks: MarkRange[]): MarkedSeg[] {
  const rs = node.rawStart;
  const re = node.rawEnd;
  const shift = node.kind === "esc" || node.kind === "code" ? 1 : 0;
  const tail = node.kind === "esc" || node.kind === "code" ? 1 : 0;
  const visibleFrom = rs + shift;
  const visibleTo = re - tail;
  const text =
    node.kind === "text" || node.kind === "code"
      ? node.text
      : node.kind === "esc"
        ? node.char
        : "";
  const hit: MarkRange | undefined = marks.find((m) => m.start < visibleTo && m.end > visibleFrom);
  if (hit === undefined) return [{ text, marked: false }];
  const from = Math.max(hit.start, visibleFrom);
  const to = Math.min(hit.end, visibleTo);
  const vFrom = from - rs - shift;
  const vTo = to - rs - shift;
  if (vTo <= vFrom) return [{ text, marked: false }];
  const segs: MarkedSeg[] = [];
  if (vFrom > 0) segs.push({ text: text.slice(0, vFrom), marked: false });
  segs.push({ text: text.slice(vFrom, vTo), marked: true });
  if (vTo < text.length) segs.push({ text: text.slice(vTo), marked: false });
  return segs;
}

function renderLeaf(node: InlineNode, marks: MarkRange[]): ReactNode {
  return leafSegments(node, marks).map((seg, i) =>
    seg.marked ? (
      <mark key={i} className="doc-mark">
        {seg.text}
      </mark>
    ) : (
      seg.text
    ),
  );
}

function renderInlineChildren(children: InlineNode[], marks: MarkRange[]): ReactNode[] {
  return children.map((child, i) => (
    <InlineLeaf key={i} node={child} marks={marks} />
  ));
}

function InlineLeaf({ node, marks }: { node: InlineNode; marks: MarkRange[] }): ReactNode {
  switch (node.kind) {
    case "text":
      return renderLeaf(node, marks);
    case "esc":
      return renderLeaf(node, marks);
    case "code":
      return <code>{renderLeaf(node, marks)}</code>;
    case "em":
      return <em>{renderInlineChildren(node.children, marks)}</em>;
    case "strong":
      return <strong>{renderInlineChildren(node.children, marks)}</strong>;
    case "link":
      return (
        <a href={node.href} target="_blank" rel="noreferrer">
          {renderInlineChildren(node.children, marks)}
        </a>
      );
  }
}

function inlineNodes(doc: ParsedDoc, spanId: number, marksBySpan: Map<number, MarkRange[]>): ReactNode {
  const span = doc.spans[spanId];
  if (span === undefined) return null;
  const text = doc.text.slice(span.rawStart + span.marker, span.end);
  const localMarks = (marksBySpan.get(spanId) ?? []).map((m) => ({
    start: m.start - (span.rawStart + span.marker),
    end: m.end - (span.rawStart + span.marker),
  }));
  const nodes = parseInline(text);
  return renderInlineChildren(nodes, localMarks);
}

function codeNodes(doc: ParsedDoc, spanId: number, marksBySpan: Map<number, MarkRange[]>): ReactNode {
  const span = doc.spans[spanId];
  if (span === undefined) return null;
  const text = doc.text.slice(span.rawStart, span.end);
  const localMarks = (marksBySpan.get(spanId) ?? []).map((m) => ({
    start: m.start - span.rawStart,
    end: m.end - span.rawStart,
  }));
  const segs: MarkedSeg[] = [];
  const plain: MarkedSeg[] = [{ text, marked: false }];
  let cursor = 0;
  for (const m of localMarks) {
    if (m.end <= m.start) continue;
    segs.push({ text: text.slice(cursor, m.start), marked: false });
    segs.push({ text: text.slice(m.start, m.end), marked: true });
    cursor = m.end;
  }
  const parts = segs.length > 0 ? segs : plain;
  return parts.map((seg, i) =>
    seg.marked ? (
      <mark key={i} className="doc-mark">
        {seg.text}
      </mark>
    ) : (
      seg.text
    ),
  );
}

export default function MarkdownView({ docText, markRanges, onSelection }: MarkViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const doc = useMemo(() => parseMarkdown(docText), [docText]);
  const spanMarks = useMemo(() => {
    const bySpan = new Map<number, MarkRange[]>();
    for (const sm of clipMarksToSpans(doc, markRanges)) {
      const list = bySpan.get(sm.spanId) ?? [];
      let merged = false;
      for (const existing of list) {
        if (sm.range.start <= existing.end && sm.range.end >= existing.start) {
          existing.start = Math.min(existing.start, sm.range.start);
          existing.end = Math.max(existing.end, sm.range.end);
          merged = true;
          break;
        }
      }
      if (!merged) list.push({ ...sm.range });
      bySpan.set(sm.spanId, list);
    }
    return bySpan;
  }, [doc, markRanges]);

  const spanIdForNode = (node: Node): number | null => {
    let el: Element | null = node instanceof Element ? node : node.parentElement;
    while (el !== null && el !== containerRef.current) {
      const dataset = (el as HTMLElement).dataset;
      if (dataset.blk !== undefined) return Number(dataset.blk);
      el = el.parentElement;
    }
    return null;
  };

  const handleSelectionChange = (): void => {
    if (onSelection === undefined) return;
    const sel = window.getSelection();
    if (sel === null || sel.rangeCount === 0 || sel.isCollapsed) {
      onSelection({ status: "empty", text: "", start: null, end: null, message: null });
      return;
    }
    const range = sel.getRangeAt(0);
    const startNode = range.startContainer;
    const text = range.toString();
    if (!containerRef.current?.contains(startNode) || text.trim().length === 0) {
      onSelection({ status: "empty", text: "", start: null, end: null, message: null });
      return;
    }
    const spanId = spanIdForNode(startNode);
    if (spanId === null) {
      onSelection({ status: "error", text, start: null, end: null, message: "selection is outside the document" });
      return;
    }
    const span = doc.spans[spanId];
    if (span === undefined) {
      onSelection({ status: "error", text, start: null, end: null, message: "selection is outside the document" });
      return;
    }
    try {
      const match = findMarkRange(doc, text, span.rawStart + span.marker, spanId);
      onSelection({ status: "ok", text, start: match.start, end: match.end, message: null });
    } catch (err) {
      onSelection({
        status: "error",
        text,
        start: null,
        end: null,
        message: err instanceof Error ? err.message : "could not map the selection",
      });
    }
  };

  const clearSelection = (): void => {
    const sel = window.getSelection();
    sel?.removeAllRanges();
    if (onSelection !== undefined) {
      onSelection({ status: "empty", text: "", start: null, end: null, message: null });
    }
  };

  const renderBlock = (blockIndex: number): ReactNode => {
    const block = doc.blocks[blockIndex]!;
    switch (block.type) {
      case "hr":
        return <hr key={blockIndex} />;
      case "heading": {
        const level = Math.min(Math.max(block.level ?? 1, 1), 6);
        const spanId = block.spanIds[0];
        if (spanId === undefined) return null;
        const tags = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;
        const tag = tags[level - 1] ?? "h1";
        return createElement(
          tag,
          { key: blockIndex, "data-blk": spanId },
          inlineNodes(doc, spanId, spanMarks),
        );
      }
      case "paragraph": {
        const spanId = block.spanIds[0];
        if (spanId === undefined) return null;
        return (
          <p key={blockIndex} data-blk={spanId}>
            {inlineNodes(doc, spanId, spanMarks)}
          </p>
        );
      }
      case "quote":
        return (
          <blockquote key={blockIndex}>
            {block.spanIds.map((spanId) => (
              <p key={spanId} data-blk={spanId}>
                {inlineNodes(doc, spanId, spanMarks)}
              </p>
            ))}
          </blockquote>
        );
      case "list": {
        const ListTag = block.ordered === true ? "ol" : "ul";
        return (
          <ListTag key={blockIndex}>
            {block.spanIds.map((spanId) => (
              <li key={spanId} data-blk={spanId}>
                {inlineNodes(doc, spanId, spanMarks)}
              </li>
            ))}
          </ListTag>
        );
      }
      case "code": {
        const spanId = block.spanIds[0];
        if (spanId === undefined) return null;
        return (
          <pre key={blockIndex} data-blk={spanId}>
            <code>{codeNodes(doc, spanId, spanMarks)}</code>
          </pre>
        );
      }
    }
  };

  if (docText.length === 0) {
    return <div className="text-sm text-muted-foreground">This document is empty.</div>;
  }

  return (
    <div
      ref={containerRef}
      className="doc-prose select-text"
      onMouseUp={handleSelectionChange}
      onKeyUp={handleSelectionChange}
      onMouseDown={clearSelection}
    >
      {doc.blocks.map((_b, i) => renderBlock(i))}
    </div>
  );
}
