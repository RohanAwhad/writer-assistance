export interface Span {
  kind: "heading" | "paragraph" | "quote" | "list" | "code";
  rawStart: number;
  marker: number;
  end: number;
}

export interface DocBlock {
  type: "heading" | "paragraph" | "quote" | "list" | "code" | "hr";
  spanIds: number[];
  level?: number;
  ordered?: boolean;
  codeLang?: string;
}

export interface ParsedDoc {
  text: string;
  spans: Span[];
  blocks: DocBlock[];
}

interface Line {
  start: number;
  text: string;
}

function splitLines(text: string): Line[] {
  const lines: Line[] = [];
  let pos = 0;
  while (pos < text.length) {
    const nl = text.indexOf("\n", pos);
    const end = nl === -1 ? text.length : nl;
    lines.push({ start: pos, text: text.slice(pos, end) });
    pos = end + 1;
  }
  return lines;
}

function isSpace(c: string | undefined): boolean {
  return c === " " || c === "\t";
}

function contentAfterMarker(line: string, markerChars: string): number {
  let pos = markerChars.length;
  while (pos < line.length && isSpace(line[pos])) pos += 1;
  return pos;
}

function trailingHashTrim(line: string): number {
  let end = line.length;
  while (end > 0 && line[end - 1] === "#") end -= 1;
  while (end > 0 && isSpace(line[end - 1])) end -= 1;
  return end;
}

export function parseMarkdown(text: string): ParsedDoc {
  const lines = splitLines(text);
  const spans: Span[] = [];
  const blocks: DocBlock[] = [];
  const total = text.length;

  const addSpan = (kind: Span["kind"], rawStart: number, marker: number, end: number): number => {
    spans.push({ kind, rawStart, marker, end });
    return spans.length - 1;
  };

  const isAtx = (line: string): RegExpMatchArray | null => /^(#{1,6})(?:[ \t]+|$)/.exec(line);
  const isFence = (line: string): RegExpMatchArray | null => /^```([A-Za-z0-9_+-]*)[ \t]*$/.exec(line);
  const isHrLine = (line: string): boolean =>
    /^\s*([-*_])(?:[ \t]*\1){2,}[ \t]*$/.test(line);
  const isQuoteLine = (line: string): string | null => {
    const m = /^ {0,3}> ?/.exec(line);
    return m === null ? null : m[0];
  };
  const isListLine = (line: string): { prefix: string; ordered: boolean } | null => {
    const m = /^([ \t]*)([-+*]|\d{1,9}[.)])[ \t]+/.exec(line);
    if (m === null) return null;
    return { prefix: m[0], ordered: /^\d/.test(m[2]!) };
  };
  const isSetextLine = (line: string): number | null => {
    const m = /^\s*(={3,}|-{3,})\s*$/.exec(line);
    if (m === null) return null;
    return m[1]!.startsWith("=") ? 1 : 2;
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i]!;
    if (line.text.trim() === "") {
      i += 1;
      continue;
    }
    const atx = isAtx(line.text);
    if (atx !== null) {
      const level = atx[1]!.length;
      const marker = contentAfterMarker(line.text, atx[1]!);
      const span = addSpan("heading", line.start, marker, line.start + trailingHashTrim(line.text));
      blocks.push({ type: "heading", spanIds: [span], level });
      i += 1;
      continue;
    }
    const fence = isFence(line.text);
    if (fence !== null) {
      const lang = fence[1] ?? "";
      i += 1;
      const codeStart = i < lines.length ? lines[i]!.start : total;
      while (i < lines.length && !/^```[ \t]*$/.test(lines[i]!.text)) i += 1;
      const codeEnd = i < lines.length ? lines[i]!.start : total;
      const end = codeEnd > 0 && text[codeEnd - 1] === "\n" ? codeEnd - 1 : codeEnd;
      if (end > codeStart) {
        const span = addSpan("code", codeStart, 0, end);
        blocks.push({ type: "code", spanIds: [span], codeLang: lang });
      }
      if (i < lines.length) i += 1;
      continue;
    }
    const setext = isSetextLine(line.text);
    if (setext !== null && blocks.length > 0) {
      const prev = blocks[blocks.length - 1]!;
      if (prev.type === "paragraph") {
        blocks.pop();
        blocks.push({ type: "heading", spanIds: prev.spanIds, level: setext });
        i += 1;
        continue;
      }
    }
    if (isHrLine(line.text)) {
      blocks.push({ type: "hr", spanIds: [] });
      i += 1;
      continue;
    }
    const quotePrefix = isQuoteLine(line.text);
    if (quotePrefix !== null) {
      const spanIds: number[] = [];
      while (i < lines.length) {
        const ql = lines[i]!;
        if (ql.text.trim() === "") break;
        const qp = isQuoteLine(ql.text);
        if (qp === null) break;
        const marker = contentAfterMarker(ql.text, qp);
        spanIds.push(addSpan("quote", ql.start, marker, ql.start + ql.text.length));
        i += 1;
      }
      blocks.push({ type: "quote", spanIds });
      continue;
    }
    const listMatch = isListLine(line.text);
    if (listMatch !== null) {
      const spanIds: number[] = [];
      let ordered = listMatch.ordered;
      while (i < lines.length) {
        const ll = lines[i]!;
        if (ll.text.trim() === "") break;
        const lm = isListLine(ll.text);
        if (lm === null) break;
        const marker = contentAfterMarker(ll.text, lm.prefix);
        spanIds.push(addSpan("list", ll.start, marker, ll.start + ll.text.length));
        ordered = lm.ordered;
        i += 1;
      }
      blocks.push({ type: "list", spanIds, ordered });
      continue;
    }
    let end = line.start + line.text.length;
    let j = i + 1;
    while (j < lines.length) {
      const next = lines[j]!.text;
      if (next.trim() === "") break;
      if (isAtx(next) !== null || isFence(next) !== null) break;
      if (isSetextLine(next) !== null || isHrLine(next)) break;
      if (isQuoteLine(next) !== null || isListLine(next) !== null) break;
      end = lines[j]!.start + next.length;
      j += 1;
    }
    const span = addSpan("paragraph", line.start, 0, end);
    blocks.push({ type: "paragraph", spanIds: [span] });
    i = j;
  }
  return { text, spans, blocks };
}

