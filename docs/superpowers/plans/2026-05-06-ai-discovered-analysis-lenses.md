# AI-Discovered Analysis Lenses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed analysis lens checklist with AI-discovered, document-specific lenses that are discovered on first run, reused for retry, regenerated explicitly, and shown only from the latest analysis run while accepted notes persist in the notes panel.

**Architecture:** Extend the existing `analysis_runs` model rather than creating a second workflow. Each run owns its own lens discovery status plus an ordered list of discovered `{name, description}` lens records, and the frontend treats the latest run as the active AI panel view. Accepted suggestions remain durable because they still become annotations, so regeneration only replaces the AI panel state and never clears user-owned notes.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, pytest, mypy, React, TypeScript, TanStack Query, Vitest, Playwright, Anthropic Vertex Python SDK

---

## Scope

This plan only changes the analysis-lens workflow for the current reading workspace:

- replace the fixed `financial/real_estate/political/software_engineering` chooser with AI-discovered open-ended lenses
- auto-discover lenses on the first `Run analysis`
- allow explicit `Regenerate lenses`
- keep `Retry failed lenses` scoped to suggestion generation only
- keep accepted suggestions visible through the existing notes flow

This plan does **not** add report generation, editor mode, export, or editable lens sets.

## File Structure

### Backend

- Modify: `apps/api/src/writer_assistance_api/ai/client.py`
  - add `DiscoveredLens`
  - change `AiClient` to support `discover_lenses()`
  - change `analyze_resource()` to accept dynamic lens name/description strings instead of the fixed literal catalog
- Modify: `apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py`
  - add a structured lens-discovery call
  - update suggestion generation prompt to use discovered lens name/description instead of hardcoded catalog guidance
- Modify: `apps/api/src/writer_assistance_api/ai/fake_client.py`
  - add deterministic discovery support for tests and smoke mode
- Create: `apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py`
  - add `lens_discovery_status`
  - add `discovered_lenses`
  - backfill existing runs safely
- Modify: `apps/api/src/writer_assistance_api/models.py`
  - persist lens discovery metadata on `AnalysisRun`
- Modify: `apps/api/src/writer_assistance_api/schemas/analysis_runs.py`
  - remove fixed lens selection from create input
  - add discovery status and discovered lenses to run response
  - change lens names in responses from fixed literal type to plain strings
- Modify: `apps/api/src/writer_assistance_api/services/analysis_runs.py`
  - implement discovery-first processing
  - implement regenerate-lenses endpoint behavior
  - keep retry behavior on failed suggestion generation only
- Modify: `apps/api/src/writer_assistance_api/routes/analysis_runs.py`
  - remove explicit lens list from the create contract
  - add `POST /resources/{resource_id}/analysis-runs/regenerate-lenses`
- Modify: `apps/api/tests/test_anthropic_vertex_client.py`
  - prove the live client uses tool-based structured discovery output
- Modify: `apps/api/tests/test_analysis_runs_api.py`
  - cover first-run discovery
  - cover retry without rediscovery
  - cover regenerate replacing latest run while accepted notes persist

### Frontend

- Modify: `apps/web/src/lib/api.ts`
  - add discovered-lens types
  - remove fixed-lens request shape from `createAnalysisRun`
  - add `regenerateLenses()` API and mutation
- Modify: `apps/web/src/components/lens-picker.tsx`
  - replace checkbox UI with read-only discovered lens display
- Modify: `apps/web/src/components/ai-suggestions-panel.tsx`
  - show `Run analysis` before first run
  - show discovery/generation progress states
  - show read-only discovered lenses after discovery succeeds
  - show `Regenerate lenses` only when a run already exists
- Modify: `apps/web/src/routes/project.tsx`
  - remove selected-lens state
  - trigger discovery-first analysis on first run
  - add regenerate-lenses action
- Modify: `apps/web/src/routes/project.test.tsx`
  - remove fixed-checkbox assumptions
  - add latest-run discovery UI coverage
- Modify: `apps/web/src/lib/api.test.ts`
  - keep the latest-run polling behavior aligned with the new discovery and generation states
- Optional touch only if required by the implementation:
  - `apps/web/e2e/reading-workspace.spec.ts`
  - only if the smoke flow needs updated waiting/assertion text

### Docs / Progress

- Modify: `devlogs.md`
  - append a short entry after implementation completes

## Task 1: Add Lens Discovery To The AI Client Contract

**Files:**
- Modify: `apps/api/src/writer_assistance_api/ai/client.py`
- Modify: `apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py`
- Modify: `apps/api/src/writer_assistance_api/ai/fake_client.py`
- Modify: `apps/api/tests/test_anthropic_vertex_client.py`

- [ ] **Step 1: Write the failing AI client test for structured lens discovery**

