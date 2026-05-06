import { Link } from 'react-router-dom';

import type { Project } from '../lib/api';

type ProjectListProps = {
  projects: Project[];
};

export function ProjectList({ projects }: ProjectListProps) {
  if (!projects.length) {
    return null;
  }

  return (
    <section>
      <h2>Projects</h2>
      <ul>
        {projects.map((project) => (
          <li key={project.id}>
            <Link to={`/projects/${project.id}`}>{project.title}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
