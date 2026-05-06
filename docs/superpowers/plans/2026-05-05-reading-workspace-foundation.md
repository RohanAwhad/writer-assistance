# Reading Workspace Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working single-user vertical slice that lets the user create projects, upload markdown resources, read them in a rendered workspace, create quote-anchored notes, and trigger/review visible AI suggestions for the current resource after the AI first discovers document-specific analysis lenses.

**Architecture:** Use a Python backend in `apps/api` and a React/TypeScript frontend in `apps/web`. The backend exposes a typed JSON API with FastAPI, persists metadata in SQLite via SQLAlchemy 2.0, stores uploaded markdown files on local disk behind a storage abstraction, and runs AI analysis as explicit background analysis runs with lens discovery status, discovered lens metadata, and per-lens status tracking.

**Tech Stack:** Python 3.12, `uv`, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, pytest, mypy, `anthropic[vertex]`, React, Vite, TypeScript, React Router, TanStack Query, Vitest, Testing Library, Playwright

---

## Scope For This Plan

This plan intentionally covers only the first executable slice of the approved spec:

- included
  - project creation
  - markdown upload with folder-path preservation
  - rendered reading workspace
  - quote-anchored user notes
  - user-triggered AI suggestion analysis with first-run lens discovery
  - latest-run-only AI suggestion panel behavior
  - suggestion accept and discard flows
- deferred to a follow-on plan
  - AI-authored draft generation
  - paragraph-block editor
  - markdown export

## Concrete V1 Decisions This Plan Locks In

- `v1` runs as a local single-user web app on one machine.
- The backend uses Python, and backend static typing is enforced with `mypy --strict`.
- Backend persistence uses SQLite at `./data/app.db`.
- Uploaded markdown resources are stored on local disk at `./data/storage`.
- AI analysis is explicitly user-triggered from the current resource view.
- AI analysis uses the Anthropic Vertex Python SDK via `from anthropic import AnthropicVertex`.
- The analysis model is fixed to `claude-sonnet-4-5@20250929`.
- The backend reads `ANTHROPIC_VERTEX_PROJECT_ID` and `CLOUD_ML_REGION` from the environment for Vertex configuration.
- The lens set is open-ended and discovered from the current resource content.
- The first analysis run for a resource discovers lenses and then immediately generates suggestions from them.
- Discovered lenses are read-only in `v1`.
- `Regenerate lenses` always creates a fresh run with fresh discovery.
- `Retry failed lenses` reruns only failed suggestion generation and does not rediscover lenses.
- The AI panel always renders only the latest analysis run for the selected resource.
- Accepted AI suggestions persist as user-owned notes even when a later run replaces the AI panel view.
- Quote anchors use this minimum schema:
  - `quoteText`
  - `normalizedText`
  - `startOffset`
  - `endOffset`
  - `blockPath`
  - `resolutionStatus` (`exact | fuzzy | unresolved`)
- Suggestion generation state is tracked separately from user review state:
  - lens discovery state: `queued | running | succeeded | failed`
  - analysis run generation state: `queued | running | succeeded | completed_with_failures | failed | cancelled`
  - per-lens generation state: `queued | running | succeeded | failed | cancelled`
  - suggestion review state: `unreviewed | accepted | discarded`

## Planned File Structure

### Root

- `.gitignore` - ignore Python, Node, build, and local data artifacts
- `Makefile` - developer commands for backend, frontend, tests, and type checking
- `package.json` - root Playwright and frontend orchestration scripts
- `pnpm-workspace.yaml` - workspace config for `apps/web`
- `playwright.config.ts` - browser smoke test runner
- `README.md` - setup and run instructions
- `devlogs.md` - append implementation progress after every task

### Backend