```python
# apps/api/tests/test_anthropic_vertex_client.py
from types import SimpleNamespace
from typing import Any

from writer_assistance_api.ai.anthropic_vertex_client import AnthropicVertexAiClient, MODEL_NAME
from writer_assistance_api.ai.client import DiscoveredLens


def test_discover_lenses_uses_tool_based_structured_output() -> None:
    messages = StubMessages()
    client = AnthropicVertexAiClient(
        project_id="project-id",
        region="us-east5",
        client=SimpleNamespace(messages=messages),  # type: ignore[arg-type]
    )

    lenses = client.discover_lenses(
        markdown="# Market\n\nDemand is rising.",
        logical_path="research/market.md",
    )

    assert lenses == [
        DiscoveredLens(name="Demand trend", description="Highlights pricing power and revenue implications.")
    ]
    assert len(messages.create_calls) == 1
    assert messages.create_calls[0]["model"] == MODEL_NAME
    assert messages.create_calls[0]["tool_choice"] == {"type": "tool", "name": "emit_lenses"}
    assert messages.create_calls[0]["tools"][0]["name"] == "emit_lenses"


class StubMessages:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name="emit_lenses",
                    input={
                        "lenses": [
                            {
                                "name": "Demand trend",
                                "description": "Highlights pricing power and revenue implications.",
                            }
                        ]
                    },
                )
            ]
        )
```

- [ ] **Step 2: Run the AI client test to verify it fails**

Run: `uv run --project apps/api pytest apps/api/tests/test_anthropic_vertex_client.py -q`

Expected: FAIL with `AttributeError` or `TypeError` because `AiClient` and `AnthropicVertexAiClient` do not expose `discover_lenses()` yet.

- [ ] **Step 3: Add `DiscoveredLens` and update the AI client protocol**

```python
# apps/api/src/writer_assistance_api/ai/client.py
from pydantic import BaseModel, ConfigDict, Field


class DiscoveredLens(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AiSuggestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    anchor: QuoteAnchor


class AiClient(Protocol):
    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        raise NotImplementedError

    def analyze_resource(
        self,
        *,
        lens_name: str,
        lens_description: str,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        raise NotImplementedError
```

- [ ] **Step 4: Implement the live and fake discovery methods**

```python
# apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py
class DiscoverLensesOutput(BaseModel):
    lenses: list[DiscoveredLens] = Field(default_factory=list)


DISCOVER_TOOL_NAME = "emit_lenses"
SUGGEST_TOOL_NAME = "emit_suggestions"


def discover_lenses(
    self,
    *,
    markdown: str,
    logical_path: str,
) -> list[DiscoveredLens]:
    response = self._client.messages.create(
        model=MODEL_NAME,
        max_tokens=1200,
        temperature=0,
        system=LENS_DISCOVERY_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_lens_discovery_prompt(
                    markdown=markdown,
                    logical_path=logical_path,
                ),
            }
        ],
        tools=[
            {
                "name": DISCOVER_TOOL_NAME,
                "description": "Return discovered analysis lenses for the document.",
                "input_schema": DiscoverLensesOutput.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": DISCOVER_TOOL_NAME},
    )
    tool_input = next(
        (
            getattr(block, "input", None)
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ),
        None,
    )
    if tool_input is None:
        raise ValueError("AI response did not include a tool_use block for lens discovery")
    return DiscoverLensesOutput.model_validate(tool_input).lenses


def analyze_resource(
    self,
    *,
    lens_name: str,
    lens_description: str,
    markdown: str,
    logical_path: str,
) -> list[AiSuggestionDraft]:
    response = self._client.messages.create(
        model=MODEL_NAME,
        max_tokens=2000,
        temperature=0,
        system=SUGGESTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_suggestion_prompt(
                    lens_name=lens_name,
                    lens_description=lens_description,
                    markdown=markdown,
                    logical_path=logical_path,
                ),
            }
        ],
        tools=[
            {
                "name": SUGGEST_TOOL_NAME,
                "description": "Return reading-workspace note suggestions in the expected schema.",
                "input_schema": AnalyzeResourceOutput.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": SUGGEST_TOOL_NAME},
    )
    tool_input = next(
        (
            getattr(block, "input", None)
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ),
        None,
    )
    if tool_input is None:
        raise ValueError("AI response did not include a tool_use block")
    return AnalyzeResourceOutput.model_validate(tool_input).suggestions
```

```python
# apps/api/src/writer_assistance_api/ai/fake_client.py
SMOKE_DISCOVERED_LENSES = [
    DiscoveredLens(
        name="Demand trend",
        description="Highlights pricing power and revenue implications in the current resource.",
    )
]


class FakeAiClient:
    def __init__(
        self,
        *,
        discovered_lenses: Sequence[DiscoveredLens] | None = None,
        outcomes_by_lens: Mapping[str, Sequence[Sequence[AiSuggestionDraftLike] | Exception]] | None = None,
    ) -> None:
        self._discovered_lenses = list(discovered_lenses or [])
        self._outcomes_by_lens = {key: list(value) for key, value in (outcomes_by_lens or {}).items()}
        self.calls: list[dict[str, Any]] = []

    def discover_lenses(self, *, markdown: str, logical_path: str) -> list[DiscoveredLens]:
        self.calls.append({"kind": "discover", "markdown": markdown, "logical_path": logical_path})
        return list(self._discovered_lenses)

    def analyze_resource(
        self,
        *,
        lens_name: str,
        lens_description: str,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        self.calls.append(
            {
                "kind": "analyze",
                "lens_name": lens_name,
                "lens_description": lens_description,
                "markdown": markdown,
                "logical_path": logical_path,
            }
        )
        outcomes = self._outcomes_by_lens.get(lens_name, [])
        if not outcomes:
            return []
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return normalize_suggestion_drafts(outcome)


class SmokeAiClient:
    def discover_lenses(self, *, markdown: str, logical_path: str) -> list[DiscoveredLens]:
        del markdown, logical_path
        return list(SMOKE_DISCOVERED_LENSES)

    def analyze_resource(
        self,
        *,
        lens_name: str,
        lens_description: str,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        del lens_description, logical_path
        if lens_name != SMOKE_DISCOVERED_LENSES[0].name:
            return []
        paragraph = _first_non_heading_paragraph(markdown)
        return [
            AiSuggestionDraft(
                body=SMOKE_SUGGESTION_BODY,
                anchor=QuoteAnchor(
                    quoteText=paragraph,
                    normalizedText=" ".join(paragraph.split()).lower(),
                    startOffset=0,
                    endOffset=len(paragraph),
                    blockPath=["paragraph", "1"],
                    resolutionStatus="exact",
                ),
            )
        ]
```

