import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, vi } from 'vitest';

import { ProjectRoute } from './project';

const fetchMock = vi.fn<typeof fetch>();

function renderProjectRoute() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/project-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectRoute />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
  window.getSelection()?.removeAllRanges();
});

it('shows resources in a folder tree and renders the selected markdown file', async () => {
  fetchMock.mockImplementation(async (input) => {
    const url = input instanceof Request ? input.url : String(input);

    if (url === '/api/projects/project-1/resources') {
      return new Response(
        JSON.stringify({
          resources: [
            {
              id: 'resource-1',
              project_id: 'project-1',
              logical_path: 'research/market.md',
              original_filename: 'market.md',
              content_hash: 'hash-1',
              upload_status: 'uploaded',
              created_at: '2026-05-05T00:00:00Z',
            },
            {
              id: 'resource-2',
              project_id: 'project-1',
              logical_path: 'research/notes/zoning.md',
              original_filename: 'zoning.md',
              content_hash: 'hash-2',
              upload_status: 'uploaded',
              created_at: '2026-05-05T00:00:00Z',
            },
            {
              id: 'resource-3',
              project_id: 'project-1',
              logical_path: 'summary.md',
              original_filename: 'summary.md',
              content_hash: 'hash-3',
              upload_status: 'uploaded',
              created_at: '2026-05-05T00:00:00Z',
            },
          ],
        }),
      );
    }

    if (url === '/api/resources/resource-2/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-2',
          markdown: '# Zoning\n\nRules are changing.',
        }),
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  expect(await screen.findByText('research')).toBeInTheDocument();
  expect(screen.getByText('notes')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'market.md' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'zoning.md' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'summary.md' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'research/market.md' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'research/notes/zoning.md' })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'zoning.md' }));

  expect(await screen.findByRole('heading', { name: 'Zoning' })).toBeInTheDocument();
  expect(screen.getByText('Rules are changing.')).toBeInTheDocument();
});

it('shows a neutral placeholder before a resource is selected', async () => {
  fetchMock.mockImplementation(async (input) => {
    const url = input instanceof Request ? input.url : String(input);

    if (url === '/api/projects/project-1/resources') {
      return new Response(
        JSON.stringify({
          resources: [
            {
              id: 'resource-1',
              project_id: 'project-1',
              logical_path: 'research/market.md',
              original_filename: 'market.md',
              content_hash: 'hash-1',
              upload_status: 'uploaded',
              created_at: '2026-05-05T00:00:00Z',
            },
          ],
        }),
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  expect(await screen.findByRole('button', { name: 'market.md' })).toBeInTheDocument();
  expect(screen.getByText('Select a document to preview.')).toBeInTheDocument();
  expect(screen.queryByText('Loading document...')).not.toBeInTheDocument();
});

it('creates a quote-anchored note for the selected resource and shows it in the notes panel', async () => {
  const storedAnnotations: Array<{
    id: string;
    project_id: string;
    resource_id: string;
    body: string;
    origin_type: string;
    provenance_source_id: null;
    created_at: string;
    updated_at: string;
    anchor: {
      quoteText: string;
      normalizedText: string;
      startOffset: number;
      endOffset: number;
      blockPath: string[];
      resolutionStatus: string;
    };
  }> = [];
  let createPayload: unknown = null;

  fetchMock.mockImplementation(async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? (input instanceof Request ? input.method : 'GET');

    if (url === '/api/projects/project-1/resources') {
      return new Response(
        JSON.stringify({
          resources: [
            {
              id: 'resource-1',
              project_id: 'project-1',
              logical_path: 'research/market.md',
              original_filename: 'market.md',
              content_hash: 'hash-1',
              upload_status: 'uploaded',
              created_at: '2026-05-05T00:00:00Z',
            },
          ],
        }),
      );
    }

    if (url === '/api/resources/resource-1/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-1',
          markdown: '# Market\n\nDemand is rising.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(JSON.stringify({ annotations: storedAnnotations }));
    }

    if (url === '/api/projects/project-1/annotations' && method === 'POST') {
      createPayload = JSON.parse(String(init?.body));
      const annotation = {
        id: 'annotation-1',
        project_id: 'project-1',
        resource_id: 'resource-1',
        body: 'Supports the demand argument.',
        origin_type: 'user',
        provenance_source_id: null,
        created_at: '2026-05-05T00:00:00Z',
        updated_at: '2026-05-05T00:00:00Z',
        anchor: {
          quoteText: 'Demand is rising.',
          normalizedText: 'demand is rising.',
          startOffset: 0,
          endOffset: 17,
          blockPath: ['paragraph', '1'],
          resolutionStatus: 'exact',
        },
      };
      storedAnnotations.splice(0, storedAnnotations.length, annotation);
      return new Response(JSON.stringify(annotation), { status: 201 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const paragraph = await screen.findByText('Demand is rising.');
  selectText(paragraph, 'Demand is rising.');
  fireEvent.mouseUp(paragraph);

  const notesPanel = await screen.findByRole('region', { name: 'Notes' });
  expect(within(notesPanel).getByText('Demand is rising.')).toBeInTheDocument();

  fireEvent.change(within(notesPanel).getByLabelText('Note'), {
    target: { value: 'Supports the demand argument.' },
  });
  fireEvent.click(within(notesPanel).getByRole('button', { name: 'Save note' }));

  const savedNote = await within(notesPanel).findByRole('listitem');
  expect(within(savedNote).getByText('Supports the demand argument.')).toBeInTheDocument();
  expect(createPayload).toEqual({
    resource_id: 'resource-1',
    body: 'Supports the demand argument.',
    anchor: {
      quoteText: 'Demand is rising.',
      normalizedText: 'demand is rising.',
      startOffset: 0,
      endOffset: 17,
      blockPath: ['paragraph', '1'],
      resolutionStatus: 'exact',
    },
  });
});

function selectText(element: HTMLElement, text: string) {
  const textNode = element.firstChild;

  if (!(textNode instanceof Text)) {
    throw new Error('Expected the selected element to contain a text node');
  }

  const start = textNode.textContent?.indexOf(text) ?? -1;
  if (start < 0) {
    throw new Error(`Could not find "${text}" in the selected element`);
  }

  const selection = window.getSelection();
  if (!selection) {
    throw new Error('Window selection is unavailable');
  }

  const range = document.createRange();
  range.setStart(textNode, start);
  range.setEnd(textNode, start + text.length);
  selection.removeAllRanges();
  selection.addRange(range);
}
