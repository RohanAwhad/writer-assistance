import type {
  AnalysisRun,
  AnalysisSuggestion,
  LensName,
} from '../lib/api';

import { LensPicker } from './lens-picker';

type AiSuggestionsPanelProps = {
  resourceId: string | null;
  selectedLenses: LensName[];
  onToggleLens: (lens: LensName) => void;
  onRunAnalysis: () => void;
  onRetryFailed: () => void;
  isRunningAnalysis: boolean;
  isRetryingFailed: boolean;
  analysisRun: AnalysisRun | null;
  onAcceptSuggestion: (suggestionId: string) => void;
  onDiscardSuggestion: (suggestionId: string) => void;
  isAcceptingSuggestion: boolean;
  isDiscardingSuggestion: boolean;
  errorMessage: string | null;
};

const LENS_LABELS: Record<LensName, string> = {
  financial: 'financial',
  real_estate: 'real_estate',
  political: 'political',
  software_engineering: 'software_engineering',
};

export function AiSuggestionsPanel({
  resourceId,
  selectedLenses,
  onToggleLens,
  onRunAnalysis,
  onRetryFailed,
  isRunningAnalysis,
  isRetryingFailed,
  analysisRun,
  onAcceptSuggestion,
  onDiscardSuggestion,
  isAcceptingSuggestion,
  isDiscardingSuggestion,
  errorMessage,
}: AiSuggestionsPanelProps) {
  const failedLenses =
    analysisRun?.lens_results.filter((lensResult) => lensResult.generation_state === 'failed') ?? [];
  const activeSuggestions = analysisRun
    ? analysisRun.lens_results.flatMap((lensResult) =>
        lensResult.suggestions.filter((suggestion) => suggestion.review_state === 'unreviewed'),
      )
    : [];
  const isGenerationInProgress =
    analysisRun?.generation_state === 'queued' || analysisRun?.generation_state === 'running';
  const showGenerationState = isGenerationInProgress || (isRunningAnalysis && analysisRun === null);

  let content = <p>Select a document to analyze.</p>;

  if (resourceId) {
    content = (
      <>
        <LensPicker
          selectedLenses={selectedLenses}
          onToggleLens={onToggleLens}
          disabled={isRunningAnalysis || isRetryingFailed}
        />
        <button
          type="button"
          onClick={onRunAnalysis}
          disabled={selectedLenses.length === 0 || isRunningAnalysis}
        >
          {isRunningAnalysis ? 'Running analysis...' : 'Run analysis'}
        </button>
        {errorMessage ? <p role="alert">{errorMessage}</p> : null}
        {failedLenses.length > 0 ? (
          <>
            <p>{`Failed lenses: ${failedLenses.map((lensResult) => lensResult.lens).join(', ')}`}</p>
            <button type="button" onClick={onRetryFailed} disabled={isRetryingFailed}>
              {isRetryingFailed ? 'Retrying failed lenses...' : 'Retry failed lenses'}
            </button>
          </>
        ) : null}
        {analysisRun ? (
          showGenerationState ? (
            <p>Generating AI suggestions...</p>
          ) : activeSuggestions.length > 0 ? (
            <ul>
              {activeSuggestions.map((suggestion) => (
                <li key={suggestion.id}>
                  <p>{humanizeLens(suggestion.lens)}</p>
                  <blockquote>
                    <p>{suggestion.anchor.quoteText}</p>
                  </blockquote>
                  <p>{suggestion.body}</p>
                  <button
                    type="button"
                    onClick={() => onAcceptSuggestion(suggestion.id)}
                    disabled={isAcceptingSuggestion || isDiscardingSuggestion}
                  >
                    Accept suggestion
                  </button>
                  <button
                    type="button"
                    onClick={() => onDiscardSuggestion(suggestion.id)}
                    disabled={isAcceptingSuggestion || isDiscardingSuggestion}
                  >
                    Discard suggestion
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>No AI suggestions awaiting review.</p>
          )
        ) : (
          <p>
            {showGenerationState
              ? 'Generating AI suggestions...'
              : 'Run analysis on this document to generate suggestions.'}
          </p>
        )}
      </>
    );
  }

  return (
    <section aria-label="AI suggestions">
      <h2>AI suggestions</h2>
      {content}
    </section>
  );
}

function humanizeLens(lens: AnalysisSuggestion['lens']) {
  return LENS_LABELS[lens].replace('_', ' ');
}