export interface MarkRange {
  start: number;
  end: number;
}

export interface SpanMark {
  spanId: number;
  range: MarkRange;
}

export function clipMarksToSpans(doc: ParsedDoc, ranges: MarkRange[]): SpanMark[] {
  const out: SpanMark[] = [];
  for (const range of ranges) {
    if (range.end <= range.start) continue;
    for (let s = 0; s < doc.spans.length; s += 1) {
      const span = doc.spans[s]!;
      const visStart = span.rawStart + span.marker;
      const clipStart = Math.max(range.start, visStart);
      const clipEnd = Math.min(range.end, span.end);
      if (clipEnd > clipStart) {
        out.push({ spanId: s, range: { start: clipStart, end: clipEnd } });
      }
    }
  }
  return out;
}

function isWs(c: string): boolean {
  return c === " " || c === "\t" || c === "\n";
}

export interface MarkMatch {
  start: number;
  end: number;
}

export function findMarkRange(
  doc: ParsedDoc,
  selectedText: string,
  anchorRawStart: number,
  blockSpanId: number,
): MarkMatch {
  const needle = selectedText.trim();
  if (needle.length === 0) throw new Error("selection is empty");
  if (needle.length > 10000) throw new Error("selection is too long to annotate");
  const span = doc.spans[blockSpanId];
  if (span === undefined) throw new Error("selection is outside the document");
  const spanText = doc.text.slice(span.rawStart + span.marker, span.end);
  const base = span.rawStart + span.marker;
  const anchorLocal = Math.min(Math.max(anchorRawStart - base, 0), spanText.length);

  const tryRange = (localS: number, localE: number): MarkMatch | null => {
    if (localE <= localS) return null;
    const slice = doc.text.slice(base + localS, base + localE);
    if (span.kind !== "code" && slice.includes("\n\n")) return null;
    return { start: base + localS, end: base + localE };
  };

  const exact: Array<{ s: number; e: number; delta: number }> = [];
  let idx = spanText.indexOf(needle);
  while (idx !== -1) {
    exact.push({ s: idx, e: idx + needle.length, delta: Math.abs(idx - anchorLocal) });
    idx = spanText.indexOf(needle, idx + 1);
  }
  exact.sort((a, b) => a.delta - b.delta);
  for (const hit of exact) {
    const ok = tryRange(hit.s, hit.e);
    if (ok !== null) return ok;
  }

  let normSpan = "";
  const rawAt: number[] = [];
  let lastSpace = false;
  for (let k = 0; k < spanText.length; k += 1) {
    const c = spanText[k]!;
    if (isWs(c)) {
      if (!lastSpace) {
        normSpan += " ";
        rawAt.push(k);
      }
      lastSpace = true;
    } else {
      normSpan += c;
      rawAt.push(k);
      lastSpace = false;
    }
  }
  let normNeedle = "";
  for (const c of needle) {
    if (isWs(c)) {
      if (normNeedle.length === 0 || !normNeedle.endsWith(" ")) normNeedle += " ";
    } else {
      normNeedle += c;
    }
  }
  normNeedle = normNeedle.trim();
  if (normNeedle.length === 0) throw new Error("selection is empty");
  const candidates: Array<{ s: number; e: number; delta: number }> = [];
  let pos = normSpan.indexOf(normNeedle);
  while (pos !== -1) {
    const rawS = rawAt[pos];
    const last = rawAt[pos + normNeedle.length - 1];
    if (rawS !== undefined && last !== undefined) {
      candidates.push({ s: rawS, e: last + 1, delta: Math.abs(rawS - anchorLocal) });
    }
    pos = normSpan.indexOf(normNeedle, pos + 1);
  }
  candidates.sort((a, b) => a.delta - b.delta);
  for (const hit of candidates) {
    let s = hit.s;
    let e = hit.e;
    while (s > 0 && isWs(spanText[s - 1] ?? "")) s -= 1;
    while (e < spanText.length && isWs(spanText[e] ?? "")) e += 1;
    const ok = tryRange(s, e);
    if (ok !== null) return ok;
  }
  throw new Error(
    "could not map the selection onto the document text; try selecting plain text within one paragraph",
  );
}