- `apps/api/.python-version`
- `apps/api/pyproject.toml`
- `apps/api/alembic.ini`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/0001_create_projects.py`
- `apps/api/alembic/versions/0002_create_resources.py`
- `apps/api/alembic/versions/0003_enforce_resource_logical_path_uniqueness.py`
- `apps/api/alembic/versions/0004_create_annotations.py`
- `apps/api/alembic/versions/0005_create_analysis_runs.py`
- `apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py`
- `apps/api/src/writer_assistance_api/__init__.py`
- `apps/api/src/writer_assistance_api/main.py`
- `apps/api/src/writer_assistance_api/app.py`
- `apps/api/src/writer_assistance_api/config.py`
- `apps/api/src/writer_assistance_api/db.py`
- `apps/api/src/writer_assistance_api/models.py`
- `apps/api/src/writer_assistance_api/storage.py`
- `apps/api/src/writer_assistance_api/disk_storage.py`
- `apps/api/src/writer_assistance_api/background.py`
- `apps/api/src/writer_assistance_api/schemas/projects.py`
- `apps/api/src/writer_assistance_api/schemas/resources.py`
- `apps/api/src/writer_assistance_api/schemas/annotations.py`
- `apps/api/src/writer_assistance_api/schemas/analysis_runs.py`
- `apps/api/src/writer_assistance_api/routes/health.py`
- `apps/api/src/writer_assistance_api/routes/projects.py`
- `apps/api/src/writer_assistance_api/routes/resources.py`
- `apps/api/src/writer_assistance_api/routes/annotations.py`
- `apps/api/src/writer_assistance_api/routes/analysis_runs.py`
- `apps/api/src/writer_assistance_api/services/projects.py`
- `apps/api/src/writer_assistance_api/services/resources.py`
- `apps/api/src/writer_assistance_api/services/annotations.py`
- `apps/api/src/writer_assistance_api/services/analysis_runs.py`
- `apps/api/src/writer_assistance_api/ai/client.py`
- `apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py`
- `apps/api/src/writer_assistance_api/ai/fake_client.py`
- `apps/api/tests/test_health.py`
- `apps/api/tests/test_projects_api.py`
- `apps/api/tests/test_resources_api.py`
- `apps/api/tests/test_annotations_api.py`
- `apps/api/tests/test_analysis_runs_api.py`

### Frontend

- `apps/web/package.json`
- `apps/web/tsconfig.json`
- `apps/web/vite.config.ts`
- `apps/web/index.html`
- `apps/web/src/main.tsx`
- `apps/web/src/App.tsx`
- `apps/web/src/app/router.tsx`
- `apps/web/src/app/query-client.ts`
- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/selection-anchor.ts`
- `apps/web/src/routes/root.tsx`
- `apps/web/src/routes/root.test.tsx`
- `apps/web/src/routes/project.tsx`
- `apps/web/src/routes/project.test.tsx`
- `apps/web/src/components/project-list.tsx`
- `apps/web/src/components/create-project-form.tsx`
- `apps/web/src/components/resource-upload-form.tsx`
- `apps/web/src/components/resource-tree.tsx`
- `apps/web/src/components/markdown-viewer.tsx`
- `apps/web/src/components/annotation-composer.tsx`
- `apps/web/src/components/notes-panel.tsx`
- `apps/web/src/components/lens-picker.tsx`
- `apps/web/src/components/ai-suggestions-panel.tsx`
- `apps/web/e2e/reading-workspace.spec.ts`

## Task 1: Bootstrap The Python API And Health Check

**Files:**
- Create: `.gitignore`
- Create: `Makefile`
- Create: `apps/api/.python-version`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/writer_assistance_api/__init__.py`
- Create: `apps/api/src/writer_assistance_api/main.py`
- Create: `apps/api/src/writer_assistance_api/app.py`
- Create: `apps/api/src/writer_assistance_api/routes/health.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write the failing backend health-route test**

```python
# apps/api/tests/test_health.py
from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --project apps/api pytest apps/api/tests/test_health.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'writer_assistance_api'`.

- [ ] **Step 3: Add the Python project, strict mypy config, and the minimal FastAPI app**

```toml
# apps/api/pyproject.toml
[project]
name = "writer-assistance-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
]

[dependency-groups]
dev = [
  "mypy>=1.10.0",
  "pytest>=8.3.0",
  "httpx>=0.27.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = []
```

```python
# apps/api/src/writer_assistance_api/app.py
from fastapi import FastAPI

from writer_assistance_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Writer Assistance API")
    app.include_router(health_router)
    return app
```

```python
# apps/api/src/writer_assistance_api/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# apps/api/src/writer_assistance_api/main.py
from writer_assistance_api.app import create_app

app = create_app()
```

```makefile
# Makefile
api-dev:
	uv run --project apps/api uvicorn writer_assistance_api.main:app --reload --app-dir apps/api/src --port 8000

api-test:
	uv run --project apps/api pytest apps/api/tests -q

api-typecheck:
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
```

- [ ] **Step 4: Sync dependencies and rerun test plus mypy**

Run: `uv sync --project apps/api && uv run --project apps/api pytest apps/api/tests/test_health.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src`

Expected: PASS with `1 passed` and mypy reporting `Success: no issues found`.

- [ ] **Step 5: Log the task and commit**

```md
# devlogs.md append
- Bootstrapped the Python FastAPI backend with a strict mypy baseline and a health route.
```

```bash
git add .gitignore Makefile apps/api/.python-version apps/api/pyproject.toml apps/api/src apps/api/tests/test_health.py devlogs.md
git commit -m "chore: bootstrap python api health check"
```

## Task 2: Add SQLite, Alembic, Project APIs, And The Web Shell

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_create_projects.py`
- Create: `apps/api/src/writer_assistance_api/config.py`
- Create: `apps/api/src/writer_assistance_api/db.py`
- Create: `apps/api/src/writer_assistance_api/models.py`
- Create: `apps/api/src/writer_assistance_api/schemas/projects.py`
- Create: `apps/api/src/writer_assistance_api/services/projects.py`
- Create: `apps/api/src/writer_assistance_api/routes/projects.py`
- Create: `apps/api/tests/test_projects_api.py`
- Modify: `apps/api/src/writer_assistance_api/app.py`
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/app/router.tsx`
- Create: `apps/web/src/app/query-client.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/routes/root.tsx`
- Create: `apps/web/src/routes/root.test.tsx`
- Create: `apps/web/src/components/project-list.tsx`
- Create: `apps/web/src/components/create-project-form.tsx`

