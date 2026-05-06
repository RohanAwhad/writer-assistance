import type { Resource } from '../lib/api';

type ResourceTreeProps = {
  resources: Resource[];
  selectedResourceId: string | null;
  onSelect: (resourceId: string) => void;
};

export function ResourceTree({
  resources,
  selectedResourceId,
  onSelect,
}: ResourceTreeProps) {
  if (!resources.length) {
    return <p>No resources yet.</p>;
  }

  return (
    <section>
      <h2>Resources</h2>
      <ul>
        {resources.map((resource) => (
          <li key={resource.id}>
            <button
              type="button"
              aria-pressed={resource.id === selectedResourceId}
              onClick={() => onSelect(resource.id)}
            >
              {resource.logical_path}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
