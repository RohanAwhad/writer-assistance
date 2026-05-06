import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

it('shows a single Run analysis action before any analysis run exists', async () => {
  let createPayload: unknown = null;
  let latestRunExists = false;
  const queuedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'queued',
    discovered_lenses: [],
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [],
  };

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
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest' && method === 'GET') {
      if (!latestRunExists) {
        return new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 });
      }
      return new Response(JSON.stringify(queuedRun));
    }

    if (url === '/api/projects/project-1/analysis-runs' && method === 'POST') {
      createPayload = JSON.parse(String(init?.body));
      latestRunExists = true;
      return new Response(JSON.stringify(queuedRun), { status: 202 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  const runAnalysisButton = await within(suggestionsPanel).findByRole('button', {
    name: 'Run analysis',
  });
  expect(runAnalysisButton).toBeInTheDocument();
  expect(within(suggestionsPanel).queryByRole('button', { name: 'Regenerate lenses' })).not.toBeInTheDocument();
  expect(within(suggestionsPanel).queryByLabelText('Financial')).not.toBeInTheDocument();
  expect(within(suggestionsPanel).queryByLabelText('Political')).not.toBeInTheDocument();
  expect(within(suggestionsPanel).queryByLabelText('Real estate')).not.toBeInTheDocument();
  expect(
    within(suggestionsPanel).queryByLabelText('Software engineering'),
  ).not.toBeInTheDocument();

  fireEvent.click(runAnalysisButton);

  await waitFor(() => {
    expect(createPayload).toEqual({ resource_id: 'resource-1' });
  });
});

it('waits for the latest-run query to settle before offering Run analysis', async () => {
  let resolveLatestRunResponse!: (response: Response) => void;
  const latestRunResponse = new Promise<Response>((resolve) => {
    resolveLatestRunResponse = resolve;
  });

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

    if (url === '/api/resources/resource-1/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-1',
          markdown: '# Market\n\nDemand is rising.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return latestRunResponse;
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(within(suggestionsPanel).getByText('Checking for an existing analysis run...')).toBeInTheDocument();
  expect(within(suggestionsPanel).queryByRole('button', { name: 'Run analysis' })).not.toBeInTheDocument();

  resolveLatestRunResponse(
    new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 }),
  );

  expect(await within(suggestionsPanel).findByRole('button', { name: 'Run analysis' })).toBeInTheDocument();
});

