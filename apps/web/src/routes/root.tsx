import { CreateProjectForm } from '../components/create-project-form';
import { ProjectList } from '../components/project-list';
import { ResourceUploadForm } from '../components/resource-upload-form';
import { useProjectsQuery } from '../lib/api';

function RootRouteContent() {
  const { data, isError, isPending } = useProjectsQuery();
  const projects = data?.projects ?? [];
  let projectsContent = <ProjectList projects={projects} />;

  if (isPending) {
    projectsContent = <p>Loading projects...</p>;
  } else if (isError) {
    projectsContent = <p role="alert">Unable to load projects.</p>;
  } else if (!projects.length) {
    projectsContent = <p>Create your first project</p>;
  }

  return (
    <main>
      <h1>Writer Assistance</h1>
      <CreateProjectForm />
      {projectsContent}
      {!isPending && !isError && projects.length ? (
        <section>
          <h2>Resource uploads</h2>
          {projects.map((project) => (
            <section key={project.id}>
              <h3>{project.title}</h3>
              <ResourceUploadForm projectId={project.id} />
            </section>
          ))}
        </section>
      ) : null}
    </main>
  );
}

export function RootRoute() {
  return <RootRouteContent />;
}
