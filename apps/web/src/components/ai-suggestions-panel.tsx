import {
  type AnalysisRun,
  canRetryAnalysisRun,
  isLensDiscoveryActive,
  isSuggestionGenerationActive,
} from '../lib/api';

import { LensPicker } from './lens-picker';

type AiSuggestionsPanelProps = {
  resourceId: string | null;
  isLatestAnalysisRunLoading: boolean;
  onRunAnalysis: () => void;
  onRegenerateLenses: () => void;
  onRetryFailed: () => void;
  isRunningAnalysis: boolean;
  isRegeneratingLenses: boolean;
  isRetryingFailed: boolean;
  analysisRun: AnalysisRun | null;
  onAcceptSuggestion: (suggestionId: string) => void;
  onDiscardSuggestion: (suggestionId: string) => void;
  isAcceptingSuggestion: boolean;
  isDiscardingSuggestion: boolean;
  errorMessage: string | null;
};

export function AiSuggestionsPanel({
  resourceId,
  isLatestAnalysisRunLoading,
  onRunAnalysis,
  onRegenerateLenses,
  onRetryFailed,
  isRunningAnalysis,
  isRegeneratingLenses,
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
  const showDiscoveryState = isLensDiscoveryActive(analysisRun);
  const showGenerationState = isSuggestionGenerationActive(analysisRun);
  const showRetryFailedAction = canRetryAnalysisRun(analysisRun);
  const discoveryFailureMessage =
    analysisRun?.lens_discovery_status === 'failed'
      ? (analysisRun.error_summary ?? 'Lens discovery failed. Regenerate lenses to try again.')
      : null;

  let content = <p>Select a document to analyze.</p>;

  if (resourceId) {
    content = (
      <>
        {analysisRun ? (
          <button
            type="button"
            onClick={onRegenerateLenses}
            disabled={isRegeneratingLenses || isRunningAnalysis}
          >
            {isRegeneratingLenses ? 'Regenerating lenses...' : 'Regenerate lenses'}
          </button>
        ) : isLatestAnalysisRunLoading ? (
          <p>Checking for an existing analysis run...</p>
        ) : (
          <button type="button" onClick={onRunAnalysis} disabled={isRunningAnalysis}>
            {isRunningAnalysis ? 'Running analysis...' : 'Run analysis'}
          </button>
        )}
        {errorMessage ? <p role="alert">{errorMessage}</p> : null}
        {discoveryFailureMessage ? <p role="alert">{discoveryFailureMessage}</p> : null}
        {showDiscoveryState ? <p>Discovering lenses...</p> : null}
        {showGenerationState ? <p>Generating suggestions...</p> : null}
        {analysisRun?.discovered_lenses.length ? (
          <LensPicker discoveredLenses={analysisRun.discovered_lenses} />
        ) : null}
        {failedLenses.length > 0 ? (
          <>
            <p>{`Failed lenses: ${failedLenses.map((lensResult) => lensResult.lens).join(', ')}`}</p>
            {showRetryFailedAction ? (
              <button type="button" onClick={onRetryFailed} disabled={isRetryingFailed}>
                {isRetryingFailed ? 'Retrying failed lenses...' : 'Retry failed lenses'}
              </button>
            ) : null}
          </>
        ) : null}
        {analysisRun ? (
          activeSuggestions.length > 0 ? (
            <ul>
              {activeSuggestions.map((suggestion) => (
                <li key={suggestion.id}>
                  <p>{suggestion.lens}</p>
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
          ) : discoveryFailureMessage ? null : !showDiscoveryState && !showGenerationState ? (
            <p>No AI suggestions awaiting review.</p>
          ) : null
        ) : isLatestAnalysisRunLoading ? null : (
          <p>
            Run analysis on this document to generate suggestions.
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