- [ ] **Step 5: Re-run the AI client tests**

Run: `uv run --project apps/api pytest apps/api/tests/test_anthropic_vertex_client.py -q`

Expected: PASS with `1 passed`.

- [ ] **Step 6: Commit the AI client contract changes**

```bash
git add apps/api/src/writer_assistance_api/ai/client.py apps/api/src/writer_assistance_api/ai/anthropic_vertex_client.py apps/api/src/writer_assistance_api/ai/fake_client.py apps/api/tests/test_anthropic_vertex_client.py
git commit -m "feat: add ai lens discovery client"
```

## Task 2: Persist Lens Discovery Metadata And Discovery-First Run Semantics

**Files:**
- Create: `apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/models.py`
- Modify: `apps/api/src/writer_assistance_api/schemas/analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/services/analysis_runs.py`
- Modify: `apps/api/src/writer_assistance_api/routes/analysis_runs.py`
- Modify: `apps/api/tests/test_analysis_runs_api.py`

- [ ] **Step 1: Write the failing backend tests for first-run discovery, retry, and regeneration**

```python
# apps/api/tests/test_analysis_runs_api.py
def test_first_run_discovers_lenses_and_generates_suggestions(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {"name": "Demand trend", "description": "Highlights pricing power and revenue implications."}
        ],
        outcomes_by_lens={
            "Demand trend": [
                [
                    suggestion_payload(
                        body="Capture the demand signal as evidence of pricing power.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ]
        },
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    )

    assert create_response.status_code == 202
    run = client.get(f"/analysis-runs/{create_response.json()['id']}").json()

    assert run["lens_discovery_status"] == "succeeded"
    assert run["discovered_lenses"] == [
        {
            "name": "Demand trend",
            "description": "Highlights pricing power and revenue implications.",
        }
    ]
    assert run["lens_results"][0]["lens"] == "Demand trend"
    assert run["lens_results"][0]["suggestions"][0]["review_state"] == "unreviewed"
    assert ai_client.discover_call_count == 1


def test_retry_failed_lenses_reuses_existing_discovered_lenses(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {"name": "Demand trend", "description": "Highlights pricing power and revenue implications."},
            {"name": "Policy risk", "description": "Checks whether policy language changes the interpretation."},
        ],
        outcomes_by_lens={
            "Demand trend": [
                [
                    suggestion_payload(
                        body="Capture the demand signal as evidence of pricing power.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "Policy risk": [
                RuntimeError("Lens timed out"),
                [
                    suggestion_payload(
                        body="Flag the policy angle as a follow-up item.",
                        quote_text="Rules are changing.",
                        start_offset=19,
                        end_offset=38,
                    )
                ],
            ],
        },
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    first_run = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    ).json()
    completed = client.get(f"/analysis-runs/{first_run['id']}").json()
    assert completed["generation_state"] == "completed_with_failures"

    retry_response = client.post(f"/analysis-runs/{first_run['id']}/retry")
    assert retry_response.status_code == 202

    retried = client.get(f"/analysis-runs/{first_run['id']}").json()
    assert retried["generation_state"] == "succeeded"
    assert retried["discovered_lenses"] == completed["discovered_lenses"]
    assert ai_client.discover_call_count == 1


def test_regenerate_lenses_replaces_latest_run_but_preserves_accepted_notes(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses_sequence=[
            [{"name": "Demand trend", "description": "Highlights pricing power and revenue implications."}],
            [{"name": "Execution risk", "description": "Looks for operational constraints in the same document."}],
        ],
        outcomes_by_lens={
            "Demand trend": [
                [
                    suggestion_payload(
                        body="Capture the demand signal as evidence of pricing power.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "Execution risk": [
                [
                    suggestion_payload(
                        body="Track the permitting delay as an execution risk.",
                        quote_text="Rules are changing.",
                        start_offset=19,
                        end_offset=38,
                    )
                ]
            ],
        },
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    first_run = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    ).json()
    first_details = client.get(f"/analysis-runs/{first_run['id']}").json()
    accepted = client.post(
        f"/analysis-suggestions/{first_details['lens_results'][0]['suggestions'][0]['id']}/accept"
    ).json()

    regenerate_response = client.post(f"/resources/{resource['id']}/analysis-runs/regenerate-lenses")
    assert regenerate_response.status_code == 202

    latest = client.get(f"/resources/{resource['id']}/analysis-runs/latest").json()
    assert latest["id"] == regenerate_response.json()["id"]
    assert latest["discovered_lenses"] != first_details["discovered_lenses"]
    annotations = client.get(f"/resources/{resource['id']}/annotations").json()["annotations"]
    assert [annotation["body"] for annotation in annotations] == [accepted["annotation"]["body"]]
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `uv run --project apps/api pytest apps/api/tests/test_analysis_runs_api.py -q`

Expected: FAIL because:
- `CreateAnalysisRunRequest` still requires `lenses`
- there is no `regenerate-lenses` route
- run responses do not include `lens_discovery_status` or `discovered_lenses`

- [ ] **Step 3: Add the migration, model fields, response schema, and service changes**

```python
# apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0006_add_lens_discovery_to_analysis_runs"
down_revision = "0005_create_analysis_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analysis_runs")}
    if "lens_discovery_status" not in columns:
        op.add_column(
            "analysis_runs",
            sa.Column("lens_discovery_status", sa.String(), nullable=False, server_default="succeeded"),
        )
    if "discovered_lenses" not in columns:
        op.add_column(
            "analysis_runs",
            sa.Column("discovered_lenses", sa.JSON(), nullable=False, server_default="[]"),
        )

    rows = bind.execute(sa.text("SELECT id, requested_lenses FROM analysis_runs")).mappings().all()
    for row in rows:
        requested = row["requested_lenses"] or []
        if isinstance(requested, str):
            requested = json.loads(requested)
        discovered = [
            {
                "name": lens,
                "description": "Imported from an earlier fixed-lens analysis run.",
            }
            for lens in requested
        ]
        bind.execute(
            sa.text(
                "UPDATE analysis_runs "
                "SET lens_discovery_status = :status, discovered_lenses = :discovered "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "status": "succeeded",
                "discovered": json.dumps(discovered),
            },
        )

    op.alter_column("analysis_runs", "lens_discovery_status", server_default=None)
    op.alter_column("analysis_runs", "discovered_lenses", server_default=None)
