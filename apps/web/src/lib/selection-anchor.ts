export type QuoteAnchor = {
  quoteText: string;
  normalizedText: string;
  startOffset: number;
  endOffset: number;
  blockPath: string[];
  resolutionStatus: 'exact' | 'fuzzy' | 'unresolved';
};

export function buildQuoteAnchor(
  selection: Selection,
  container: HTMLElement,
): QuoteAnchor | null {
  if (selection.rangeCount === 0 || selection.isCollapsed) {
    return null;
  }

  const range = selection.getRangeAt(0);
  if (!container.contains(range.commonAncestorContainer)) {
    return null;
  }

  const startBlock = findClosestBlock(range.startContainer, container);
  const endBlock = findClosestBlock(range.endContainer, container);
  if (!startBlock || !endBlock || startBlock !== endBlock) {
    return null;
  }

  const blockPath = parseBlockPath(startBlock);
  if (!blockPath) {
    return null;
  }

  const selectedText = selection.toString();
  const quoteText = selectedText.trim();
  if (!quoteText) {
    return null;
  }

  const rawStartOffset = getOffsetWithinBlock(startBlock, range.startContainer, range.startOffset);
  const rawEndOffset = getOffsetWithinBlock(endBlock, range.endContainer, range.endOffset);
  const startOffset = rawStartOffset + getLeadingWhitespaceLength(selectedText);
  const endOffset = rawEndOffset - getTrailingWhitespaceLength(selectedText);
  if (startOffset >= endOffset) {
    return null;
  }

  return {
    quoteText,
    normalizedText: normalizeQuoteText(quoteText),
    startOffset,
    endOffset,
    blockPath,
    resolutionStatus: 'exact',
  };
}

function findClosestBlock(node: Node | null, container: HTMLElement): HTMLElement | null {
  let current: Element | null = node instanceof Element ? node : node?.parentElement ?? null;

  while (current) {
    if (current instanceof HTMLElement && current.dataset.blockPath) {
      return current;
    }

    if (current === container) {
      return null;
    }

    current = current.parentElement;
  }

  return null;
}

function parseBlockPath(element: HTMLElement): string[] | null {
  const rawBlockPath = element.dataset.blockPath;
  if (!rawBlockPath) {
    return null;
  }

  const blockPath = rawBlockPath.split('/').filter(Boolean);
  return blockPath.length ? blockPath : null;
}

function getOffsetWithinBlock(block: HTMLElement, node: Node, offset: number): number {
  const range = document.createRange();
  range.selectNodeContents(block);
  range.setEnd(node, offset);
  return range.toString().length;
}

function getLeadingWhitespaceLength(value: string): number {
  return value.match(/^\s*/)?.[0].length ?? 0;
}

function getTrailingWhitespaceLength(value: string): number {
  return value.match(/\s*$/)?.[0].length ?? 0;
}

function normalizeQuoteText(quoteText: string): string {
  return quoteText.replace(/\s+/g, ' ').trim().toLowerCase();
}
