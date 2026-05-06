import { getLatestAnalysisRunPollIntervalMs, type AnalysisRun } from './api';

function buildAnalysisRun(generationState: AnalysisRun['generation_state']): AnalysisRun {
  return {
    id: 'run-1',
    project_id: 'project-1',
    resource_id: 'resource-1',
    generation_state: generationState,
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