- [ ] **Step 1: Write the failing project API and landing-page tests**

```python
# apps/api/tests/test_projects_api.py
from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_create_and_list_projects() -> None:
    client = TestClient(create_app(database_url="sqlite+pysqlite:///:memory:"))

    create_response = client.post("/projects", json={"title": "Municipal Housing Brief"})
    assert create_response.status_code == 201

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    assert list_response.json()["projects"][0]["title"] == "Municipal Housing Brief"
```

```tsx
// apps/web/src/routes/root.test.tsx
import { render, screen } from '@testing-library/react';
import { RootRoute } from './root';

it('shows the project empty state', () => {
  render(<RootRoute />);
  expect(screen.getByText('Create your first project')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --project apps/api pytest apps/api/tests/test_projects_api.py -q && pnpm install && pnpm --dir apps/web vitest run src/routes/root.test.tsx`

Expected: FAIL because the DB layer, project routes, and web shell do not exist yet.

- [ ] **Step 3: Add SQLAlchemy models, Alembic migration, and project routes**

```python
# apps/api/src/writer_assistance_api/models.py
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

```python
# apps/api/src/writer_assistance_api/schemas/projects.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
```

```python
# apps/api/src/writer_assistance_api/routes/projects.py
from fastapi import APIRouter, Depends, status

from writer_assistance_api.schemas.projects import CreateProjectRequest, ProjectResponse
from writer_assistance_api.services.projects import ProjectsService, get_projects_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(service: ProjectsService = Depends(get_projects_service)) -> dict[str, list[ProjectResponse]]:
    return {"projects": service.list_projects()}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProjectRequest,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectResponse:
    return service.create_project(payload)
```

```python
# apps/api/alembic/versions/0001_create_projects.py
from alembic import op
import sqlalchemy as sa

revision = "0001_create_projects"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("projects")
```

- [ ] **Step 4: Add the React shell with project listing and creation**

```json
// apps/web/package.json
{
  "name": "@writer-assistance/web",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.2"
  }
}
```

```tsx
// apps/web/src/routes/root.tsx
export function RootRoute() {
  const { data } = useProjectsQuery();

  return (
    <main>
      <h1>Writer Assistance</h1>
      <CreateProjectForm />
      <ProjectList projects={data?.projects ?? []} />
      {data?.projects?.length ? null : <p>Create your first project</p>}
    </main>
  );
}
```

```ts
// apps/web/src/lib/api.ts
export async function createProject(input: { title: string }) {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error('Failed to create project');
  }

  return response.json();
}
```

- [ ] **Step 5: Run the tests, migration, and mypy**

Run: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head && uv run --project apps/api pytest apps/api/tests/test_projects_api.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web exec vitest run src/routes/root.test.tsx`

Expected: PASS with project creation/listing working in the API, the root route rendering, and mypy clean.

- [ ] **Step 6: Log the task and commit**

```md
# devlogs.md append
- Added SQLite, Alembic migrations, project APIs, and the initial React shell.
```

```bash
git add package.json pnpm-workspace.yaml apps/api/alembic.ini apps/api/alembic apps/api/src/writer_assistance_api apps/api/tests/test_projects_api.py apps/web devlogs.md
git commit -m "feat: add project creation flow"
```

## Task 3: Add Disk Storage And Markdown Resource Upload

**Files:**
- Create: `apps/api/alembic/versions/0002_create_resources.py`
- Create: `apps/api/src/writer_assistance_api/storage.py`
- Create: `apps/api/src/writer_assistance_api/disk_storage.py`
- Create: `apps/api/src/writer_assistance_api/schemas/resources.py`
- Create: `apps/api/src/writer_assistance_api/services/resources.py`
- Create: `apps/api/src/writer_assistance_api/routes/resources.py`
- Modify: `apps/api/src/writer_assistance_api/models.py`
- Modify: `apps/api/src/writer_assistance_api/app.py`
- Create: `apps/api/tests/test_resources_api.py`
- Create: `apps/web/src/components/resource-upload-form.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/routes/root.tsx`

- [ ] **Step 1: Write the failing upload test**

```python
# apps/api/tests/test_resources_api.py
from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_upload_markdown_resources_with_logical_paths(tmp_path) -> None:
    client = TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
        )
    )

    project = client.post("/projects", json={"title": "Research Memo"}).json()

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("files", ("market.md", b"# Market\n\nDemand is rising.", "text/markdown")),
            ("files", ("zoning.md", b"# Zoning\n\nRules are changing.", "text/markdown")),
        ],
        data=[
            ("paths", "research/market.md"),
            ("paths", "research/zoning.md"),
        ],
    )

    assert response.status_code == 201
    assert [item["logical_path"] for item in response.json()["resources"]] == [
        "research/market.md",
        "research/zoning.md",
    ]
```