```

```python
# apps/api/src/writer_assistance_api/models.py
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    lens_discovery_status: Mapped[str] = mapped_column(String)
    discovered_lenses: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    generation_state: Mapped[str] = mapped_column(String)
    requested_lenses: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
```

```python
# apps/api/src/writer_assistance_api/schemas/analysis_runs.py
LensDiscoveryState = Literal["queued", "running", "succeeded", "failed"]


class CreateAnalysisRunRequest(BaseModel):
    resource_id: str


class DiscoveredLensResponse(BaseModel):
    name: str
    description: str


class AnalysisSuggestionResponse(BaseModel):
    id: str
    analysis_run_id: str
    lens: str
    body: str
    review_state: SuggestionReviewState
    created_at: datetime
    updated_at: datetime
    anchor: QuoteAnchor


class AnalysisLensResultResponse(BaseModel):
    id: str
    lens: str
    generation_state: AnalysisLensGenerationState
    error_message: str | None
    suggestions: list[AnalysisSuggestionResponse]


class AnalysisRunDetailResponse(BaseModel):
    id: str
    project_id: str
    resource_id: str
    lens_discovery_status: LensDiscoveryState
    discovered_lenses: list[DiscoveredLensResponse]
    generation_state: AnalysisRunGenerationState
    lens_results: list[AnalysisLensResultResponse]
    created_at: datetime
    updated_at: datetime
