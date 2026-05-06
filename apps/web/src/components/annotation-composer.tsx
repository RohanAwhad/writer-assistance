import type { FormEvent } from 'react';

import type { QuoteAnchor } from '../lib/selection-anchor';

type AnnotationComposerProps = {
  anchor: QuoteAnchor;
  body: string;
  onBodyChange: (body: string) => void;
  onSave: () => void;
  isSaving: boolean;
};

export function AnnotationComposer({
  anchor,
  body,
  onBodyChange,
  onSave,
  isSaving,
}: AnnotationComposerProps) {
  const isDisabled = !body.trim() || isSaving;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isDisabled) {
      return;
    }

    onSave();
  }

  return (
    <form onSubmit={handleSubmit}>
      <h3>New note</h3>
      <blockquote>
        <p>{anchor.quoteText}</p>
      </blockquote>
      <label>
        Note
        <textarea value={body} onChange={(event) => onBodyChange(event.target.value)} rows={4} />
      </label>
      <div>
        <button type="submit" disabled={isDisabled}>
          {isSaving ? 'Saving...' : 'Save note'}
        </button>
      </div>
    </form>
  );
}