- [ ] **Step 2: Run the upload test to verify it fails**

Run: `uv run --project apps/api pytest apps/api/tests/test_resources_api.py -q`

Expected: FAIL because the resource model, storage abstraction, and upload route do not exist yet.

- [ ] **Step 3: Implement the resource model, disk storage, and upload route**

```python
# apps/api/src/writer_assistance_api/storage.py
from pathlib import Path
from typing import Protocol


class StoredObject(BaseModel):
    storage_path: str
    content_hash: str


class StorageDriver(Protocol):
    def put_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject: ...
    def read_object(self, storage_path: str) -> bytes: ...
```

```python
# apps/api/src/writer_assistance_api/disk_storage.py
from hashlib import sha256
from pathlib import Path

from writer_assistance_api.storage import StorageDriver, StoredObject


class DiskStorage(StorageDriver):
    def __init__(self, root: Path) -> None:
        self.root = root

    def put_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject:
        target = self.root / project_id / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObject(storage_path=str(target), content_hash=sha256(content).hexdigest())

    def read_object(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
```

```python
# apps/api/src/writer_assistance_api/routes/resources.py
@router.post("/projects/{project_id}/resources/upload", status_code=status.HTTP_201_CREATED)
async def upload_resources(
    project_id: str,
    files: list[UploadFile],
    paths: list[str] = Form(...),
    service: ResourcesService = Depends(get_resources_service),
) -> dict[str, list[ResourceResponse]]:
    return {"resources": await service.upload_resources(project_id=project_id, files=files, paths=paths)}
```

```python
# apps/api/alembic/versions/0002_create_resources.py
def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("logical_path", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_location", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("upload_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
```

- [ ] **Step 4: Add the browser upload form with folder-path preservation**

```tsx
// apps/web/src/components/resource-upload-form.tsx
export function ResourceUploadForm({ projectId }: { projectId: string }) {
  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        const input = event.currentTarget.elements.namedItem('files') as HTMLInputElement;
        await uploadResources(projectId, Array.from(input.files ?? []));
      }}
    >
      <label htmlFor="resource-upload">Upload markdown</label>
      <input
        id="resource-upload"
        name="files"
        type="file"
        accept=".md,text/markdown"
        multiple
        ref={(node) => node?.setAttribute('webkitdirectory', '')}
      />
      <button type="submit">Upload markdown</button>
    </form>
  );
}
```

```ts
// apps/web/src/lib/api.ts
export async function uploadResources(projectId: string, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
    formData.append('paths', (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name);
  });

  const response = await fetch(`/api/projects/${projectId}/resources/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload resources');
  }

  return response.json();
}
```

- [ ] **Step 5: Run migration, tests, and mypy**

Run: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head && uv run --project apps/api pytest apps/api/tests/test_resources_api.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src`

Expected: PASS with both markdown files stored, logical paths preserved, and mypy clean.

- [ ] **Step 6: Log the task and commit**

```md
# devlogs.md append
- Added disk-backed markdown storage with path-preserving resource uploads.
```

```bash
git add apps/api/alembic/versions/0002_create_resources.py apps/api/src/writer_assistance_api/storage.py apps/api/src/writer_assistance_api/disk_storage.py apps/api/src/writer_assistance_api/schemas/resources.py apps/api/src/writer_assistance_api/services/resources.py apps/api/src/writer_assistance_api/routes/resources.py apps/api/src/writer_assistance_api/models.py apps/api/tests/test_resources_api.py apps/web/src/components/resource-upload-form.tsx apps/web/src/lib/api.ts apps/web/src/routes/root.tsx devlogs.md
git commit -m "feat: add markdown resource upload"
```

## Task 4: Build The Rendered Reading Workspace

**Files:**
- Modify: `apps/api/src/writer_assistance_api/routes/resources.py`
- Modify: `apps/api/src/writer_assistance_api/services/resources.py`
- Create: `apps/web/src/routes/project.tsx`
- Create: `apps/web/src/routes/project.test.tsx`
- Create: `apps/web/src/components/resource-tree.tsx`
- Create: `apps/web/src/components/markdown-viewer.tsx`
- Modify: `apps/web/src/app/router.tsx`
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Write the failing reading-workspace test**

```tsx
// apps/web/src/routes/project.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProjectRoute } from './project';

it('shows a resource tree and renders the selected markdown file', async () => {
  render(<ProjectRoute />);

  await userEvent.click(screen.getByRole('button', { name: 'research/market.md' }));

  expect(await screen.findByRole('heading', { name: 'Market' })).toBeInTheDocument();
  expect(screen.getByText('Demand is rising.')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the workspace test to verify it fails**

Run: `pnpm --dir apps/web vitest run src/routes/project.test.tsx`

Expected: FAIL because the route, tree, and viewer do not exist yet.

- [ ] **Step 3: Add resource-list and resource-content backend endpoints**

```python
# apps/api/src/writer_assistance_api/routes/resources.py
@router.get("/projects/{project_id}/resources")
def list_resources(
    project_id: str,
    service: ResourcesService = Depends(get_resources_service),
) -> dict[str, list[ResourceResponse]]:
    return {"resources": service.list_resources(project_id)}