it('renders discovered lenses from the latest run and offers regeneration', async () => {
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

    if (url === '/api/resources/resource-1/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-1',
          markdown: '# Market\n\nDemand is rising.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(
        JSON.stringify({
          annotations: [
            {
              id: 'annotation-1',
              project_id: 'project-1',
              resource_id: 'resource-1',
              body: 'Accepted note persists.',
              origin_type: 'accepted_ai',
              provenance_source_id: 'suggestion-1',
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
            },
          ],
        }),
      );
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return new Response(
        JSON.stringify({
          id: 'run-2',
          project_id: 'project-1',
          resource_id: 'resource-1',
          lens_discovery_status: 'succeeded',
          discovered_lenses: [
            {
              name: 'Demand trend',
              description: 'Highlights pricing power and revenue implications.',
            },
          ],
          generation_state: 'succeeded',
          lens_results: [
            {
              id: 'lens-result-1',
              lens: 'Demand trend',
              generation_state: 'succeeded',
              error_message: null,
              suggestions: [],
            },
          ],
          created_at: '2026-05-05T00:00:00Z',
          updated_at: '2026-05-05T00:00:00Z',
        }),
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(await within(suggestionsPanel).findByText('Demand trend')).toBeInTheDocument();
  expect(
    await within(suggestionsPanel).findByText('Highlights pricing power and revenue implications.'),
  ).toBeInTheDocument();
  expect(
    await within(suggestionsPanel).findByRole('button', { name: 'Regenerate lenses' }),
  ).toBeInTheDocument();
  expect(within(suggestionsPanel).queryByRole('button', { name: 'Run analysis' })).not.toBeInTheDocument();
  expect(within(suggestionsPanel).queryByLabelText('Financial')).not.toBeInTheDocument();
  expect(screen.getByText('Accepted note persists.')).toBeInTheDocument();
});

it('shows discovery progress for a persisted queued run after the first create request returns', async () => {
  let createPayload: unknown = null;
  let latestStage: 'none' | 'queued' = 'none';
  let latestRunRequests = 0;
  const queuedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'queued',
    discovered_lenses: [],
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [],
  };

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
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest' && method === 'GET') {
      latestRunRequests += 1;
      if (latestStage === 'none') {
        return new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 });
      }
      return new Response(JSON.stringify(queuedRun));
    }

    if (url === '/api/projects/project-1/analysis-runs' && method === 'POST') {
      createPayload = JSON.parse(String(init?.body));
      latestStage = 'queued';
      return new Response(JSON.stringify(queuedRun), { status: 202 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  fireEvent.click(
    await within(suggestionsPanel).findByRole('button', { name: 'Run analysis' }),
  );

  await waitFor(() => {
    expect(createPayload).toEqual({ resource_id: 'resource-1' });
    expect(latestRunRequests).toBeGreaterThanOrEqual(2);
  });

  expect(within(suggestionsPanel).getByText('Discovering lenses...')).toBeInTheDocument();
  expect(
    within(suggestionsPanel).queryByText('Generating suggestions...'),
  ).not.toBeInTheDocument();
  expect(within(suggestionsPanel).getByRole('button', { name: 'Regenerate lenses' })).toBeDisabled();
});

it('shows a discovery failure message instead of the generic empty state', async () => {
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

    if (url === '/api/resources/resource-1/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-1',
          markdown: '# Market\n\nDemand is rising.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return new Response(
        JSON.stringify({
          id: 'run-1',
          project_id: 'project-1',
          resource_id: 'resource-1',
          lens_discovery_status: 'failed',
          discovered_lenses: [],
          generation_state: 'failed',
          error_summary: 'Lens discovery failed. Regenerate lenses to try again.',
          lens_results: [],
          created_at: '2026-05-05T00:00:00Z',
          updated_at: '2026-05-05T00:00:00Z',
        }),
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(
    await within(suggestionsPanel).findByRole('alert'),
  ).toHaveTextContent('Lens discovery failed. Regenerate lenses to try again.');
  expect(
    within(suggestionsPanel).getByRole('button', { name: 'Regenerate lenses' }),
  ).toBeInTheDocument();
  expect(within(suggestionsPanel).queryByText('No AI suggestions awaiting review.')).not.toBeInTheDocument();
});

it('does not offer retry failed lenses while the latest run is still active', async () => {
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

    if (url === '/api/resources/resource-1/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-1',
          markdown: '# Market\n\nDemand is rising.\n\nRules are changing.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return new Response(
        JSON.stringify({
          id: 'run-1',
          project_id: 'project-1',
          resource_id: 'resource-1',
          lens_discovery_status: 'succeeded',
          discovered_lenses: [
            {
              name: 'Demand trend',
              description: 'Highlights pricing power and revenue implications.',
            },
            {
              name: 'Policy risk',
              description: 'Checks whether policy language changes the interpretation.',
            },
          ],
          generation_state: 'running',
          error_summary: null,
          lens_results: [
            {
              id: 'lens-result-1',
              lens: 'Demand trend',
              generation_state: 'failed',
              error_message: 'Lens timed out',
              suggestions: [],
            },
            {
              id: 'lens-result-2',
              lens: 'Policy risk',
              generation_state: 'running',
              error_message: null,
              suggestions: [],
            },
          ],
          created_at: '2026-05-05T00:00:00Z',
          updated_at: '2026-05-05T00:00:00Z',
        }),
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(await within(suggestionsPanel).findByText('Failed lenses: Demand trend')).toBeInTheDocument();
  expect(within(suggestionsPanel).getByText('Generating suggestions...')).toBeInTheDocument();
  expect(
    within(suggestionsPanel).queryByRole('button', { name: 'Retry failed lenses' }),
  ).not.toBeInTheDocument();
});

it('rehydrates the persisted latest run after switching away and back', async () => {
  let latestRunRequestsForResourceOne = 0;
  const persistedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'succeeded',
    discovered_lenses: [
      {
        name: 'Demand trend',
        description: 'Highlights pricing power and revenue implications.',
      },
    ],
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'Demand trend',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'Demand trend',
            body: 'Persisted financial suggestion.',
            review_state: 'unreviewed',
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
          },
        ],
      },
    ],
  };

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
            {
              id: 'resource-2',
              project_id: 'project-1',
              logical_path: 'research/zoning.md',
              original_filename: 'zoning.md',
              content_hash: 'hash-2',
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

    if (url === '/api/resources/resource-2/content') {
      return new Response(
        JSON.stringify({
          resource_id: 'resource-2',
          markdown: '# Zoning\n\nRules are changing.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations' || url === '/api/resources/resource-2/annotations') {
      return new Response(JSON.stringify({ annotations: [] }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest' && method === 'GET') {
      latestRunRequestsForResourceOne += 1;
      return new Response(JSON.stringify(persistedRun));
    }

    if (url === '/api/resources/resource-2/analysis-runs/latest' && method === 'GET') {
      return new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(await within(suggestionsPanel).findByText('Persisted financial suggestion.')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'zoning.md' }));
  expect(await screen.findByText('Run analysis on this document to generate suggestions.')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'market.md' }));
  expect(await within(suggestionsPanel).findByText('Persisted financial suggestion.')).toBeInTheDocument();
  expect(latestRunRequestsForResourceOne).toBeGreaterThanOrEqual(2);
});

it('keeps accepted notes visible when the latest run changes', async () => {
  const annotations: Array<{
    id: string;
    project_id: string;
    resource_id: string;
    body: string;
    origin_type: string;
    provenance_source_id: string | null;
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
  let latestStage: 'initial' | 'regenerated' = 'initial';
  const initialRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'succeeded',
    discovered_lenses: [
      {
        name: 'Demand trend',
        description: 'Highlights pricing power and revenue implications.',
      },
    ],
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'Demand trend',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'Demand trend',
            body: 'Capture the demand signal in the final memo.',
            review_state: 'unreviewed',
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
          },
        ],
      },
    ],
  };
  const queuedRegeneratedRun = {
    id: 'run-2',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'queued',
    discovered_lenses: [],
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [],
  };
  const regeneratedRun = {
    id: 'run-2',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'succeeded',
    discovered_lenses: [
      {
        name: 'Execution risk',
        description: 'Looks for operational constraints in the same document.',
      },
    ],
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-2',
        lens: 'Execution risk',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [],
      },
    ],
  };

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
      return new Response(JSON.stringify({ annotations }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest' && method === 'GET') {
      return new Response(JSON.stringify(latestStage === 'initial' ? initialRun : regeneratedRun));
    }

    if (url === '/api/analysis-suggestions/suggestion-1/accept' && method === 'POST') {
      const suggestion = initialRun.lens_results[0].suggestions[0];
      suggestion.review_state = 'accepted';
      const annotation = {
        id: 'annotation-accepted',
        project_id: 'project-1',
        resource_id: 'resource-1',
        body: suggestion.body,
        origin_type: 'accepted_ai',
        provenance_source_id: suggestion.id,
        created_at: '2026-05-05T00:00:00Z',
        updated_at: '2026-05-05T00:00:00Z',
        anchor: suggestion.anchor,
      };
      annotations.splice(0, annotations.length, annotation);
      return new Response(JSON.stringify({ suggestion, annotation }), { status: 201 });
    }

    if (url === '/api/resources/resource-1/analysis-runs/regenerate-lenses' && method === 'POST') {
      latestStage = 'regenerated';
      return new Response(JSON.stringify(queuedRegeneratedRun), { status: 202 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const notesPanel = await screen.findByRole('region', { name: 'Notes' });
  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });

  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Accept suggestion' }));

  expect(
    await within(notesPanel).findByText('Capture the demand signal in the final memo.'),
  ).toBeInTheDocument();

  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Regenerate lenses' }));

  expect(await within(suggestionsPanel).findByText('Execution risk')).toBeInTheDocument();
  expect(
    within(notesPanel).getByText('Capture the demand signal in the final memo.'),
  ).toBeInTheDocument();
});

