import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from writer_assistance_api.ai.client import DiscoveredLens, resolve_analysis_lens
from writer_assistance_api.app import create_app
from writer_assistance_api.models import AnalysisRun, AnalysisRunLensResult
from writer_assistance_api.schemas.analysis_runs import CreateAnalysisRunRequest
from writer_assistance_api.services.analysis_runs import AnalysisRunsService


def test_first_run_discovers_lenses_and_generates_suggestions(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            }
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
    queued_run = create_response.json()
    assert queued_run["lens_discovery_status"] == "queued"
    assert queued_run["discovered_lenses"] == []
    assert queued_run["generation_state"] == "queued"
    assert queued_run["lens_results"] == []

    run = client.get(f"/analysis-runs/{queued_run['id']}").json()

    assert run["lens_discovery_status"] == "succeeded"
    assert run["discovered_lenses"] == [
        {
            "name": "Demand trend",
            "description": "Highlights pricing power and revenue implications.",
        }
    ]
    assert run["generation_state"] == "succeeded"
    assert [item["lens"] for item in run["lens_results"]] == ["Demand trend"]
    assert run["lens_results"][0]["generation_state"] == "succeeded"
    assert run["lens_results"][0]["suggestions"][0]["review_state"] == "unreviewed"
    assert ai_client.discover_call_count == 1
    assert [call["lens_name"] for call in ai_client.analyze_calls] == ["Demand trend"]
    assert [call["lens_description"] for call in ai_client.analyze_calls] == [
        "Highlights pricing power and revenue implications."
    ]

    with client.app.state.session_factory() as session:
        stored_run = session.execute(
            text(
                """
                SELECT lens_discovery_status, discovered_lenses, requested_lenses, generation_state
                FROM analysis_runs
                """
            )
        ).mappings().one()

    assert stored_run["lens_discovery_status"] == "succeeded"
    assert _json_value(stored_run["discovered_lenses"]) == run["discovered_lenses"]
    assert _json_value(stored_run["requested_lenses"]) == ["Demand trend"]
    assert stored_run["generation_state"] == "succeeded"


def test_duplicate_discovered_lens_names_are_deduped_before_generation(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            },
            {
                "name": "Demand trend",
                "description": "Duplicate copy that should not create a second lens result.",
            },
            {
                "name": "Execution risk",
                "description": "Looks for operational constraints in the same document.",
            },
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

    with client.app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=client.app.state.storage,
            ai_client=ai_client,
        )
        queued_run = service.create_analysis_run(
            project["id"],
            CreateAnalysisRunRequest(resource_id=resource["id"]),
        )

        service.process_analysis_run(queued_run.id)
        run = service.get_analysis_run(queued_run.id)
        stored_run = session.execute(
            text(
                """
                SELECT discovered_lenses, requested_lenses
                FROM analysis_runs
                WHERE id = :run_id
                """
            ),
            {"run_id": queued_run.id},
        ).mappings().one()

    assert run.generation_state == "succeeded"
    assert [lens.name for lens in run.discovered_lenses] == ["Demand trend", "Execution risk"]
    assert [lens.description for lens in run.discovered_lenses] == [
        "Highlights pricing power and revenue implications.",
        "Looks for operational constraints in the same document.",
    ]
    assert [result.lens for result in run.lens_results] == ["Demand trend", "Execution risk"]
    assert [call["lens_name"] for call in ai_client.analyze_calls] == ["Demand trend", "Execution risk"]
    assert [call["lens_description"] for call in ai_client.analyze_calls] == [
        "Highlights pricing power and revenue implications.",
        "Looks for operational constraints in the same document.",
    ]
    assert _json_value(stored_run["discovered_lenses"]) == [
        {
            "name": "Demand trend",
            "description": "Highlights pricing power and revenue implications.",
        },
        {
            "name": "Execution risk",
            "description": "Looks for operational constraints in the same document.",
        },
    ]
    assert _json_value(stored_run["requested_lenses"]) == ["Demand trend", "Execution risk"]


