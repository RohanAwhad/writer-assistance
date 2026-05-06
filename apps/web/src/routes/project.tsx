import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { AiSuggestionsPanel } from '../components/ai-suggestions-panel';
import { MarkdownViewer } from '../components/markdown-viewer';
import { NotesPanel } from '../components/notes-panel';
import { ResourceTree } from '../components/resource-tree';
import {
  isAnalysisRunActive,
  useAnnotationsQuery,
  useAcceptAnalysisSuggestionMutation,
  useCreateAnalysisRunMutation,
  useCreateAnnotationMutation,
  useDiscardAnalysisSuggestionMutation,
  useLatestAnalysisRunQuery,
  useRegenerateLensesMutation,
  useResourceContentQuery,
  useRetryAnalysisRunMutation,
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
  const latestAnalysisRunQuery = useLatestAnalysisRunQuery(resourceId);
  const createAnnotationMutation = useCreateAnnotationMutation(projectId);
  const createAnalysisRunMutation = useCreateAnalysisRunMutation(projectId);
  const regenerateLensesMutation = useRegenerateLensesMutation();
  const retryAnalysisRunMutation = useRetryAnalysisRunMutation();
  const acceptAnalysisSuggestionMutation = useAcceptAnalysisSuggestionMutation();
  const discardAnalysisSuggestionMutation = useDiscardAnalysisSuggestionMutation();
  const latestAnalysisRun = latestAnalysisRunQuery.data ?? null;
  const isLatestAnalysisRunLoading = Boolean(resourceId) && latestAnalysisRunQuery.isPending;
  const isPersistedAnalysisInProgress = isAnalysisRunActive(latestAnalysisRun);
  const isRunningAnalysis =
    createAnalysisRunMutation.isPending ||
    regenerateLensesMutation.isPending ||
    retryAnalysisRunMutation.isPending ||
    isPersistedAnalysisInProgress;

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

  async function handleRunAnalysis() {
    if (!resourceId) {
      return;
    }

    await createAnalysisRunMutation.mutateAsync({
      resource_id: resourceId,
    });
  }

  async function handleRegenerateLenses() {
    if (!resourceId) {
      return;
    }

    await regenerateLensesMutation.mutateAsync(resourceId);
  }

  async function handleRetryAnalysis() {
    if (!latestAnalysisRunQuery.data) {
      return;
    }

    await retryAnalysisRunMutation.mutateAsync(latestAnalysisRunQuery.data.id);
  }

  async function handleAcceptSuggestion(suggestionId: string) {
    await acceptAnalysisSuggestionMutation.mutateAsync(suggestionId);
  }

  async function handleDiscardSuggestion(suggestionId: string) {
    await discardAnalysisSuggestionMutation.mutateAsync(suggestionId);
  }

  const analysisErrorMessage = createAnalysisRunMutation.isError
    ? 'Unable to run analysis.'
    : regenerateLensesMutation.isError
      ? 'Unable to regenerate lenses.'
    : retryAnalysisRunMutation.isError
      ? 'Unable to retry analysis.'
      : acceptAnalysisSuggestionMutation.isError
        ? 'Unable to accept suggestion.'
        : discardAnalysisSuggestionMutation.isError
          ? 'Unable to discard suggestion.'
          : latestAnalysisRunQuery.isError
            ? 'Unable to load AI suggestions.'
          : null;

  return (
    <main className="workspace">
      {resourcesContent}
      {markdownContent}
      <AiSuggestionsPanel
        resourceId={resourceId}
        isLatestAnalysisRunLoading={isLatestAnalysisRunLoading}
        onRunAnalysis={handleRunAnalysis}
        onRegenerateLenses={handleRegenerateLenses}
        onRetryFailed={handleRetryAnalysis}
        isRunningAnalysis={isRunningAnalysis}
        isRegeneratingLenses={regenerateLensesMutation.isPending}
        isRetryingFailed={retryAnalysisRunMutation.isPending}
        analysisRun={latestAnalysisRun}
        onAcceptSuggestion={handleAcceptSuggestion}
        onDiscardSuggestion={handleDiscardSuggestion}
        isAcceptingSuggestion={acceptAnalysisSuggestionMutation.isPending}
        isDiscardingSuggestion={discardAnalysisSuggestionMutation.isPending}
        errorMessage={analysisErrorMessage}
      />
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
