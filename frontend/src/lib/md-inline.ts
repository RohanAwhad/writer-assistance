export type InlineNode =
  | { kind: "text"; text: string; rawStart: number; rawEnd: number }
  | { kind: "esc"; char: string; rawStart: number; rawEnd: number }
  | { kind: "code"; text: string; rawStart: number; rawEnd: number }
  | { kind: "em"; rawStart: number; rawEnd: number; children: InlineNode[] }
  | { kind: "strong"; rawStart: number; rawEnd: number; children: InlineNode[] }
  | { kind: "link"; href: string; rawStart: number; rawEnd: number; children: InlineNode[] };

const ESCAPABLE = "\\`*_{}[]()#+-.!>";

function isWordChar(c: string | undefined): boolean {
  return c !== undefined && /[A-Za-z0-9_]/.test(c);
}

export function parseInline(s: string): InlineNode[] {
  return scan(s, 0, s.length);
}

function scan(s: string, from: number, to: number): InlineNode[] {
  const nodes: InlineNode[] = [];
  let pos = from;
  let textStart = from;

  const flushText = (end: number): void => {
    if (end > textStart) {
      nodes.push({ kind: "text", text: s.slice(textStart, end), rawStart: textStart, rawEnd: end });
    }
  };

  const push = (node: InlineNode): void => {
    flushText(node.rawStart);
    nodes.push(node);
    pos = node.rawEnd;
    textStart = node.rawEnd;
  };

  while (pos < to) {
    const c = s[pos]!;
    if (c === "\\" && pos + 1 < to && ESCAPABLE.includes(s[pos + 1] ?? "")) {
      const ch = s[pos + 1]!;
      push({ kind: "esc", char: ch, rawStart: pos, rawEnd: pos + 2 });
      continue;
    }
    if (c === "`") {
      const close = s.indexOf("`", pos + 1);
      const nl = s.indexOf("\n", pos + 1);
      if (close !== -1 && (nl === -1 || close < nl)) {
        const text = s.slice(pos + 1, close);
        push({ kind: "code", text, rawStart: pos, rawEnd: close + 1 });
        continue;
      }
    }
    if (c === "[") {
      const linkMatch = /^\[([^\]]*)\]\(([^)\s]+)(?:[ \t]+(?:"[^"]*"|'[^']*'))?\)/.exec(
        s.slice(pos, to),
      );
      if (linkMatch !== null) {
        const label = linkMatch[1] ?? "";
        const href = linkMatch[2] ?? "";
        const consumed = linkMatch[0].length;
        const children = scan(s, pos + 1, pos + 1 + label.length);
        push({
          kind: "link",
          href,
          rawStart: pos,
          rawEnd: pos + consumed,
          children,
        });
        continue;
      }
    }
    if (c === "*" || c === "_") {
      let runLen = 1;
      while (runLen < 3 && pos + runLen < to && s[pos + runLen] === c) runLen += 1;
      const prev = s[pos - 1];
      const next = s[pos + runLen];
      const openable =
        next !== undefined && next !== " " && next !== "\n" && !(c === "_" && isWordChar(prev));
      if (openable) {
        const closer = findCloser(s, pos + runLen, to, c, runLen);
        if (closer !== -1) {
          const inner = scan(s, pos + runLen, closer);
          const node: InlineNode =
            runLen === 3
              ? { kind: "strong", rawStart: pos, rawEnd: closer + runLen, children: [
                  { kind: "em", rawStart: pos + runLen, rawEnd: closer, children: inner },
                ] }
              : runLen === 2
                ? { kind: "strong", rawStart: pos, rawEnd: closer + runLen, children: inner }
                : { kind: "em", rawStart: pos, rawEnd: closer + runLen, children: inner };
          push(node);
          continue;
        }
      }
    }
    pos += 1;
  }
  flushText(to);
  return nodes;
}

function findCloser(s: string, from: number, to: number, c: string, runLen: number): number {
  let p = from;
  while (p < to) {
    if (s[p] === "\n") return -1;
    if (s[p] === "\\" && p + 1 < to) {
      p += 2;
      continue;
    }
    if (s[p] !== c) {
      p += 1;
      continue;
    }
    let n = 1;
    while (p + n < to && s[p + n] === c && n < runLen) n += 1;
    if (n >= runLen) {
      const before = s[p - 1];
      const after = s[p + n];
      const badClose =
        c === "_"
          ? isWordChar(before) && isWordChar(after)
          : before !== undefined && (before === " " || before === "\n");
      if (!badClose) return p;
    }
    p += 1;
  }
  return -1;
}