@router.get("/resources/{resource_id}/content")
def get_resource_content(
    resource_id: str,
    service: ResourcesService = Depends(get_resources_service),
) -> ResourceContentResponse:
    return service.get_resource_content(resource_id)
```

```python
# apps/api/src/writer_assistance_api/services/resources.py
def get_resource_content(self, resource_id: str) -> ResourceContentResponse:
    resource = self._session.get(Resource, resource_id)
    assert resource is not None
    markdown = self._storage.read_object(resource.storage_location).decode("utf-8")
    return ResourceContentResponse(resource_id=resource.id, markdown=markdown)
```

- [ ] **Step 4: Implement the project route, tree, and markdown viewer**

```tsx
// apps/web/src/routes/project.tsx
export function ProjectRoute() {
  const { projectId } = useParams();
  const [resourceId, setResourceId] = useState<string | null>(null);
  const resourcesQuery = useResourcesQuery(projectId!);
  const resourceQuery = useResourceContentQuery(resourceId);

  return (
    <main className="workspace">
      <ResourceTree resources={resourcesQuery.data?.resources ?? []} onSelect={setResourceId} />
      <MarkdownViewer markdown={resourceQuery.data?.markdown ?? ''} />
    </main>
  );
}
```

```tsx
// apps/web/src/components/markdown-viewer.tsx
import ReactMarkdown from 'react-markdown';

