import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
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
});

it('shows a resource tree and renders the selected markdown file', async () => {
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

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();

  fireEvent.click(await screen.findByRole('button', { name: 'research/market.md' }));

  expect(await screen.findByRole('heading', { name: 'Market' })).toBeInTheDocument();
  expect(screen.getByText('Demand is rising.')).toBeInTheDocument();
});
