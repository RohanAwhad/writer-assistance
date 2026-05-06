import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import { uploadResources } from '../lib/api';

import { ResourceUploadForm } from './resource-upload-form';

vi.mock('../lib/api', () => ({
  uploadResources: vi.fn(),
}));

it('offers separate controls for uploading markdown files and folders', () => {
  render(<ResourceUploadForm projectId="project-1" />);

  const fileInput = screen.getByLabelText('Upload markdown files');
  const folderInput = screen.getByLabelText('Upload markdown folder');

  expect(fileInput).toHaveAttribute('type', 'file');
  expect(fileInput).not.toHaveAttribute('webkitdirectory');
  expect(folderInput).toHaveAttribute('type', 'file');
  expect(folderInput).toHaveAttribute('webkitdirectory', '');
});

it('shows a success message after uploading markdown files', async () => {
  vi.mocked(uploadResources).mockResolvedValueOnce({
    resources: [
      {
        id: 'resource-1',
        project_id: 'project-1',
        logical_path: 'alpha.md',
        original_filename: 'alpha.md',
        content_hash: 'hash-1',
        upload_status: 'uploaded',
        created_at: '2026-05-06T00:00:00Z',
      },
      {
        id: 'resource-2',
        project_id: 'project-1',
        logical_path: 'beta.md',
        original_filename: 'beta.md',
        content_hash: 'hash-2',
        upload_status: 'uploaded',
        created_at: '2026-05-06T00:00:00Z',
      },
    ],
  });

  render(<ResourceUploadForm projectId="project-1" />);

  const fileInput = screen.getByLabelText('Upload markdown files');
  const uploadButton = screen.getByRole('button', { name: 'Upload files' });
  const alphaFile = new File(['# Alpha'], 'alpha.md', { type: 'text/markdown' });
  const betaFile = new File(['# Beta'], 'beta.md', { type: 'text/markdown' });

  fireEvent.change(fileInput, {
    target: { files: [alphaFile, betaFile] },
  });
  fireEvent.click(uploadButton);

  await waitFor(() => {
    expect(screen.getByText('Uploaded 2 markdown files.')).toBeInTheDocument();
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
