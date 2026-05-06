import { useLayoutEffect, useRef } from 'react';

import ReactMarkdown from 'react-markdown';

import { buildQuoteAnchor, type QuoteAnchor } from '../lib/selection-anchor';

type MarkdownViewerProps = {
  markdown: string;
  onQuoteSelection?: (anchor: QuoteAnchor | null) => void;
};

export function MarkdownViewer({ markdown, onQuoteSelection }: MarkdownViewerProps) {
  const containerRef = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const blockCounts = new Map<string, number>();
    const blocks = container.querySelectorAll<HTMLElement>('h1, h2, h3, h4, h5, h6, p, li, blockquote, pre');

    blocks.forEach((block) => {
      const kind = getBlockKind(block.tagName);
      const nextIndex = (blockCounts.get(kind) ?? 0) + 1;
      blockCounts.set(kind, nextIndex);
      block.dataset.blockPath = `${kind}/${nextIndex}`;
    });
  }, [markdown]);

  function handleMouseUp() {
    if (!onQuoteSelection || !containerRef.current) {
      return;
    }

    const selection = window.getSelection();
    if (!selection) {
      onQuoteSelection(null);
      return;
    }

    onQuoteSelection(buildQuoteAnchor(selection, containerRef.current));
  }

  return (
    <article ref={containerRef} onMouseUp={handleMouseUp}>
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </article>
  );
}

function getBlockKind(tagName: string): string {
  if (/^H[1-6]$/.test(tagName)) {
    return 'heading';
  }

  if (tagName === 'P') {
    return 'paragraph';
  }

  if (tagName === 'LI') {
    return 'listItem';
  }

  if (tagName === 'BLOCKQUOTE') {
    return 'blockquote';
  }

  if (tagName === 'PRE') {
    return 'codeBlock';
  }

  return 'block';
}
