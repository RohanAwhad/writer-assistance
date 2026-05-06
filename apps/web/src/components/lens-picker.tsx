import type { LensName } from '../lib/api';

const LENS_LABELS: Record<LensName, string> = {
  financial: 'Financial',
  real_estate: 'Real estate',
  political: 'Political',
  software_engineering: 'Software engineering',
};

type LensPickerProps = {
  selectedLenses: LensName[];
  onToggleLens: (lens: LensName) => void;
  disabled?: boolean;
};

export function LensPicker({
  selectedLenses,
  onToggleLens,
  disabled = false,
}: LensPickerProps) {
  return (
    <fieldset disabled={disabled}>
      <legend>Analysis lenses</legend>
      {Object.entries(LENS_LABELS).map(([lens, label]) => (
        <label key={lens}>
          <input
            type="checkbox"
            checked={selectedLenses.includes(lens as LensName)}
            onChange={() => onToggleLens(lens as LensName)}
          />
          {label}
        </label>
      ))}
    </fieldset>
  );
}
