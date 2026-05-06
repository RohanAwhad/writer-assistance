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
