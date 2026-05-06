import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { MarkdownViewer } from '../components/markdown-viewer';
import { NotesPanel } from '../components/notes-panel';
import { ResourceTree } from '../components/resource-tree';
import {
  useAnnotationsQuery,
  useCreateAnnotationMutation,
  useResourceContentQuery,
  useResourcesQuery,
} from '../lib/api';
import type { QuoteAnchor } from '../lib/selection-anchor';

export function ProjectRoute() {
  const { projectId } = useParams();
  const [resourceId, setResourceId] = useState<string | null>(null);
  const [selectedAnchor, setSelectedAnchor] = useState<QuoteAnchor | null>(null);
  const [draftBody, setDraftBody] = useState('');
  const resourcesQuery = useResourcesQuery(projectId);
  const resourceQuery = useResourceContentQuery(resourceId);
  const annotationsQuery = useAnnotationsQuery(resourceId);
  const createAnnotationMutation = useCreateAnnotationMutation(projectId);

  useEffect(() => {
    setSelectedAnchor(null);
    setDraftBody('');
    window.getSelection()?.removeAllRanges();
  }, [resourceId]);

  if (!projectId) {
    return <p role="alert">Project not found.</p>;
  }

  let resourcesContent = (
    <ResourceTree
      resources={resourcesQuery.data?.resources ?? []}
      selectedResourceId={resourceId}
      onSelect={setResourceId}
    />
  );

  if (resourcesQuery.isPending) {
    resourcesContent = <p>Loading resources...</p>;
  } else if (resourcesQuery.isError) {
    resourcesContent = <p role="alert">Unable to load resources.</p>;
  }

  let markdownContent = <p>Select a document to preview.</p>;

  if (resourceId) {
    markdownContent = (
      <MarkdownViewer
        markdown={resourceQuery.data?.markdown ?? ''}
        onQuoteSelection={setSelectedAnchor}
      />
    );

    if (resourceQuery.isPending) {
      markdownContent = <p>Loading document...</p>;
    } else if (resourceQuery.isError) {
      markdownContent = <p role="alert">Unable to load document.</p>;
    }
  }

  async function handleSaveAnnotation() {
    if (!resourceId || !selectedAnchor || !draftBody.trim()) {
      return;
    }

    await createAnnotationMutation.mutateAsync({
      resource_id: resourceId,
      body: draftBody.trim(),
      anchor: selectedAnchor,
    });
    setSelectedAnchor(null);
    setDraftBody('');
    window.getSelection()?.removeAllRanges();
  }

  return (
    <main className="workspace">
      {resourcesContent}
      {markdownContent}
      <NotesPanel
        resourceId={resourceId}
        annotations={annotationsQuery.data?.annotations ?? []}
        isLoading={annotationsQuery.isPending}
        isError={annotationsQuery.isError}
        selectedAnchor={selectedAnchor}
        draftBody={draftBody}
        onDraftBodyChange={setDraftBody}
        onSave={handleSaveAnnotation}
        isSaving={createAnnotationMutation.isPending}
      />
    </main>
  );
}