@pytest.mark.parametrize(
    ("lens_discovery_status", "generation_state"),
    [("queued", "queued"), ("running", "running")],
)
def test_cancelled_discovery_phase_run_stays_cancelled_when_processed(
    tmp_path: Path,
    lens_discovery_status: str,
    generation_state: str,
) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            }
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

    with client.app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=client.app.state.storage,
            ai_client=ai_client,
        )
        queued_run = service.create_analysis_run(
            project["id"],
            CreateAnalysisRunRequest(resource_id=resource["id"]),
        )
        stored_run = session.get(AnalysisRun, queued_run.id)
        assert stored_run is not None
        stored_run.lens_discovery_status = lens_discovery_status
        stored_run.generation_state = generation_state
        stored_run.updated_at = datetime.now(UTC)
        session.commit()

        cancelled = service.cancel_analysis_run(queued_run.id)
        service.process_analysis_run(queued_run.id)
        final_run = service.get_analysis_run(queued_run.id)

    assert cancelled.generation_state == "cancelled"
    assert cancelled.lens_discovery_status == "cancelled"
    assert final_run.generation_state == "cancelled"
    assert final_run.lens_discovery_status == "cancelled"
    assert final_run.discovered_lenses == []
    assert final_run.lens_results == []
    assert ai_client.discover_call_count == 0
    assert ai_client.analyze_calls == []


def test_discovery_failure_surfaces_error_summary_in_api_state(tmp_path: Path) -> None:
    ai_client = FailingLensDiscoveryAiClient("Lens discovery timed out")
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    )

    assert create_response.status_code == 202
    queued_run = create_response.json()
    assert queued_run["error_summary"] is None

    failed_run = client.get(f"/analysis-runs/{queued_run['id']}").json()

    assert failed_run["lens_discovery_status"] == "failed"
    assert failed_run["generation_state"] == "failed"
    assert failed_run["lens_results"] == []
    assert failed_run["error_summary"] == "Lens discovery failed. Regenerate lenses to try again."
    assert ai_client.discover_call_count == 1
    assert ai_client.analyze_call_count == 0


