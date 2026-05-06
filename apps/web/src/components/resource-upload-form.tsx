import type { FormEvent } from 'react';
import { useState } from 'react';

import { uploadResources } from '../lib/api';

type ResourceUploadFormProps = {
  projectId: string;
};

export function ResourceUploadForm({ projectId }: ResourceUploadFormProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>, inputName: string) {
    event.preventDefault();

    const form = event.currentTarget;
    const fileInput = form.elements.namedItem(inputName);
    if (!(fileInput instanceof HTMLInputElement)) {
      return;
    }

    const files = Array.from(fileInput.files ?? []);
    if (!files.length) {
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const result = await uploadResources(projectId, files);
      form.reset();
      setSuccessMessage(
        `Uploaded ${result.resources.length} markdown file${result.resources.length === 1 ? '' : 's'}.`,
      );
    } catch {
      setErrorMessage('Unable to upload markdown.');
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div>
      <form onSubmit={(event) => void handleSubmit(event, 'markdown-files')}>
        <label htmlFor={`resource-upload-files-${projectId}`}>Upload markdown files</label>
        <input
          id={`resource-upload-files-${projectId}`}
          name="markdown-files"
          type="file"
          accept=".md,text/markdown"
          multiple
        />
        <button type="submit" disabled={isUploading}>
          {isUploading ? 'Uploading...' : 'Upload files'}
        </button>
      </form>
      <form onSubmit={(event) => void handleSubmit(event, 'markdown-folder')}>
        <label htmlFor={`resource-upload-folder-${projectId}`}>Upload markdown folder</label>
        <input
          id={`resource-upload-folder-${projectId}`}
          name="markdown-folder"
          type="file"
          accept=".md,text/markdown"
          multiple
          ref={(node) => {
            node?.setAttribute('webkitdirectory', '');
          }}
        />
        <button type="submit" disabled={isUploading}>
          {isUploading ? 'Uploading...' : 'Upload folder'}
        </button>
      </form>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {successMessage ? <p>{successMessage}</p> : null}
    </div>
  );
}
