import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

import { RootRoute } from './root';

const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function createJsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
    ...init,
  });
}

function renderRootRoute() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <RootRoute />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it('shows a loading state while projects are being fetched', () => {
  fetchMock.mockImplementation(() => new Promise<Response>(() => {}));

  renderRootRoute();

  expect(screen.getByText('Loading projects...')).toBeInTheDocument();
});

it('shows the project empty state when there are no projects', async () => {
  fetchMock.mockResolvedValue(createJsonResponse({ projects: [] }));

  renderRootRoute();

  expect(await screen.findByText('Create your first project')).toBeInTheDocument();
});

it('shows the project list when projects exist', async () => {
  fetchMock.mockResolvedValue(
    createJsonResponse({
      projects: [
        {
          id: 'project-1',
          title: 'Municipal Housing Brief',
          created_at: '2026-05-05T21:00:00.000Z',
          updated_at: '2026-05-05T21:00:00.000Z',
        },
      ],
    }),
  );

  renderRootRoute();

  expect(await screen.findByRole('heading', { name: 'Projects' })).toBeInTheDocument();
  expect(screen.getByText('Municipal Housing Brief')).toBeInTheDocument();
  expect(screen.queryByText('Create your first project')).not.toBeInTheDocument();
});

it('shows an error state when loading projects fails', async () => {
  fetchMock.mockResolvedValue(new Response(null, { status: 500 }));

  renderRootRoute();

  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load projects.');
  expect(screen.queryByText('Create your first project')).not.toBeInTheDocument();
});
