import fs from 'node:fs/promises';
import path from 'node:path';

import { expect, test, type Page } from '@playwright/test';

test('smoke covers the reading workspace flow', async ({ page }, testInfo) => {
  const projectTitle = 'Smoke Project';
  const userNote = 'User note from the smoke test.';
  const acceptedSuggestion = 'Highlight the demand trend as evidence for pricing power.';
  const uploadDirectory = testInfo.outputPath('upload');
  const markdownPath = path.join(uploadDirectory, 'market.md');

  await fs.mkdir(uploadDirectory, { recursive: true });
  await fs.writeFile(markdownPath, '# Market\n\nDemand is rising.\n\nRules are changing.\n');

  await page.goto('/');

  await page.getByLabel('Project title').fill(projectTitle);
  await page.getByRole('button', { name: 'Create project' }).click();

  await expect(page.getByRole('link', { name: projectTitle })).toBeVisible();
  const uploadSection = page.locator('section', {
    has: page.getByRole('heading', { name: projectTitle }),
  });

  const uploadResponsePromise = page.waitForResponse((response) =>
    response.url().includes('/api/projects/') && response.url().includes('/resources/upload'),
  );
  await uploadSection.getByLabel('Upload markdown folder').setInputFiles(uploadDirectory);
  await uploadSection.getByRole('button', { name: 'Upload folder' }).click();
  const uploadResponse = await uploadResponsePromise;
  const uploadPayload = (await uploadResponse.json()) as {
    resources: Array<{ logical_path: string }>;
  };

  expect(uploadResponse.ok()).toBeTruthy();
  expect(uploadPayload.resources).toHaveLength(1);

  await page.getByRole('link', { name: projectTitle }).click();
  await expect(page).toHaveURL(/\/projects\/.+/);

  await page.getByRole('button', { name: 'market.md' }).click();
  await expect(page.getByRole('heading', { name: 'Market' })).toBeVisible();

  await selectText(page, 'Demand is rising.');

  const notesPanel = page.getByRole('region', { name: 'Notes' });
  await expect(notesPanel.getByText('Demand is rising.')).toBeVisible();

  await notesPanel.getByLabel('Note').fill(userNote);
  await notesPanel.getByRole('button', { name: 'Save note' }).click();

  await expect(notesPanel.getByText(userNote)).toBeVisible();

  const suggestionsPanel = page.getByRole('region', { name: 'AI suggestions' });
  await expect(suggestionsPanel.getByRole('heading', { name: 'AI suggestions' })).toBeVisible();
  await suggestionsPanel.getByRole('button', { name: 'Run analysis' }).click();

  await expect(suggestionsPanel.getByText(acceptedSuggestion)).toBeVisible({ timeout: 15_000 });

  await suggestionsPanel.getByRole('button', { name: 'Accept suggestion' }).click();

  await expect(notesPanel.getByText(userNote)).toBeVisible();
  await expect(notesPanel.getByText(acceptedSuggestion)).toBeVisible();
  await expect(suggestionsPanel.getByText(acceptedSuggestion)).toHaveCount(0);
});

async function selectText(page: Page, text: string) {
  await page.locator('article').evaluate((article, selectedText) => {
    const block = Array.from(article.querySelectorAll<HTMLElement>('p, h1, h2, h3, h4, h5, h6, li'))
      .find((element) => element.textContent?.includes(selectedText));
    if (!block) {
      throw new Error(`Could not find block containing "${selectedText}"`);
    }

    const textNode = Array.from(block.childNodes).find(
      (node): node is Text =>
        node.nodeType === Node.TEXT_NODE && (node.textContent ?? '').includes(selectedText),
    );
    if (!textNode || textNode.textContent === null) {
      throw new Error(`Could not find text node containing "${selectedText}"`);
    }

    const start = textNode.textContent.indexOf(selectedText);
    if (start < 0) {
      throw new Error(`Could not find "${selectedText}" in text node`);
    }

    const range = document.createRange();
    range.setStart(textNode, start);
    range.setEnd(textNode, start + selectedText.length);

    const selection = window.getSelection();
    if (!selection) {
      throw new Error('Window selection is unavailable');
    }

    selection.removeAllRanges();
    selection.addRange(range);
  }, text);

  await page.locator('article').dispatchEvent('mouseup');
}