def test_retry_rejects_active_run_with_failed_lenses(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient()
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    with client.app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=client.app.state.storage,
            ai_client=ai_client,
        )
        queued_run = service.create_analysis_run(
            project["id"],
            CreateAnalysisRunRequest(resource_id=resource["id"]),
        )
        stored_run = session.get(AnalysisRun, queued_run.id)
        assert stored_run is not None

        now = datetime.now(UTC)
        stored_run.lens_discovery_status = "succeeded"
        stored_run.discovered_lenses = [
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            },
            {
                "name": "Policy risk",
                "description": "Checks whether policy language changes the interpretation.",
            },
        ]
        stored_run.requested_lenses = ["Demand trend", "Policy risk"]
        stored_run.generation_state = "running"
        stored_run.updated_at = now
        session.add_all(
            [
                AnalysisRunLensResult(
                    id=str(uuid4()),
                    analysis_run_id=queued_run.id,
                    lens="Demand trend",
                    generation_state="failed",
                    error_message="Lens timed out",
                    created_at=now,
                    updated_at=now,
                ),
                AnalysisRunLensResult(
                    id=str(uuid4()),
                    analysis_run_id=queued_run.id,
                    lens="Policy risk",
                    generation_state="running",
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    retry_response = client.post(f"/analysis-runs/{queued_run.id}/retry")

    assert retry_response.status_code == 409
    assert retry_response.json() == {"detail": "Analysis run is still active"}

    run = client.get(f"/analysis-runs/{queued_run.id}").json()
    assert run["generation_state"] == "running"
    assert [item["generation_state"] for item in run["lens_results"]] == ["failed", "running"]


def test_retry_failed_lenses_reuses_existing_discovered_lenses(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            },
            {
                "name": "Policy risk",
                "description": "Checks whether policy language changes the interpretation.",
            },
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

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    )
    assert create_response.status_code == 202
    first_run = create_response.json()
    completed = client.get(f"/analysis-runs/{first_run['id']}").json()

    assert completed["generation_state"] == "completed_with_failures"
    assert completed["lens_discovery_status"] == "succeeded"
    assert [item["generation_state"] for item in completed["lens_results"]] == [
        "succeeded",
        "failed",
    ]

    retry_response = client.post(f"/analysis-runs/{first_run['id']}/retry")

    assert retry_response.status_code == 202
    queued_retry_run = retry_response.json()
    assert queued_retry_run["id"] == first_run["id"]
    assert queued_retry_run["lens_discovery_status"] == "succeeded"
    assert queued_retry_run["generation_state"] == "queued"
    assert queued_retry_run["discovered_lenses"] == completed["discovered_lenses"]
    assert [item["generation_state"] for item in queued_retry_run["lens_results"]] == [
        "succeeded",
        "queued",
    ]
    assert [item["review_state"] for item in queued_retry_run["lens_results"][0]["suggestions"]] == [
        "unreviewed"
    ]
    assert queued_retry_run["lens_results"][1]["suggestions"] == []

    retried = client.get(f"/analysis-runs/{first_run['id']}").json()

    assert retried["generation_state"] == "succeeded"
    assert retried["discovered_lenses"] == completed["discovered_lenses"]
    assert [item["generation_state"] for item in retried["lens_results"]] == ["succeeded", "succeeded"]
    assert [item["review_state"] for item in retried["lens_results"][0]["suggestions"]] == ["unreviewed"]
    assert [item["review_state"] for item in retried["lens_results"][1]["suggestions"]] == ["unreviewed"]
    assert ai_client.discover_call_count == 1
    assert [call["lens_name"] for call in ai_client.analyze_calls] == [
        "Demand trend",
        "Policy risk",
        "Policy risk",
    ]


def test_regenerate_lenses_replaces_latest_run_but_preserves_accepted_notes(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses_sequence=[
            [
                {
                    "name": "Demand trend",
                    "description": "Highlights pricing power and revenue implications.",
                }
            ],
            [
                {
                    "name": "Execution risk",
                    "description": "Looks for operational constraints in the same document.",
                }
            ],
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

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    )
    assert create_response.status_code == 202
    first_run = create_response.json()
    first_details = client.get(f"/analysis-runs/{first_run['id']}").json()
    accepted = client.post(
        f"/analysis-suggestions/{first_details['lens_results'][0]['suggestions'][0]['id']}/accept"
    ).json()

    regenerate_response = client.post(f"/resources/{resource['id']}/analysis-runs/regenerate-lenses")

    assert regenerate_response.status_code == 202
    queued_regenerated_run = regenerate_response.json()
    assert queued_regenerated_run["id"] != first_details["id"]
    assert queued_regenerated_run["lens_discovery_status"] == "queued"
    assert queued_regenerated_run["discovered_lenses"] == []
    assert queued_regenerated_run["lens_results"] == []

    latest = client.get(f"/resources/{resource['id']}/analysis-runs/latest").json()
    original = client.get(f"/analysis-runs/{first_details['id']}").json()
    annotations = client.get(f"/resources/{resource['id']}/annotations").json()["annotations"]

    assert latest["id"] == queued_regenerated_run["id"]
    assert latest["discovered_lenses"] == [
        {
            "name": "Execution risk",
            "description": "Looks for operational constraints in the same document.",
        }
    ]
    assert latest["discovered_lenses"] != first_details["discovered_lenses"]
    assert latest["lens_results"][0]["lens"] == "Execution risk"
    assert original["lens_results"][0]["suggestions"][0]["review_state"] == "accepted"
    assert [annotation["body"] for annotation in annotations] == [accepted["annotation"]["body"]]
    assert ai_client.discover_call_count == 2


def test_accept_and_discard_persist_review_state_and_annotation_provenance(tmp_path: Path) -> None:
    ai_client = DiscoveryScriptedAiClient(
        discovered_lenses=[
            {
                "name": "Demand trend",
                "description": "Highlights pricing power and revenue implications.",
            },
            {
                "name": "Execution risk",
                "description": "Looks for operational constraints in the same document.",
            },
        ],
        outcomes_by_lens={
            "Demand trend": [
                [
                    suggestion_payload(
                        body="Capture the demand signal in the final memo.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "Execution risk": [
                [
                    suggestion_payload(
                        body="Flag the permitting delay as a delivery risk.",
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

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={"resource_id": resource["id"]},
    )

    assert create_response.status_code == 202
    created_run = client.get(f"/resources/{resource['id']}/analysis-runs/latest").json()
    first_suggestion = created_run["lens_results"][0]["suggestions"][0]
    second_suggestion = created_run["lens_results"][1]["suggestions"][0]

    accept_response = client.post(f"/analysis-suggestions/{first_suggestion['id']}/accept")

    assert accept_response.status_code == 201
    accepted_payload = accept_response.json()
    assert accepted_payload["suggestion"]["id"] == first_suggestion["id"]
    assert accepted_payload["suggestion"]["review_state"] == "accepted"
    assert accepted_payload["annotation"]["resource_id"] == resource["id"]
    assert accepted_payload["annotation"]["body"] == first_suggestion["body"]
    assert accepted_payload["annotation"]["origin_type"] == "accepted_ai"
    assert accepted_payload["annotation"]["provenance_source_id"] == first_suggestion["id"]
    assert accepted_payload["annotation"]["anchor"] == first_suggestion["anchor"]

    discard_response = client.post(f"/analysis-suggestions/{second_suggestion['id']}/discard")

    assert discard_response.status_code == 200
    assert discard_response.json()["suggestion"]["id"] == second_suggestion["id"]
    assert discard_response.json()["suggestion"]["review_state"] == "discarded"

    annotations_response = client.get(f"/resources/{resource['id']}/annotations")

    assert annotations_response.status_code == 200
    assert annotations_response.json()["annotations"] == [accepted_payload["annotation"]]

    details_response = client.get(f"/analysis-runs/{created_run['id']}")

    assert details_response.status_code == 200
    suggestions_by_id = {
        suggestion["id"]: suggestion
        for lens_result in details_response.json()["lens_results"]
        for suggestion in lens_result["suggestions"]
    }
    assert suggestions_by_id[first_suggestion["id"]]["review_state"] == "accepted"
    assert suggestions_by_id[second_suggestion["id"]]["review_state"] == "discarded"

    with client.app.state.session_factory() as session:
        stored_suggestions = session.execute(
            text(
                """
                SELECT id, review_state
                FROM analysis_suggestions
                """
            )
        ).mappings().all()
        stored_annotations = session.execute(
            text(
                """
                SELECT body, origin_type, provenance_source_id
                FROM annotations
                ORDER BY id
                """
            )
        ).mappings().all()

    assert {row["id"]: row["review_state"] for row in stored_suggestions} == {
        first_suggestion["id"]: "accepted",
        second_suggestion["id"]: "discarded",
    }
    assert stored_annotations == [
        {
            "body": "Capture the demand signal in the final memo.",
            "origin_type": "accepted_ai",
            "provenance_source_id": first_suggestion["id"],
        }
    ]


class DiscoveryScriptedAiClient:
    def __init__(
        self,
        *,
        discovered_lenses: Sequence[dict[str, str] | DiscoveredLens] | None = None,
        discovered_lenses_sequence: Sequence[Sequence[dict[str, str] | DiscoveredLens]] | None = None,
        outcomes_by_lens: dict[str, Sequence[Sequence[dict[str, object]] | Exception]] | None = None,
    ) -> None:
        if discovered_lenses is not None and discovered_lenses_sequence is not None:
            raise ValueError("Provide discovered_lenses or discovered_lenses_sequence, not both")

        if discovered_lenses_sequence is None:
            initial_lenses = [] if discovered_lenses is None else list(discovered_lenses)
            self._discovered_lenses_sequence = [self._normalize_lenses(initial_lenses)]
        else:
            self._discovered_lenses_sequence = [
                self._normalize_lenses(sequence) for sequence in discovered_lenses_sequence
            ]
        self._outcomes_by_lens = {lens: list(outcomes) for lens, outcomes in (outcomes_by_lens or {}).items()}
        self.discover_call_count = 0
        self.discover_calls: list[dict[str, str]] = []
        self.analyze_calls: list[dict[str, str]] = []

    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        self.discover_call_count += 1
        self.discover_calls.append({"markdown": markdown, "logical_path": logical_path})
        assert logical_path == "research/market.md"
        assert markdown == "# Market\n\nDemand is rising.\n\nRules are changing."
        if not self._discovered_lenses_sequence:
            return []
        index = min(self.discover_call_count - 1, len(self._discovered_lenses_sequence) - 1)
        return [lens.model_copy(deep=True) for lens in self._discovered_lenses_sequence[index]]

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: str | None = None,
    ) -> list[dict[str, object]]:
        resolved_lens_name, resolved_lens_description = resolve_analysis_lens(
            lens_name=lens_name,
            lens_description=lens_description,
            lens=lens,
        )
        self.analyze_calls.append(
            {
                "lens_name": resolved_lens_name,
                "lens_description": resolved_lens_description,
                "markdown": markdown,
                "logical_path": logical_path,
            }
        )
        assert logical_path == "research/market.md"
        assert markdown == "# Market\n\nDemand is rising.\n\nRules are changing."
        outcomes = self._outcomes_by_lens.get(resolved_lens_name)
        assert outcomes is not None, f"Unexpected lens: {resolved_lens_name}"
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return list(outcome)

    @staticmethod
    def _normalize_lenses(
        lenses: Sequence[dict[str, str] | DiscoveredLens],
    ) -> list[DiscoveredLens]:
        normalized: list[DiscoveredLens] = []
        for lens in lenses:
            if isinstance(lens, DiscoveredLens):
                normalized.append(lens)
            else:
                normalized.append(DiscoveredLens.model_validate(lens))
        return normalized


class FailingLensDiscoveryAiClient:
    def __init__(self, message: str) -> None:
        self._message = message
        self.discover_call_count = 0
        self.analyze_call_count = 0

    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        self.discover_call_count += 1
        assert logical_path == "research/market.md"
        assert markdown == "# Market\n\nDemand is rising.\n\nRules are changing."
        raise RuntimeError(self._message)

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: str | None = None,
    ) -> list[dict[str, object]]:
        del markdown, logical_path, lens_name, lens_description, lens
        self.analyze_call_count += 1
        raise AssertionError("analyze_resource should not run after discovery fails")


def suggestion_payload(
    *,
    body: str,
    quote_text: str,
    start_offset: int,
    end_offset: int,
) -> dict[str, object]:
    return {
        "body": body,
        "anchor": {
            "quoteText": quote_text,
            "normalizedText": quote_text.lower(),
            "startOffset": start_offset,
            "endOffset": end_offset,
            "blockPath": ["paragraph", "1"],
            "resolutionStatus": "exact",
        },
    }


def _create_client(tmp_path: Path, *, ai_client: object) -> TestClient:
    return TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
            ai_client=ai_client,
        )
    )


def _create_project(client: TestClient) -> dict[str, str]:
    response = client.post("/projects", json={"title": "Research Memo"})
    assert response.status_code == 201
    return response.json()


def _upload_resource(client: TestClient, *, project_id: str) -> dict[str, str]:
    response = client.post(
        f"/projects/{project_id}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            (
                "files",
                (
                    "market.md",
                    b"# Market\n\nDemand is rising.\n\nRules are changing.",
                    "text/markdown",
                ),
            ),
        ],
    )

    assert response.status_code == 201
    return response.json()["resources"][0]


def _json_value(value: object) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value
