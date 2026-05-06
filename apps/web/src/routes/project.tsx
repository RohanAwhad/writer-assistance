import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { AiSuggestionsPanel } from '../components/ai-suggestions-panel';
import { MarkdownViewer } from '../components/markdown-viewer';
import { NotesPanel } from '../components/notes-panel';
import { ResourceTree } from '../components/resource-tree';
import {
  LENS_CATALOG,
  type LensName,
  useAnnotationsQuery,
  useAcceptAnalysisSuggestionMutation,
  useCreateAnalysisRunMutation,
  useCreateAnnotationMutation,
  useDiscardAnalysisSuggestionMutation,
  useLatestAnalysisRunQuery,
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
  const [selectedLenses, setSelectedLenses] = useState<LensName[]>([...LENS_CATALOG]);
  const resourcesQuery = useResourcesQuery(projectId);
  const resourceQuery = useResourceContentQuery(resourceId);
  const annotationsQuery = useAnnotationsQuery(resourceId);
  const latestAnalysisRunQuery = useLatestAnalysisRunQuery(resourceId);
  const createAnnotationMutation = useCreateAnnotationMutation(projectId);
  const createAnalysisRunMutation = useCreateAnalysisRunMutation(projectId);
  const retryAnalysisRunMutation = useRetryAnalysisRunMutation();
  const acceptAnalysisSuggestionMutation = useAcceptAnalysisSuggestionMutation();
  const discardAnalysisSuggestionMutation = useDiscardAnalysisSuggestionMutation();
  const latestAnalysisRun = latestAnalysisRunQuery.data ?? null;
  const isPersistedAnalysisInProgress =
    latestAnalysisRun?.generation_state === 'queued' ||
    latestAnalysisRun?.generation_state === 'running';
  const isRunningAnalysis =
    createAnalysisRunMutation.isPending ||
    retryAnalysisRunMutation.isPending ||
    isPersistedAnalysisInProgress;

  useEffect(() => {
    setSelectedAnchor(null);
    setDraftBody('');
    setSelectedLenses([...LENS_CATALOG]);
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
    if (!resourceId || selectedLenses.length === 0) {
      return;
    }

    await createAnalysisRunMutation.mutateAsync({
      resource_id: resourceId,
      lenses: selectedLenses,
    });
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

  function handleToggleLens(lens: LensName) {
    setSelectedLenses((current) =>
      current.includes(lens)
        ? current.filter((selectedLens) => selectedLens !== lens)
        : LENS_CATALOG.filter(
            (candidateLens) => candidateLens === lens || current.includes(candidateLens),
          ),
    );
  }

  const analysisErrorMessage = createAnalysisRunMutation.isError
    ? 'Unable to run analysis.'
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
        selectedLenses={selectedLenses}
        onToggleLens={handleToggleLens}
        onRunAnalysis={handleRunAnalysis}
        onRetryFailed={handleRetryAnalysis}
        isRunningAnalysis={isRunningAnalysis}
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