it('accepts and discards AI suggestions from the persisted latest run while keeping notes separate until accepted', async () => {
  const annotations: Array<{
    id: string;
    project_id: string;
    resource_id: string;
    body: string;
    origin_type: string;
    provenance_source_id: string | null;
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
  const analysisRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'succeeded',
    discovered_lenses: [
      {
        name: 'Demand trend',
        description: 'Highlights pricing power and revenue implications.',
      },
      {
        name: 'Execution risk',
        description: 'Looks for operational constraints in the same document.',
      },
    ],
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'Demand trend',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'Demand trend',
            body: 'Capture the demand signal in the final memo.',
            review_state: 'unreviewed',
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
          },
        ],
      },
      {
        id: 'lens-result-2',
        lens: 'Execution risk',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-2',
            analysis_run_id: 'run-1',
            lens: 'Execution risk',
            body: 'Flag the zoning change as a local market constraint.',
            review_state: 'unreviewed',
            created_at: '2026-05-05T00:00:00Z',
            updated_at: '2026-05-05T00:00:00Z',
            anchor: {
              quoteText: 'Rules are changing.',
              normalizedText: 'rules are changing.',
              startOffset: 19,
              endOffset: 38,
              blockPath: ['paragraph', '2'],
              resolutionStatus: 'exact',
            },
          },
        ],
      },
    ],
  };
  const queuedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: 'queued',
    discovered_lenses: [],
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'Demand trend',
        generation_state: 'queued',
        error_message: null,
        suggestions: [],
      },
      {
        id: 'lens-result-2',
        lens: 'Execution risk',
        generation_state: 'queued',
        error_message: null,
        suggestions: [],
      },
    ],
  };
  let latestStage: 'none' | 'completed' = 'none';

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
          markdown: '# Market\n\nDemand is rising.\n\nRules are changing.',
        }),
      );
    }

    if (url === '/api/resources/resource-1/annotations') {
      return new Response(JSON.stringify({ annotations }));
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest' && method === 'GET') {
      if (latestStage === 'none') {
        return new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 });
      }
      return new Response(JSON.stringify(analysisRun));
    }

    if (url === '/api/projects/project-1/analysis-runs' && method === 'POST') {
      latestStage = 'completed';
      return new Response(JSON.stringify(queuedRun), { status: 202 });
    }

    if (url === '/api/analysis-suggestions/suggestion-1/accept' && method === 'POST') {
      const suggestion = analysisRun.lens_results[0].suggestions[0];
      suggestion.review_state = 'accepted';
      const annotation = {
        id: 'annotation-accepted',
        project_id: 'project-1',
        resource_id: 'resource-1',
        body: suggestion.body,
        origin_type: 'accepted_ai',
        provenance_source_id: suggestion.id,
        created_at: '2026-05-05T00:00:00Z',
        updated_at: '2026-05-05T00:00:00Z',
        anchor: suggestion.anchor,
      };
      annotations.splice(0, annotations.length, annotation);
      return new Response(JSON.stringify({ suggestion, annotation }), { status: 201 });
    }

    if (url === '/api/analysis-suggestions/suggestion-2/discard' && method === 'POST') {
      const suggestion = analysisRun.lens_results[1].suggestions[0];
      suggestion.review_state = 'discarded';
      return new Response(JSON.stringify({ suggestion }));
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const notesPanel = await screen.findByRole('region', { name: 'Notes' });
  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });

  fireEvent.click(
    await within(suggestionsPanel).findByRole('button', { name: 'Run analysis' }),
  );

  expect(
    await within(suggestionsPanel).findByText('Capture the demand signal in the final memo.'),
  ).toBeInTheDocument();
  expect(
    within(notesPanel).queryByText('Capture the demand signal in the final memo.'),
  ).not.toBeInTheDocument();

  fireEvent.click(within(suggestionsPanel).getAllByRole('button', { name: 'Accept suggestion' })[0]);

  expect(
    await within(notesPanel).findByText('Capture the demand signal in the final memo.'),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      within(suggestionsPanel).queryByText('Capture the demand signal in the final memo.'),
    ).not.toBeInTheDocument();
  });

  fireEvent.click(within(suggestionsPanel).getAllByRole('button', { name: 'Discard suggestion' })[0]);

  await waitFor(() => {
    expect(
      within(suggestionsPanel).queryByText('Flag the zoning change as a local market constraint.'),
    ).not.toBeInTheDocument();
  });
  expect(analysisRun.lens_results[1].suggestions[0].review_state).toBe('discarded');
  expect(within(notesPanel).queryByText('Flag the zoning change as a local market constraint.')).not.toBeInTheDocument();
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