export function MarkdownViewer({ markdown }: { markdown: string }) {
  return <ReactMarkdown>{markdown}</ReactMarkdown>;
}
```

- [ ] **Step 5: Run the focused frontend test**

Run: `pnpm --dir apps/web vitest run src/routes/project.test.tsx`

Expected: PASS with the selected resource rendered as markdown.

- [ ] **Step 6: Log the task and commit**

```md
# devlogs.md append
- Added the rendered reading workspace with resource tree navigation and markdown viewing.
```

```bash
git add apps/api/src/writer_assistance_api/routes/resources.py apps/api/src/writer_assistance_api/services/resources.py apps/web/src/routes/project.tsx apps/web/src/routes/project.test.tsx apps/web/src/components/resource-tree.tsx apps/web/src/components/markdown-viewer.tsx apps/web/src/app/router.tsx apps/web/src/lib/api.ts devlogs.md
git commit -m "feat: add rendered reading workspace"
```

## Task 5: Add Quote-Anchored User Notes

**Files:**
- Create: `apps/api/alembic/versions/0004_create_annotations.py`
- Create: `apps/api/src/writer_assistance_api/schemas/annotations.py`
- Create: `apps/api/src/writer_assistance_api/services/annotations.py`
- Create: `apps/api/src/writer_assistance_api/routes/annotations.py`
- Modify: `apps/api/src/writer_assistance_api/models.py`
- Modify: `apps/api/src/writer_assistance_api/app.py`
- Create: `apps/api/tests/test_annotations_api.py`
- Create: `apps/web/src/lib/selection-anchor.ts`
- Create: `apps/web/src/components/annotation-composer.tsx`
- Create: `apps/web/src/components/notes-panel.tsx`
- Modify: `apps/web/src/routes/project.tsx`

- [ ] **Step 1: Write the failing annotation API test with duplicate quote text**

```python
# apps/api/tests/test_annotations_api.py
from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_store_quote_anchor_with_offsets_and_block_path(tmp_path) -> None:
    client = TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
        )
    )

    project = client.post("/projects", json={"title": "Market Memo"}).json()
    resource = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[("files", ("market.md", b"# Market\n\nDemand is rising.\n\nDemand is rising.", "text/markdown"))],
        data=[("paths", "research/market.md")],
    ).json()["resources"][0]

    response = client.post(
        f"/projects/{project['id']}/annotations",
        json={
            "resource_id": resource["id"],
            "body": "This repeated claim needs verification.",
            "anchor": {
                "quoteText": "Demand is rising.",
                "normalizedText": "demand is rising.",
                "startOffset": 18,
                "endOffset": 35,
                "blockPath": ["Market", "paragraph-1"],
                "resolutionStatus": "exact",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["anchor"]["blockPath"] == ["Market", "paragraph-1"]
```

- [ ] **Step 2: Run the annotation test to verify it fails**

Run: `uv run --project apps/api pytest apps/api/tests/test_annotations_api.py -q`

Expected: FAIL because the annotation model and route do not exist yet.

- [ ] **Step 3: Implement the annotation model, schema, and route**

```python
# apps/api/src/writer_assistance_api/schemas/annotations.py
from pydantic import BaseModel


class AnnotationAnchor(BaseModel):
    quoteText: str
    normalizedText: str
    startOffset: int
    endOffset: int
    blockPath: list[str]
    resolutionStatus: str


class CreateAnnotationRequest(BaseModel):
    resource_id: str
    body: str
    anchor: AnnotationAnchor
```

```python
# apps/api/src/writer_assistance_api/routes/annotations.py
@router.post("/projects/{project_id}/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(
    project_id: str,
    payload: CreateAnnotationRequest,
    service: AnnotationsService = Depends(get_annotations_service),
) -> AnnotationResponse:
    return service.create_annotation(project_id=project_id, payload=payload)
```

```python
# apps/api/alembic/versions/0004_create_annotations.py
def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=False),
        sa.Column("anchor_json", sa.Text(), nullable=False),
        sa.Column("origin_type", sa.String(), nullable=False),
        sa.Column("provenance_source_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
```

- [ ] **Step 4: Add selection anchoring and the notes panel in the web app**

```ts
// apps/web/src/lib/selection-anchor.ts
export function buildSelectionAnchor(selection: Selection) {
  const text = selection.toString();
  const nearestBlock = selection.anchorNode?.parentElement?.closest('[data-block-path]');
  const startOffset = Math.min(selection.anchorOffset, selection.focusOffset);
  const endOffset = Math.max(selection.anchorOffset, selection.focusOffset);

  return {
    quoteText: text,
    normalizedText: text.trim().toLowerCase(),
    startOffset,
    endOffset,
    blockPath: [nearestBlock?.getAttribute('data-block-path') ?? 'unknown'],
    resolutionStatus: 'exact' as const,
  };
}
```

```tsx
// apps/web/src/components/notes-panel.tsx
export function NotesPanel({ notes }: { notes: Array<{ id: string; quoteText: string; body: string }> }) {
  return (
    <aside>
      <h2>Your notes</h2>
      <ul>
        {notes.map((note) => (
          <li key={note.id}>
            <blockquote>{note.quoteText}</blockquote>
            <p>{note.body}</p>
          </li>
        ))}
      </ul>
    </aside>
  );
}
```

- [ ] **Step 5: Run migration, API test, frontend test, and mypy**

Run: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head && uv run --project apps/api pytest apps/api/tests/test_annotations_api.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web vitest run src/routes/project.test.tsx`

Expected: PASS with quote anchors persisted, notes visible in the UI, and mypy clean.

- [ ] **Step 6: Log the task and commit**

```md
# devlogs.md append
- Added quote-anchored user notes with explicit anchor metadata and a visible notes panel.
```

```bash
git add apps/api/alembic/versions/0004_create_annotations.py apps/api/src/writer_assistance_api/schemas/annotations.py apps/api/src/writer_assistance_api/services/annotations.py apps/api/src/writer_assistance_api/routes/annotations.py apps/api/src/writer_assistance_api/models.py apps/api/tests/test_annotations_api.py apps/web/src/lib/selection-anchor.ts apps/web/src/components/annotation-composer.tsx apps/web/src/components/notes-panel.tsx apps/web/src/routes/project.tsx devlogs.md
git commit -m "feat: add quote-anchored user notes"
```

## Task 6: Add AI Lens Discovery And Latest-Run Suggestion Review

**Files:**
- Create: `apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/ai/client.py`
- Modify: `apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py`
- Modify: `apps/api/src/writer_assistance_api/ai/fake_client.py`
- Modify: `apps/api/src/writer_assistance_api/schemas/analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/services/analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/routes/analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/models.py`
- Modify: `apps/api/tests/test_analysis_runs_api.py`
- Modify: `apps/web/src/components/lens-picker.tsx`
- Modify: `apps/web/src/components/ai-suggestions-panel.tsx`
- Modify: `apps/web/src/routes/project.tsx`
- Modify: `apps/web/src/routes/project.test.tsx`
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Write failing tests for discovery-first analysis**

```python
# apps/api/tests/test_analysis_runs_api.py
def test_first_run_discovers_lenses_and_generates_suggestions(tmp_path) -> None:
    ...
    create_response = client.post(
        f"/projects/{project_id}/analysis-runs",
        json={"resource_id": resource_id},
    )
    run = client.get(f"/analysis-runs/{create_response.json()['id']}").json()

    assert run["lens_discovery_status"] == "succeeded"
    assert run["discovered_lenses"] == [
        {"name": "Market Timing", "description": "Examines whether the document's market claims are time-sensitive."}
    ]
    assert run["suggestions"][0]["review_status"] == "unreviewed"


def test_regenerate_lenses_replaces_latest_run_but_accepted_notes_persist(tmp_path) -> None:
    ...
    regenerate_response = client.post(
        f"/resources/{resource_id}/analysis-runs/regenerate-lenses",
    )
    latest = client.get(f"/resources/{resource_id}/analysis-runs/latest").json()

    assert latest["id"] == regenerate_response.json()["id"]
    assert latest["discovered_lenses"] != first_run["discovered_lenses"]
    assert client.get(f"/resources/{resource_id}/annotations").json()["items"]
```

Also add targeted coverage that:
- `POST /analysis-runs/{run_id}/retry` reuses the existing discovered lenses instead of calling discovery again.
- `GET /resources/{resource_id}/analysis-runs/latest` switches the AI panel payload to the newest run after regeneration.

- [ ] **Step 2: Run the targeted analysis tests to verify they fail**

Run: `uv run --project apps/api pytest apps/api/tests/test_analysis_runs_api.py -q`

Expected: FAIL because the current contracts still expect explicit lens selection and do not support discovery metadata or regeneration.

- [ ] **Step 3: Extend the backend contract for discovered lenses**

```python
# apps/api/src/writer_assistance_api/ai/client.py
class DiscoveredLens(TypedDict):
    name: str
    description: str


class AiClient(Protocol):
    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]: ...
```

```python
# apps/api/src/writer_assistance_api/schemas/analysis_runs.py
class CreateAnalysisRunRequest(BaseModel):
    resource_id: str


class DiscoveredLensResponse(BaseModel):
    name: str
    description: str


class AnalysisRunDetailResponse(BaseModel):
    lens_discovery_status: Literal["queued", "running", "succeeded", "failed"]
    discovered_lenses: list[DiscoveredLensResponse]
    generation_status: str
    lenses: list[AnalysisRunLensResponse]
    suggestions: list[AiSuggestionResponse]
```

```python
# apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py
def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("lens_discovery_status", sa.String(), nullable=False))
    op.add_column("analysis_runs", sa.Column("discovered_lenses_json", sa.Text(), nullable=False))
```

- [ ] **Step 4: Implement discovery-first processing and regeneration endpoints**

```python
# apps/api/src/writer_assistance_api/services/analysis_runs.py
def process_analysis_run(self, run_id: str) -> None:
    run = self._get_run(run_id)
    self._mark_run_running(run_id)
    self._mark_lens_discovery_running(run_id)

    discovered_lenses = self._discover_or_load_lenses(run)
    if discovered_lenses is None:
        self._finish_run(run_id, "failed")
        return

    completed_with_failures = False
    for lens in discovered_lenses:
        ...


def retry_failed_lenses(self, run_id: str) -> AnalysisRun:
    ...


def create_regenerated_run(self, resource_id: str) -> AnalysisRun:
    ...
```

```python
# apps/api/src/writer_assistance_api/routes/analysis_runs.py
@router.post("/projects/{project_id}/analysis-runs", status_code=status.HTTP_202_ACCEPTED)
def create_analysis_run(...) -> AnalysisRunQueuedResponse: ...


@router.post("/resources/{resource_id}/analysis-runs/regenerate-lenses", status_code=status.HTTP_202_ACCEPTED)
def regenerate_lenses(...) -> AnalysisRunQueuedResponse: ...


@router.post("/analysis-runs/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_analysis_run(...) -> AnalysisRunQueuedResponse: ...
```

- [ ] **Step 5: Replace the fixed lens picker with discovery-state UI**

```tsx
// apps/web/src/components/lens-picker.tsx
export function LensPicker({
  discoveredLenses,
}: {
  discoveredLenses: Array<{ name: string; description: string }>;
}) {
  return (
    <section>
      <h2>AI lenses</h2>
      {discoveredLenses.map((lens) => (
        <article key={lens.name}>
          <strong>{lens.name}</strong>
          <p>{lens.description}</p>
        </article>
      ))}
    </section>
  );
}
```

```tsx
// apps/web/src/components/ai-suggestions-panel.tsx
export function AiSuggestionsPanel(...) {
  return (
    <aside>
      <h2>AI suggestions</h2>
      {hasExistingRun ? <button>Regenerate lenses</button> : <button>Run analysis</button>}
      {hasFailedLenses ? <button>Retry failed lenses</button> : null}
      {lensDiscoveryStatus === 'running' ? <p>Discovering lenses...</p> : null}
      {generationStatus === 'running' ? <p>Generating suggestions...</p> : null}
      {discoveredLenses.length > 0 ? <LensPicker discoveredLenses={discoveredLenses} /> : null}
      {/* latest-run suggestions only */}
    </aside>
  );
}
```

Keep accepted suggestions visible through the normal notes query so the notes panel still shows them even after the latest AI run changes.

- [ ] **Step 6: Verify backend and frontend behavior**

Run: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head && uv run --project apps/api pytest apps/api/tests/test_analysis_runs_api.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web exec vitest run src/routes/project.test.tsx src/lib/api.test.ts`

Expected: PASS with first-run lens discovery, latest-run replacement behavior, retry without rediscovery, regenerate with fresh discovery, and mypy clean.

- [ ] **Step 7: Log the task and commit**

```md
# devlogs.md append
- Updated the reading workspace plan so AI analysis discovers open-ended document-specific lenses on first run, keeps the AI panel bound to the latest run, and preserves accepted notes across regenerated runs.
```

```bash
git add apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py apps/api/src/writer_assistance_api/ai apps/api/src/writer_assistance_api/schemas/analysis_runs.py apps/api/src/writer_assistance_api/services/analysis_runs.py apps/api/src/writer_assistance_api/routes/analysis_runs.py apps/api/src/writer_assistance_api/models.py apps/api/tests/test_analysis_runs_api.py apps/web/src/components/lens-picker.tsx apps/web/src/components/ai-suggestions-panel.tsx apps/web/src/routes/project.tsx apps/web/src/routes/project.test.tsx apps/web/src/lib/api.ts devlogs.md
git commit -m "feat: add ai-discovered analysis lenses"
```

## Task 7: Add Smoke Coverage, Docs, And Final Verification

**Files:**
- Create: `playwright.config.ts`
- Create: `README.md`
- Create: `apps/web/e2e/reading-workspace.spec.ts`
- Modify: `package.json`
- Modify: `Makefile`
- Modify: `devlogs.md`

- [ ] **Step 1: Write the failing Playwright smoke test**

```ts
// apps/web/e2e/reading-workspace.spec.ts
import { expect, test } from '@playwright/test';

test('user can create a project, upload markdown, add a note, and accept an ai suggestion', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Project title').fill('Housing Brief');
  await page.getByRole('button', { name: 'Create project' }).click();

  await page.getByLabel('Upload markdown').setInputFiles([
    { name: 'market.md', mimeType: 'text/markdown', buffer: Buffer.from('# Market\n\nDemand is rising.') },
  ]);

  await page.getByRole('button', { name: 'market.md' }).click();
  await page.getByText('Demand is rising.').selectText();
  await page.getByLabel('Note body').fill('Need stronger evidence here.');
  await page.getByRole('button', { name: 'Save note' }).click();

  await page.getByRole('button', { name: 'Run analysis' }).click();
  await expect(page.getByText('AI suggestions')).toBeVisible();
  await page.getByRole('button', { name: 'Accept' }).first().click();
  await expect(page.getByText('Check whether rents justify this claim.')).toBeVisible();
});
```

- [ ] **Step 2: Run the Playwright test to verify it fails**

Run: `pnpm exec playwright test apps/web/e2e/reading-workspace.spec.ts`

Expected: FAIL until the full create-upload-read-note-analyze flow exists.

- [ ] **Step 3: Add runbook docs and final verification commands**

```json
// package.json
{
  "name": "writer-assistance",
  "private": true,
  "scripts": {
    "web:install": "pnpm --dir apps/web install",
      "web:test": "pnpm --dir apps/web exec vitest run",
    "test:e2e": "pnpm exec playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.2"
  }
}
```

```makefile
# Makefile additions
web-dev:
	pnpm --dir apps/web dev

web-test:
	pnpm --dir apps/web vitest run

smoke:
	uv run --project apps/api pytest apps/api/tests -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web exec vitest run && pnpm exec playwright test
```

```md
# README.md
# Writer Assistance

## Local setup

1. `uv sync --project apps/api`
2. `pnpm install`
3. `pnpm --dir apps/web install`
4. `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
5. Run `make api-dev` and `make web-dev` in separate terminals

The app stores SQLite data in `./data/app.db` and markdown resources in `./data/storage`.
```

- [ ] **Step 4: Run the full verification suite**

Run: `uv run --project apps/api pytest apps/api/tests -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web exec vitest run && pnpm exec playwright test`

Expected: PASS with backend tests, strict mypy, frontend tests, and one browser smoke test all green.

- [ ] **Step 5: Log the task and commit**

```md
# devlogs.md append
- Added smoke coverage, developer runbooks, and final verification commands for the reading-workspace slice.
```

```bash
git add playwright.config.ts README.md package.json Makefile apps/web/e2e/reading-workspace.spec.ts devlogs.md
git commit -m "test: add reading workspace smoke coverage"
```

## Self-Review Checklist

- Spec coverage
  - immutable uploaded resources: Tasks 3 and 4
  - rendered reading workspace: Task 4
  - quote-anchored user notes: Task 5
  - visible AI suggestion review: Task 6
  - local disk persistence and storage abstraction: Task 3
  - explicit retryable async analysis model: Task 6
  - strict backend type checking: Tasks 1 through 7
- Placeholder scan
  - no `TBD`, `TODO`, or unspecified status models remain
- Type consistency
  - backend state names stay consistent across models, routes, tests, and UI
  - `resolutionStatus` remains `exact | fuzzy | unresolved`
  - backend verification always includes `mypy`

## Follow-On Plan

After this plan is implemented, write a second plan for:

- AI-authored initial draft generation
- report versioning and staleness
- paragraph-block editor model
- tone alternatives
- critique mode
- markdown export
