import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { MarkdownViewer } from '../components/markdown-viewer';
import { ResourceTree } from '../components/resource-tree';
import { useResourceContentQuery, useResourcesQuery } from '../lib/api';

export function ProjectRoute() {
  const { projectId } = useParams();
  const [resourceId, setResourceId] = useState<string | null>(null);
  const resourcesQuery = useResourcesQuery(projectId);
  const resourceQuery = useResourceContentQuery(resourceId);

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

  let markdownContent = <MarkdownViewer markdown={resourceQuery.data?.markdown ?? ''} />;

  if (resourceQuery.isPending) {
    markdownContent = <p>Loading document...</p>;
  } else if (resourceQuery.isError) {
    markdownContent = <p role="alert">Unable to load document.</p>;
  }

  return (
    <main className="workspace">
      {resourcesContent}
      {markdownContent}
    </main>
  );
}
