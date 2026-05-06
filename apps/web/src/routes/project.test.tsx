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

it('queues analysis and polls the persisted latest run until suggestions are ready', async () => {
  let createPayload: unknown = null;
  let latestStage: 'none' | 'queued' | 'completed' = 'none';
  let latestQueuedReads = 0;
  let latestRunRequests = 0;
  const queuedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'queued',
        error_message: null,
        suggestions: [],
      },
      {
        id: 'lens-result-2',
        lens: 'political',
        generation_state: 'queued',
        error_message: null,
        suggestions: [],
      },
    ],
  };
  const completedRun = {
    ...queuedRun,
    generation_state: 'completed_with_failures',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'financial',
            body: 'Call out the demand trend as evidence of pricing power.',
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
        lens: 'political',
        generation_state: 'failed',
        error_message: 'Political lens timed out',
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
          markdown: '# Market\n\nDemand is rising.\n\nRules are changing.',
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
      if (latestStage === 'queued') {
        latestQueuedReads += 1;
        if (latestQueuedReads >= 2) {
          latestStage = 'completed';
          return new Response(JSON.stringify(completedRun));
        }
        return new Response(JSON.stringify(queuedRun));
      }
      return new Response(JSON.stringify(completedRun));
    }

    if (url === '/api/projects/project-1/analysis-runs' && method === 'POST') {
      createPayload = JSON.parse(String(init?.body));
      latestStage = 'queued';
      latestQueuedReads = 0;
      return new Response(JSON.stringify(queuedRun), { status: 202 });
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(within(suggestionsPanel).getByLabelText('Financial')).toBeChecked();
  expect(within(suggestionsPanel).getByLabelText('Political')).toBeChecked();
  expect(within(suggestionsPanel).getByLabelText('Real estate')).toBeChecked();
  expect(within(suggestionsPanel).getByLabelText('Software engineering')).toBeChecked();

  fireEvent.click(within(suggestionsPanel).getByLabelText('Real estate'));
  fireEvent.click(within(suggestionsPanel).getByLabelText('Software engineering'));
  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Run analysis' }));

  await waitFor(() => {
    expect(createPayload).toEqual({
      resource_id: 'resource-1',
      lenses: ['financial', 'political'],
    });
  });
  expect(
    await within(suggestionsPanel).findByText(
      'Call out the demand trend as evidence of pricing power.',
      {},
      { timeout: 4000 },
    ),
  ).toBeInTheDocument();
  expect(within(suggestionsPanel).getByText('Failed lenses: political')).toBeInTheDocument();
  expect(latestRunRequests).toBeGreaterThanOrEqual(3);
  expect(
    within(suggestionsPanel).getByRole('button', { name: 'Retry failed lenses' }),
  ).toBeInTheDocument();
});

it('keeps a persisted queued analysis run in generation mode after the create request returns', async () => {
  let createPayload: unknown = null;
  let latestStage: 'none' | 'queued' = 'none';
  let latestRunRequests = 0;
  const queuedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'queued',
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
  fireEvent.click(within(suggestionsPanel).getByLabelText('Real estate'));
  fireEvent.click(within(suggestionsPanel).getByLabelText('Political'));
  fireEvent.click(within(suggestionsPanel).getByLabelText('Software engineering'));
  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Run analysis' }));

  await waitFor(() => {
    expect(createPayload).toEqual({
      resource_id: 'resource-1',
      lenses: ['financial'],
    });
    expect(latestRunRequests).toBeGreaterThanOrEqual(2);
  });

  expect(within(suggestionsPanel).getByText('Generating AI suggestions...')).toBeInTheDocument();
  expect(
    within(suggestionsPanel).queryByText('No AI suggestions awaiting review.'),
  ).not.toBeInTheDocument();
  expect(within(suggestionsPanel).getByRole('button', { name: /analysis/i })).toBeDisabled();
});

it('rehydrates the persisted latest run after switching away and back', async () => {
  let latestRunRequestsForResourceOne = 0;
  const persistedRun = {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'financial',
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
    generation_state: 'succeeded',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-1',
            analysis_run_id: 'run-1',
            lens: 'financial',
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
        lens: 'real_estate',
        generation_state: 'succeeded',
        error_message: null,
        suggestions: [
          {
            id: 'suggestion-2',
            analysis_run_id: 'run-1',
            lens: 'real_estate',
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
    generation_state: 'queued',
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
    lens_results: [
      {
        id: 'lens-result-1',
        lens: 'financial',
        generation_state: 'queued',
        error_message: null,
        suggestions: [],
      },
      {
        id: 'lens-result-2',
        lens: 'real_estate',
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

  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Run analysis' }));

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
