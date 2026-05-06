import { afterEach, test, expect } from 'vitest';

import { buildQuoteAnchor } from './selection-anchor';

afterEach(() => {
  window.getSelection()?.removeAllRanges();
  document.body.innerHTML = '';
});

test('buildQuoteAnchor trims boundary whitespace and adjusts offsets to the trimmed span', () => {
  document.body.innerHTML = `
    <div id="container">
      <p data-block-path="paragraph/1">  Demand is rising.  </p>
    </div>
  `;

  const container = document.getElementById('container');
  const paragraph = container?.querySelector('p');
  const textNode = paragraph?.firstChild;

  if (!(container instanceof HTMLElement) || !(paragraph instanceof HTMLParagraphElement)) {
    throw new Error('Expected container and paragraph elements');
  }

  if (!(textNode instanceof Text)) {
    throw new Error('Expected paragraph text node');
  }

  const range = document.createRange();
  range.setStart(textNode, 0);
  range.setEnd(textNode, textNode.textContent?.length ?? 0);

  const selection = window.getSelection();
  if (!selection) {
    throw new Error('Expected window selection');
  }

  selection.removeAllRanges();
  selection.addRange(range);

  expect(buildQuoteAnchor(selection, container)).toEqual({
    quoteText: 'Demand is rising.',
    normalizedText: 'demand is rising.',
    startOffset: 2,
    endOffset: 19,
    blockPath: ['paragraph', '1'],
    resolutionStatus: 'exact',
  });
});
