import type { Annotation } from '../lib/api';
import type { QuoteAnchor } from '../lib/selection-anchor';

import { AnnotationComposer } from './annotation-composer';

type NotesPanelProps = {
  resourceId: string | null;
  annotations: Annotation[];
  isLoading: boolean;
  isError: boolean;
  selectedAnchor: QuoteAnchor | null;
  draftBody: string;
  onDraftBodyChange: (body: string) => void;
  onSave: () => void;
  isSaving: boolean;
};

export function NotesPanel({
  resourceId,
  annotations,
  isLoading,
  isError,
  selectedAnchor,
  draftBody,
  onDraftBodyChange,
  onSave,
  isSaving,
}: NotesPanelProps) {
  let notesContent = <p>No notes yet.</p>;

  if (!resourceId) {
    notesContent = <p>Select a document to review notes.</p>;
  } else if (isLoading) {
    notesContent = <p>Loading notes...</p>;
  } else if (isError) {
    notesContent = <p role="alert">Unable to load notes.</p>;
  } else if (annotations.length) {
    notesContent = (
      <ul>
        {annotations.map((annotation) => (
          <li key={annotation.id}>
            <blockquote>
              <p>{annotation.anchor.quoteText}</p>
            </blockquote>
            <p>{annotation.body}</p>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section aria-label="Notes">
      <h2>Notes</h2>
      {resourceId ? (
        <>
          {selectedAnchor ? (
            <AnnotationComposer
              anchor={selectedAnchor}
              body={draftBody}
              onBodyChange={onDraftBodyChange}
              onSave={onSave}
              isSaving={isSaving}
            />
          ) : (
            <p>Select text in the document to add a note.</p>
          )}
          {notesContent}
        </>
      ) : (
        notesContent
      )}
    </section>
  );
}
