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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const fileInput = event.currentTarget.elements.namedItem('files');
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
      event.currentTarget.reset();
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
    <form onSubmit={handleSubmit}>
      <label htmlFor={`resource-upload-${projectId}`}>Upload markdown</label>
      <input
        id={`resource-upload-${projectId}`}
        name="files"
        type="file"
        accept=".md,text/markdown"
        multiple
        ref={(node) => {
          node?.setAttribute('webkitdirectory', '');
        }}
      />
      <button type="submit" disabled={isUploading}>
        {isUploading ? 'Uploading...' : 'Upload markdown'}
      </button>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {successMessage ? <p>{successMessage}</p> : null}
    </form>
  );
}
