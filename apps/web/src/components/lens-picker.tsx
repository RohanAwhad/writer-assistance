import type { DiscoveredLens } from '../lib/api';

type LensPickerProps = {
  discoveredLenses: DiscoveredLens[];
};

export function LensPicker({ discoveredLenses }: LensPickerProps) {
  return (
    <section aria-label="Discovered analysis lenses">
      <h3>Analysis lenses</h3>
      <ul>
        {discoveredLenses.map((lens) => (
          <li key={lens.name}>
            <p>
              <strong>{lens.name}</strong>
            </p>
            <p>{lens.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
