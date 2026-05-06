import type { ReactNode } from 'react';

import type { Resource } from '../lib/api';

type ResourceTreeProps = {
  resources: Resource[];
  selectedResourceId: string | null;
  onSelect: (resourceId: string) => void;
};

type ResourceTreeNode =
  | {
      kind: 'folder';
      name: string;
      children: Map<string, ResourceTreeNode>;
    }
  | {
      kind: 'file';
      name: string;
      resource: Resource;
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
      <ul>{renderNodes(buildResourceTree(resources), selectedResourceId, onSelect)}</ul>
    </section>
  );
}

function buildResourceTree(resources: Resource[]): ResourceTreeNode[] {
  const root = new Map<string, ResourceTreeNode>();

  for (const resource of resources) {
    const segments = resource.logical_path.split('/');
    let currentChildren = root;

    segments.forEach((segment, index) => {
      const isFile = index === segments.length - 1;

      if (isFile) {
        currentChildren.set(segment, {
          kind: 'file',
          name: segment,
          resource,
        });
        return;
      }

      const existingNode = currentChildren.get(segment);
      if (existingNode?.kind === 'folder') {
        currentChildren = existingNode.children;
        return;
      }

      const folderNode: ResourceTreeNode = {
        kind: 'folder',
        name: segment,
        children: new Map<string, ResourceTreeNode>(),
      };
      currentChildren.set(segment, folderNode);
      currentChildren = folderNode.children;
    });
  }

  return sortNodes([...root.values()]);
}

function sortNodes(nodes: ResourceTreeNode[]): ResourceTreeNode[] {
  return nodes
    .slice()
    .sort((left, right) => {
      if (left.kind === right.kind) {
        return left.name.localeCompare(right.name);
      }

      return left.kind === 'folder' ? -1 : 1;
    });
}

function renderNodes(
  nodes: ResourceTreeNode[],
  selectedResourceId: string | null,
  onSelect: (resourceId: string) => void,
  parentPath = '',
): ReactNode {
  return nodes.map((node) => {
    const nodePath = parentPath ? `${parentPath}/${node.name}` : node.name;

    if (node.kind === 'folder') {
      return (
        <li key={nodePath}>
          <span>{node.name}</span>
          <ul>{renderNodes(sortNodes([...node.children.values()]), selectedResourceId, onSelect, nodePath)}</ul>
        </li>
      );
    }

    return (
      <li key={node.resource.id}>
        <button
          type="button"
          aria-pressed={node.resource.id === selectedResourceId}
          onClick={() => onSelect(node.resource.id)}
        >
          {node.name}
        </button>
      </li>
    );
  });
}
