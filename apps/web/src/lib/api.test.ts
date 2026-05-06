import { canRetryAnalysisRun, getLatestAnalysisRunPollIntervalMs, type AnalysisRun } from './api';

function buildAnalysisRun(
  generationState: AnalysisRun['generation_state'],
  lensDiscoveryStatus: AnalysisRun['lens_discovery_status'] = 'succeeded',
): AnalysisRun {
  return {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    lens_discovery_status: lensDiscoveryStatus,
    discovered_lenses: [],
    generation_state: generationState,
    error_summary: null,
    lens_results: [],
    created_at: '2026-05-05T00:00:00Z',
    updated_at: '2026-05-05T00:00:00Z',
  };
}

it('uses a sane poll interval for queued and running analysis runs', () => {
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('queued'))).toBe(1500);
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('running'))).toBe(1500);
});

it('stops polling once the analysis run is terminal or absent', () => {
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('succeeded'))).toBe(false);
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('completed_with_failures'))).toBe(false);
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('failed'))).toBe(false);
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('cancelled'))).toBe(false);
  expect(getLatestAnalysisRunPollIntervalMs(null)).toBe(false);
  expect(getLatestAnalysisRunPollIntervalMs(undefined)).toBe(false);
});

it('treats cancelled lens discovery as terminal even if generation still looks queued', () => {
  expect(getLatestAnalysisRunPollIntervalMs(buildAnalysisRun('queued', 'cancelled'))).toBe(false);
});

it('allows retry only after a failed run becomes terminal', () => {
  const activeRun = buildAnalysisRun('running');
  activeRun.lens_results = [
    {
      id: 'lens-result-1',
      lens: 'Demand trend',
      generation_state: 'failed',
      error_message: 'Lens timed out',
      suggestions: [],
    },
  ];

  const terminalRun = buildAnalysisRun('completed_with_failures');
  terminalRun.lens_results = [
    {
      id: 'lens-result-1',
      lens: 'Demand trend',
      generation_state: 'failed',
      error_message: 'Lens timed out',
      suggestions: [],
    },
  ];

  expect(canRetryAnalysisRun(activeRun)).toBe(false);
  expect(canRetryAnalysisRun(terminalRun)).toBe(true);
  expect(canRetryAnalysisRun(buildAnalysisRun('failed'))).toBe(false);
});
