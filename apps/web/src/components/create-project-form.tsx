import type { FormEvent } from 'react';
import { useState } from 'react';

import { useCreateProjectMutation } from '../lib/api';

export function CreateProjectForm() {
  const [title, setTitle] = useState('');
  const createProjectMutation = useCreateProjectMutation();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      return;
    }

    createProjectMutation.mutate(
      { title: trimmedTitle },
      {
        onSuccess: () => {
          setTitle('');
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="project-title">Project title</label>
      <input
        id="project-title"
        name="title"
        value={title}
        onChange={(event) => {
          setTitle(event.target.value);
        }}
      />
      <button type="submit" disabled={createProjectMutation.isPending || title.trim().length === 0}>
        Create project
      </button>
      {createProjectMutation.isError ? <p role="alert">Unable to create project.</p> : null}
    </form>
  );
}