```

```python
# apps/api/src/writer_assistance_api/routes/analysis_runs.py
@router.post("/projects/{project_id}/analysis-runs", status_code=status.HTTP_202_ACCEPTED)
def create_analysis_run(
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: str,
    payload: CreateAnalysisRunRequest,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    queued_run = service.create_analysis_run(project_id, payload)
    background_tasks.add_task(process_analysis_run_in_background, request.app, queued_run.id)
    return queued_run


@router.post("/resources/{resource_id}/analysis-runs/regenerate-lenses", status_code=status.HTTP_202_ACCEPTED)
def regenerate_lenses(
    request: Request,
    background_tasks: BackgroundTasks,
    resource_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    queued_run = service.regenerate_lenses(resource_id)
    background_tasks.add_task(process_analysis_run_in_background, request.app, queued_run.id)
    return queued_run
```

```python
# apps/api/src/writer_assistance_api/services/analysis_runs.py
def create_analysis_run(
    self,
    project_id: str,
    payload: CreateAnalysisRunRequest,
) -> AnalysisRunDetailResponse:
    project = self._session.scalar(select(Project).where(Project.id == project_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    resource = self._session.scalar(
        select(Resource).where(Resource.id == payload.resource_id, Resource.project_id == project_id)
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    now = datetime.now(UTC)
    run = AnalysisRun(
        id=str(uuid4()),
        project_id=project_id,
        resource_id=resource.id,
        lens_discovery_status="queued",
        discovered_lenses=[],
        generation_state="queued",
        requested_lenses=[],
        created_at=now,
        updated_at=now,
    )
    self._session.add(run)
    self._session.commit()
    return self._serialize_run(run)


def regenerate_lenses(self, resource_id: str) -> AnalysisRunDetailResponse:
    resource = self._session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    now = datetime.now(UTC)
    run = AnalysisRun(
        id=str(uuid4()),
        project_id=resource.project_id,
        resource_id=resource.id,
        lens_discovery_status="queued",
        discovered_lenses=[],
        generation_state="queued",
        requested_lenses=[],
        created_at=now,
        updated_at=now,
    )
    self._session.add(run)
    self._session.commit()
    return self._serialize_run(run)


def process_analysis_run(self, analysis_run_id: str) -> None:
    run = self._get_analysis_run_or_404(analysis_run_id)
    resource = self._get_resource_for_run(run)
    if self._ai_client is None:
        raise RuntimeError("AI client is required to process analysis runs")

    markdown = self._read_markdown_resource(resource)
    self._session.refresh(run)

    if run.lens_discovery_status == "queued":
        run.generation_state = "running"
        run.lens_discovery_status = "running"
        run.updated_at = datetime.now(UTC)
        self._session.commit()
        try:
            discovered_lenses = self._ai_client.discover_lenses(
                markdown=markdown,
                logical_path=resource.logical_path,
            )
            if not discovered_lenses:
                raise RuntimeError("Lens discovery returned no lenses")
        except Exception as exc:
            run.lens_discovery_status = "failed"
            run.generation_state = "failed"
            run.updated_at = datetime.now(UTC)
            self._session.commit()
            raise exc

        now = datetime.now(UTC)
        run.discovered_lenses = [lens.model_dump(mode="python") for lens in discovered_lenses]
        run.requested_lenses = [lens.name for lens in discovered_lenses]
        run.lens_discovery_status = "succeeded"
        run.updated_at = now
        self._session.add_all(
            AnalysisRunLensResult(
                id=str(uuid4()),
                analysis_run_id=run.id,
                lens=lens.name,
                generation_state="queued",
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            for lens in discovered_lenses
        )
        self._session.commit()

    lens_descriptions = {
        lens["name"]: lens["description"]
        for lens in run.discovered_lenses
    }
    lens_results_to_process = [
        lens_result
        for lens_result in self._ordered_lens_results(run)
        if lens_result.generation_state == "queued"
    ]
    if not lens_results_to_process:
        return

    run.generation_state = "running"
    run.updated_at = datetime.now(UTC)
    self._session.commit()

    for lens_result in lens_results_to_process:
        try:
            drafts = self._ai_client.analyze_resource(
                lens_name=lens_result.lens,
                lens_description=lens_descriptions[lens_result.lens],
                markdown=markdown,
                logical_path=resource.logical_path,
            )
            suggestions = [
                self._build_suggestion(
                    run_id=run.id,
                    lens_result=lens_result,
                    body=draft.body,
                    anchor=draft.anchor,
                )
                for draft in drafts
            ]
            self._session.add_all(suggestions)
            lens_result.generation_state = "succeeded"
            lens_result.error_message = None
        except Exception as exc:
            lens_result.generation_state = "failed"
            lens_result.error_message = str(exc) or exc.__class__.__name__
        lens_result.updated_at = datetime.now(UTC)
        run.generation_state = _run_generation_state(self._ordered_lens_results(run))
        run.updated_at = datetime.now(UTC)
        self._session.commit()


def retry_analysis_run(self, analysis_run_id: str) -> AnalysisRunDetailResponse:
    run = self._get_analysis_run_or_404(analysis_run_id)
    failed_lens_results = [
        lens_result
        for lens_result in self._ordered_lens_results(run)
        if lens_result.generation_state == "failed"
    ]
    if not failed_lens_results:
        return self._serialize_run(run)

    run.generation_state = "queued"
    run.updated_at = datetime.now(UTC)
    for lens_result in failed_lens_results:
        lens_result.generation_state = "queued"
        lens_result.error_message = None
        lens_result.updated_at = datetime.now(UTC)
    self._session.commit()
    return self._serialize_run(run)


def _serialize_run(self, run: AnalysisRun) -> AnalysisRunDetailResponse:
    ordered_lens_results = self._ordered_lens_results(run)
    suggestions = list(
        self._session.scalars(
            select(AnalysisSuggestion)
            .where(AnalysisSuggestion.analysis_run_id == run.id)
            .order_by(AnalysisSuggestion.created_at, AnalysisSuggestion.id)
        )
    )
    suggestions_by_lens_result: dict[str, list[AnalysisSuggestion]] = defaultdict(list)
    for suggestion in suggestions:
        suggestions_by_lens_result[suggestion.lens_result_id].append(suggestion)
    return AnalysisRunDetailResponse(
        id=run.id,
        project_id=run.project_id,
        resource_id=run.resource_id,
        lens_discovery_status=cast(LensDiscoveryState, run.lens_discovery_status),
        discovered_lenses=[
            DiscoveredLensResponse.model_validate(lens)
            for lens in run.discovered_lenses
        ],
        generation_state=cast(AnalysisRunGenerationState, run.generation_state),
        lens_results=[
            AnalysisLensResultResponse(
                id=lens_result.id,
                lens=lens_result.lens,
                generation_state=cast(AnalysisLensGenerationState, lens_result.generation_state),
                error_message=lens_result.error_message,
                suggestions=[
                    self._serialize_suggestion(suggestion)
                    for suggestion in suggestions_by_lens_result.get(lens_result.id, [])
                ],
            )
            for lens_result in ordered_lens_results
        ],
        created_at=_coerce_utc(run.created_at),
        updated_at=_coerce_utc(run.updated_at),
    )
```

- [ ] **Step 4: Re-run backend tests and mypy**

Run: `uv run --project apps/api pytest apps/api/tests/test_analysis_runs_api.py -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src`

Expected: PASS with `8 passed` and `Success: no issues found in 25 source files`.

- [ ] **Step 5: Commit the backend discovery workflow**

```bash
git add apps/api/alembic/versions/0006_add_lens_discovery_to_analysis_runs.py apps/api/src/writer_assistance_api/models.py apps/api/src/writer_assistance_api/schemas/analysis_runs.py apps/api/src/writer_assistance_api/services/analysis_runs.py apps/api/src/writer_assistance_api/routes/analysis_runs.py apps/api/tests/test_analysis_runs_api.py
git commit -m "feat: add discovery-first analysis runs"
```

## Task 3: Replace The Fixed Lens Checklist With Discovery-State UI

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/lens-picker.tsx`
- Modify: `apps/web/src/components/ai-suggestions-panel.tsx`
- Modify: `apps/web/src/routes/project.tsx`
- Modify: `apps/web/src/routes/project.test.tsx`
- Modify: `apps/web/src/lib/api.test.ts`

- [ ] **Step 1: Write the failing frontend tests for the new AI panel behavior**

```tsx
// apps/web/src/routes/project.test.tsx
it('shows a single Run analysis action before any analysis run exists', async () => {
  let createPayload: unknown = null;

  fetchMock.mockImplementation(async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? (input instanceof Request ? input.method : 'GET');

    if (url === '/api/projects/project-1/resources') {
      return createJsonResponse({
        resources: [
          {
            id: 'resource-1',
            project_id: 'project-1',
            logical_path: 'research/market.md',
            original_filename: 'market.md',
            content_hash: 'hash-1',
            upload_status: 'uploaded',
            created_at: '2026-05-05T00:00:00Z',
          },
        ],
      });
    }

    if (url === '/api/resources/resource-1/content') {
      return createJsonResponse({
        resource_id: 'resource-1',
        markdown: '# Market\\n\\nDemand is rising.',
      });
    }

    if (url === '/api/resources/resource-1/annotations') {
      return createJsonResponse({ annotations: [] });
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return new Response(JSON.stringify({ detail: 'Analysis run not found' }), { status: 404 });
    }

    if (url === '/api/projects/project-1/analysis-runs' && method === 'POST') {
      createPayload = JSON.parse(String(init?.body));
      return createJsonResponse(
        {
          id: 'run-1',
          project_id: 'project-1',
          resource_id: 'resource-1',
          lens_discovery_status: 'queued',
          discovered_lenses: [],
          generation_state: 'queued',
          lens_results: [],
          created_at: '2026-05-05T00:00:00Z',
          updated_at: '2026-05-05T00:00:00Z',
        },
        { status: 202 },
      );
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  });

  renderProjectRoute();
  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(within(suggestionsPanel).queryByLabelText('Financial')).not.toBeInTheDocument();

  fireEvent.click(within(suggestionsPanel).getByRole('button', { name: 'Run analysis' }));

  await waitFor(() => {
    expect(createPayload).toEqual({ resource_id: 'resource-1' });
  });
});


it('renders discovered lenses from the latest run and offers regeneration', async () => {
  fetchMock.mockImplementation(async (input) => {
    const url = input instanceof Request ? input.url : String(input);

    if (url === '/api/projects/project-1/resources') {
      return createJsonResponse({
        resources: [
          {
            id: 'resource-1',
            project_id: 'project-1',
            logical_path: 'research/market.md',
            original_filename: 'market.md',
            content_hash: 'hash-1',
            upload_status: 'uploaded',
            created_at: '2026-05-05T00:00:00Z',
          },
        ],
      });
    }

    if (url === '/api/resources/resource-1/content') {
      return createJsonResponse({
        resource_id: 'resource-1',
        markdown: '# Market\\n\\nDemand is rising.',
      });
    }

    if (url === '/api/resources/resource-1/annotations') {
      return createJsonResponse({
        annotations: [
          {
            id: 'annotation-1',
            project_id: 'project-1',
            resource_id: 'resource-1',
            body: 'Accepted note persists.',
            origin_type: 'accepted_ai',
            provenance_source_id: 'suggestion-1',
            created_at: '2026-05-05T00:00:00Z',
            updated_at: '2026-05-05T00:00:00Z',
            anchor: {
              quoteText: 'Demand is rising.',
              normalizedText: 'demand is rising.',
              startOffset: 0,
              endOffset: 17,
              blockPath: ['paragraph', '1'],
              resolutionStatus: 'exact',
            },
          },
        ],
      });
    }

    if (url === '/api/resources/resource-1/analysis-runs/latest') {
      return createJsonResponse({
        id: 'run-2',
        project_id: 'project-1',
        resource_id: 'resource-1',
        lens_discovery_status: 'succeeded',
        discovered_lenses: [
          {
            name: 'Demand trend',
            description: 'Highlights pricing power and revenue implications.',
          },
        ],
        generation_state: 'succeeded',
        lens_results: [
          {
            id: 'lens-result-1',
            lens: 'Demand trend',
            generation_state: 'succeeded',
            error_message: null,
            suggestions: [],
          },
        ],
        created_at: '2026-05-05T00:00:00Z',
        updated_at: '2026-05-05T00:00:00Z',
      });
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  renderProjectRoute();
  fireEvent.click(await screen.findByRole('button', { name: 'market.md' }));

  const suggestionsPanel = await screen.findByRole('region', { name: 'AI suggestions' });
  expect(within(suggestionsPanel).getByText('Demand trend')).toBeInTheDocument();
  expect(
    within(suggestionsPanel).getByText('Highlights pricing power and revenue implications.'),
  ).toBeInTheDocument();
  expect(within(suggestionsPanel).getByRole('button', { name: 'Regenerate lenses' })).toBeInTheDocument();
  expect(screen.getByText('Accepted note persists.')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `pnpm --dir apps/web exec vitest run src/routes/project.test.tsx src/lib/api.test.ts`

Expected: FAIL because the current UI still renders the fixed checkbox lens picker and the create-analysis request still includes a `lenses` array.

- [ ] **Step 3: Replace the frontend contract and panel logic**

```ts
// apps/web/src/lib/api.ts
export type DiscoveredLens = {
  name: string;
  description: string;
};

export type LensDiscoveryState = 'queued' | 'running' | 'succeeded' | 'failed';

export type AnalysisSuggestion = {
  id: string;
  analysis_run_id: string;
  lens: string;
  body: string;
  review_state: SuggestionReviewState;
  created_at: string;
  updated_at: string;
  anchor: QuoteAnchor;
};

export type AnalysisLensResult = {
  id: string;
  lens: string;
  generation_state: AnalysisLensGenerationState;
  error_message: string | null;
  suggestions: AnalysisSuggestion[];
};

export type AnalysisRun = {
  id: string;
  project_id: string;
  resource_id: string;
  lens_discovery_status: LensDiscoveryState;
  discovered_lenses: DiscoveredLens[];
  generation_state: AnalysisRunGenerationState;
  lens_results: AnalysisLensResult[];
  created_at: string;
  updated_at: string;
};

export type CreateAnalysisRunInput = {
  resource_id: string;
};

export async function regenerateLenses(resourceId: string): Promise<AnalysisRun> {
  const response = await fetch(`/api/resources/${resourceId}/analysis-runs/regenerate-lenses`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to regenerate lenses');
  }
  return (await response.json()) as AnalysisRun;
}

export function useRegenerateLensesMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: regenerateLenses,
    onSuccess: async (analysisRun) => {
      queryClient.setQueryData<AnalysisRun | null>(
        latestAnalysisRunQueryKey(analysisRun.resource_id),
        analysisRun,
      );
      await queryClient.invalidateQueries({
        queryKey: latestAnalysisRunQueryKey(analysisRun.resource_id),
      });
    },
  });
}
```

```tsx
// apps/web/src/components/lens-picker.tsx
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
            <strong>{lens.name}</strong>
            <p>{lens.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

```tsx
// apps/web/src/components/ai-suggestions-panel.tsx
type AiSuggestionsPanelProps = {
  resourceId: string | null;
  analysisRun: AnalysisRun | null;
  onRunAnalysis: () => void;
  onRegenerateLenses: () => void;
  onRetryFailed: () => void;
  onAcceptSuggestion: (suggestionId: string) => void;
  onDiscardSuggestion: (suggestionId: string) => void;
  isRunningAnalysis: boolean;
  isRegeneratingLenses: boolean;
  isRetryingFailed: boolean;
  isAcceptingSuggestion: boolean;
  isDiscardingSuggestion: boolean;
  errorMessage: string | null;
};

export function AiSuggestionsPanel({
  resourceId,
  analysisRun,
  onRunAnalysis,
  onRegenerateLenses,
  onRetryFailed,
  onAcceptSuggestion,
  onDiscardSuggestion,
  isRunningAnalysis,
  isRegeneratingLenses,
  isRetryingFailed,
  isAcceptingSuggestion,
  isDiscardingSuggestion,
  errorMessage,
}: AiSuggestionsPanelProps) {
  const failedLenses =
    analysisRun?.lens_results.filter((lensResult) => lensResult.generation_state === 'failed') ?? [];
  const activeSuggestions = analysisRun
    ? analysisRun.lens_results.flatMap((lensResult) =>
        lensResult.suggestions.filter((suggestion) => suggestion.review_state === 'unreviewed'),
      )
    : [];
  const showDiscoveryState =
    analysisRun?.lens_discovery_status === 'queued' || analysisRun?.lens_discovery_status === 'running';
  const showGenerationState =
    analysisRun?.lens_discovery_status === 'succeeded' &&
    (analysisRun.generation_state === 'queued' || analysisRun.generation_state === 'running');

  if (!resourceId) {
    return (
      <section aria-label="AI suggestions">
        <h2>AI suggestions</h2>
        <p>Select a document to analyze.</p>
      </section>
    );
  }

  return (
    <section aria-label="AI suggestions">
      <h2>AI suggestions</h2>
      {analysisRun ? (
        <button type="button" onClick={onRegenerateLenses} disabled={isRegeneratingLenses || isRunningAnalysis}>
          {isRegeneratingLenses ? 'Regenerating lenses...' : 'Regenerate lenses'}
        </button>
      ) : (
        <button type="button" onClick={onRunAnalysis} disabled={isRunningAnalysis}>
          {isRunningAnalysis ? 'Running analysis...' : 'Run analysis'}
        </button>
      )}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {showDiscoveryState ? <p>Discovering lenses...</p> : null}
      {showGenerationState ? <p>Generating suggestions...</p> : null}
      {analysisRun?.discovered_lenses.length ? (
        <LensPicker discoveredLenses={analysisRun.discovered_lenses} />
      ) : null}
      {failedLenses.length > 0 ? (
        <button type="button" onClick={onRetryFailed} disabled={isRetryingFailed}>
          {isRetryingFailed ? 'Retrying failed lenses...' : 'Retry failed lenses'}
        </button>
      ) : null}
      {activeSuggestions.length > 0 ? (
        <ul>
          {activeSuggestions.map((suggestion) => (
            <li key={suggestion.id}>
              <p>{suggestion.lens}</p>
              <blockquote>
                <p>{suggestion.anchor.quoteText}</p>
              </blockquote>
              <p>{suggestion.body}</p>
              <button
                type="button"
                onClick={() => onAcceptSuggestion(suggestion.id)}
                disabled={isAcceptingSuggestion || isDiscardingSuggestion}
              >
                Accept suggestion
              </button>
              <button
                type="button"
                onClick={() => onDiscardSuggestion(suggestion.id)}
                disabled={isAcceptingSuggestion || isDiscardingSuggestion}
              >
                Discard suggestion
              </button>
            </li>
          ))}
        </ul>
      ) : analysisRun && !showDiscoveryState && !showGenerationState ? (
        <p>No AI suggestions awaiting review.</p>
      ) : null}
    </section>
  );
}
```

```tsx
// apps/web/src/routes/project.tsx
const createAnalysisRunMutation = useCreateAnalysisRunMutation(projectId);
const regenerateLensesMutation = useRegenerateLensesMutation();

const isRunningAnalysis =
  createAnalysisRunMutation.isPending ||
  regenerateLensesMutation.isPending ||
  retryAnalysisRunMutation.isPending ||
  latestAnalysisRun?.lens_discovery_status === 'queued' ||
  latestAnalysisRun?.lens_discovery_status === 'running' ||
  latestAnalysisRun?.generation_state === 'queued' ||
  latestAnalysisRun?.generation_state === 'running';

async function handleRunAnalysis() {
  if (!resourceId) {
    return;
  }
  await createAnalysisRunMutation.mutateAsync({ resource_id: resourceId });
}

async function handleRegenerateLenses() {
  if (!resourceId) {
    return;
  }
  await regenerateLensesMutation.mutateAsync(resourceId);
}

<AiSuggestionsPanel
  resourceId={resourceId}
  analysisRun={latestAnalysisRun}
  onRunAnalysis={handleRunAnalysis}
  onRegenerateLenses={handleRegenerateLenses}
  onRetryFailed={handleRetryAnalysis}
  onAcceptSuggestion={handleAcceptSuggestion}
  onDiscardSuggestion={handleDiscardSuggestion}
  isRunningAnalysis={isRunningAnalysis}
  isRegeneratingLenses={regenerateLensesMutation.isPending}
  isRetryingFailed={retryAnalysisRunMutation.isPending}
  isAcceptingSuggestion={acceptAnalysisSuggestionMutation.isPending}
  isDiscardingSuggestion={discardAnalysisSuggestionMutation.isPending}
  errorMessage={analysisErrorMessage}
/>
```

- [ ] **Step 4: Re-run frontend tests**

Run: `pnpm --dir apps/web exec vitest run src/routes/project.test.tsx src/lib/api.test.ts && pnpm --dir apps/web exec tsc --noEmit`

Expected: PASS with the fixed-lens assumptions removed and the new discovery-state UI covered.

- [ ] **Step 5: Commit the frontend discovery UI**

```bash
git add apps/web/src/lib/api.ts apps/web/src/components/lens-picker.tsx apps/web/src/components/ai-suggestions-panel.tsx apps/web/src/routes/project.tsx apps/web/src/routes/project.test.tsx apps/web/src/lib/api.test.ts
git commit -m "feat: show ai-discovered lens state"
```

## Task 4: Final Verification, Smoke Coverage, And Progress Logging

**Files:**
- Modify: `apps/web/e2e/reading-workspace.spec.ts` (only if needed)
- Modify: `devlogs.md`

- [ ] **Step 1: Append the implementation milestone to the dev log**

```md
# devlogs.md append
- Task 8 progress: replaced the fixed lens checklist with AI-discovered document-specific lenses, first-run discovery, explicit regeneration, retry without rediscovery, and latest-run-only AI panel behavior while accepted notes remain in the notes panel.
```

- [ ] **Step 2: Run the full verification suite**

Run: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head && uv run --project apps/api pytest apps/api/tests -q && uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src && pnpm --dir apps/web exec vitest run && pnpm --dir apps/web exec tsc --noEmit && pnpm exec playwright test apps/web/e2e/reading-workspace.spec.ts`

Expected: PASS with:
- backend migrations applying cleanly
- all backend tests green
- `mypy --strict` clean
- frontend tests green
- the reading-workspace smoke test still completing the create → upload → note → analyze → accept path

- [ ] **Step 3: Commit the completed feature**

```bash
git add devlogs.md apps/web/e2e/reading-workspace.spec.ts
git commit -m "feat: add ai-discovered analysis lenses"
```

## Self-Review Checklist

- Spec coverage
  - first run auto-discovers lenses and then generates suggestions: Task 2
  - discovered lenses are open-ended and read-only: Tasks 1 and 3
  - latest-run-only AI panel behavior: Task 3
  - explicit regenerate-lenses action: Tasks 2 and 3
  - retry failed lenses does not rediscover: Task 2
  - accepted notes persist across regenerated runs: Tasks 2 and 3
- Placeholder scan
  - no ellipsis placeholders, `TODO`, or omitted route/schema semantics remain in this plan
- Type consistency
  - fixed `LensName` literals are removed from run payloads and UI contracts
  - `lens_discovery_status`, `generation_state`, and `review_state` stay separate across models, routes, tests, and UI

## Execution Notes

- Implement this plan on `reading-workspace-foundation`; do not start a new feature branch.
- Keep commits scoped to the tasks above.
- Do not bundle the later report-generation work into this change.
