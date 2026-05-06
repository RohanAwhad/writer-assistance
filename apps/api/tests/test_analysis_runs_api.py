from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from writer_assistance_api.ai.client import AiClient
from writer_assistance_api.app import create_app
from writer_assistance_api.schemas.analysis_runs import CreateAnalysisRunRequest
from writer_assistance_api.services.analysis_runs import AnalysisRunsService


def test_create_analysis_run_returns_queued_then_latest_read_shows_completed_results(
    tmp_path: Path,
) -> None:
    ai_client = ScriptedAiClient(
        {
            "financial": [
                [
                    suggestion_payload(
                        body="Call out the demand trend as evidence of pricing power.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "political": [
                RuntimeError("Political lens timed out"),
                [
                    suggestion_payload(
                        body="Note the zoning pressure as a policy risk to monitor.",
                        quote_text="Rules are changing.",
                        start_offset=19,
                        end_offset=38,
                    )
                ],
            ],
        }
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={
            "resource_id": resource["id"],
            "lenses": ["financial", "political"],
        },
    )

    assert create_response.status_code == 202
    created_run = create_response.json()
    assert created_run["generation_state"] == "queued"
    assert [item["lens"] for item in created_run["lens_results"]] == ["financial", "political"]

    financial_result, political_result = created_run["lens_results"]
    assert financial_result["generation_state"] == "queued"
    assert political_result["generation_state"] == "queued"
    assert financial_result["error_message"] is None
    assert political_result["error_message"] is None
    assert financial_result["suggestions"] == []
    assert political_result["suggestions"] == []

    details_response = client.get(f"/analysis-runs/{created_run['id']}")
    latest_response = client.get(f"/resources/{resource['id']}/analysis-runs/latest")

    assert details_response.status_code == 200
    assert latest_response.status_code == 200
    assert latest_response.json() == details_response.json()

    completed_run = details_response.json()
    assert completed_run["generation_state"] == "completed_with_failures"
    assert [item["lens"] for item in completed_run["lens_results"]] == ["financial", "political"]

    completed_financial_result, completed_political_result = completed_run["lens_results"]
    assert completed_financial_result["generation_state"] == "succeeded"
    assert completed_political_result["generation_state"] == "failed"
    assert completed_political_result["error_message"] == "Political lens timed out"
    assert [item["review_state"] for item in completed_financial_result["suggestions"]] == ["unreviewed"]
    assert completed_financial_result["suggestions"][0]["body"] == (
        "Call out the demand trend as evidence of pricing power."
    )
    assert ai_client.calls == ["financial", "political"]

    with client.app.state.session_factory() as session:
        stored_run = session.execute(
            text(
                """
                SELECT generation_state
                FROM analysis_runs
                """
            )
        ).mappings().one()
        stored_lens_rows = session.execute(
            text(
                """
                SELECT lens, generation_state, error_message
                FROM analysis_run_lens_results
                ORDER BY lens
                """
            )
        ).mappings().all()
        stored_suggestions = session.execute(
            text(
                """
                SELECT lens, review_state
                FROM analysis_suggestions
                ORDER BY lens
                """
            )
        ).mappings().all()

    assert stored_run["generation_state"] == "completed_with_failures"
    assert stored_lens_rows == [
        {"lens": "financial", "generation_state": "succeeded", "error_message": None},
        {
            "lens": "political",
            "generation_state": "failed",
            "error_message": "Political lens timed out",
        },
    ]
    assert stored_suggestions == [{"lens": "financial", "review_state": "unreviewed"}]


def test_retry_returns_queued_and_only_retries_failed_lenses(tmp_path: Path) -> None:
    ai_client = ScriptedAiClient(
        {
            "financial": [
                [
                    suggestion_payload(
                        body="Call out the demand trend as evidence of pricing power.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "political": [
                RuntimeError("Political lens timed out"),
                [
                    suggestion_payload(
                        body="Note the zoning pressure as a policy risk to monitor.",
                        quote_text="Rules are changing.",
                        start_offset=19,
                        end_offset=38,
                    )
                ],
            ],
        }
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={
            "resource_id": resource["id"],
            "lenses": ["financial", "political"],
        },
    )

    assert create_response.status_code == 202
    created_run = create_response.json()

    completed_run = client.get(f"/analysis-runs/{created_run['id']}").json()
    assert completed_run["generation_state"] == "completed_with_failures"

    retry_response = client.post(f"/analysis-runs/{created_run['id']}/retry")

    assert retry_response.status_code == 202
    queued_retry_run = retry_response.json()
    assert queued_retry_run["id"] == created_run["id"]
    assert queued_retry_run["generation_state"] == "queued"
    assert [item["generation_state"] for item in queued_retry_run["lens_results"]] == [
        "succeeded",
        "queued",
    ]
    assert [item["review_state"] for item in queued_retry_run["lens_results"][0]["suggestions"]] == [
        "unreviewed"
    ]
    assert queued_retry_run["lens_results"][1]["suggestions"] == []

    retried_run = client.get(f"/analysis-runs/{created_run['id']}").json()
    assert retried_run["generation_state"] == "succeeded"
    assert [item["generation_state"] for item in retried_run["lens_results"]] == ["succeeded", "succeeded"]
    assert [item["review_state"] for item in retried_run["lens_results"][0]["suggestions"]] == ["unreviewed"]
    assert [item["review_state"] for item in retried_run["lens_results"][1]["suggestions"]] == ["unreviewed"]
    assert ai_client.calls == ["financial", "political", "political"]

    with client.app.state.session_factory() as session:
        stored_lens_rows_after_retry = session.execute(
            text(
                """
                SELECT lens, generation_state, error_message
                FROM analysis_run_lens_results
                ORDER BY lens
                """
            )
        ).mappings().all()
        stored_suggestions_after_retry = session.execute(
            text(
                """
                SELECT lens, review_state
                FROM analysis_suggestions
                ORDER BY lens
                """
            )
        ).mappings().all()

    assert stored_lens_rows_after_retry == [
        {"lens": "financial", "generation_state": "succeeded", "error_message": None},
        {"lens": "political", "generation_state": "succeeded", "error_message": None},
    ]
    assert stored_suggestions_after_retry == [
        {"lens": "financial", "review_state": "unreviewed"},
        {"lens": "political", "review_state": "unreviewed"},
    ]


def test_accept_and_discard_persist_review_state_and_annotation_provenance(tmp_path: Path) -> None:
    ai_client = ScriptedAiClient(
        {
            "financial": [
                [
                    suggestion_payload(
                        body="Capture the demand signal in the final memo.",
                        quote_text="Demand is rising.",
                        start_offset=0,
                        end_offset=17,
                    )
                ]
            ],
            "real_estate": [
                [
                    suggestion_payload(
                        body="Flag the zoning change as a local market constraint.",
                        quote_text="Rules are changing.",
                        start_offset=19,
                        end_offset=38,
                    )
                ]
            ],
        }
    )
    client = _create_client(tmp_path, ai_client=ai_client)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    create_response = client.post(
        f"/projects/{project['id']}/analysis-runs",
        json={
            "resource_id": resource["id"],
            "lenses": ["financial", "real_estate"],
        },
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


def test_cancel_analysis_run_marks_queued_run_and_pending_lenses_cancelled(tmp_path: Path) -> None:
    client = _create_client(tmp_path, ai_client=ScriptedAiClient({}))
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    with client.app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=client.app.state.storage,
            ai_client=client.app.state.ai_client,
        )
        created_run = service.create_analysis_run(
            project["id"],
            CreateAnalysisRunRequest(resource_id=resource["id"], lenses=["financial", "political"]),
        )

    cancel_response = client.post(f"/analysis-runs/{created_run.id}/cancel")

    assert cancel_response.status_code == 202
    cancelled_run = cancel_response.json()
    assert cancelled_run["generation_state"] == "cancelled"
    assert [item["generation_state"] for item in cancelled_run["lens_results"]] == [
        "cancelled",
        "cancelled",
    ]
    assert [item["suggestions"] for item in cancelled_run["lens_results"]] == [[], []]

    details_response = client.get(f"/analysis-runs/{created_run.id}")

    assert details_response.status_code == 200
    assert details_response.json() == cancelled_run

    with client.app.state.session_factory() as session:
        stored_run = session.execute(
            text(
                """
                SELECT generation_state
                FROM analysis_runs
                WHERE id = :run_id
                """
            ),
            {"run_id": created_run.id},
        ).mappings().one()
        stored_lens_rows = session.execute(
            text(
                """
                SELECT lens, generation_state
                FROM analysis_run_lens_results
                WHERE analysis_run_id = :run_id
                ORDER BY lens
                """
            ),
            {"run_id": created_run.id},
        ).mappings().all()

    assert stored_run["generation_state"] == "cancelled"
    assert stored_lens_rows == [
        {"lens": "financial", "generation_state": "cancelled"},
        {"lens": "political", "generation_state": "cancelled"},
    ]


def test_cancel_running_analysis_run_keeps_mixed_cancelled_outcomes_classified_correctly(
    tmp_path: Path,
) -> None:
    app = create_app(
        database_url="sqlite+pysqlite:///:memory:",
        storage_root=tmp_path / "storage",
        ai_client=None,
    )
    client = TestClient(app)
    cancelling_client = CancellingAiClient(
        cancel_run=lambda run_id: _cancel_analysis_run(app, run_id),
    )
    app.state.ai_client = cancelling_client
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    with app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=app.state.storage,
            ai_client=app.state.ai_client,
        )
        created_run = service.create_analysis_run(
            project["id"],
            CreateAnalysisRunRequest(resource_id=resource["id"], lenses=["financial", "political"]),
        )

    cancelling_client.target_run_id = created_run.id

    with app.state.session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=app.state.storage,
            ai_client=app.state.ai_client,
        )
        service.process_analysis_run(created_run.id)

    details_response = client.get(f"/analysis-runs/{created_run.id}")

    assert details_response.status_code == 200
    processed_run = details_response.json()
    assert processed_run["generation_state"] == "completed_with_failures"
    assert [item["generation_state"] for item in processed_run["lens_results"]] == [
        "succeeded",
        "cancelled",
    ]
    assert [len(item["suggestions"]) for item in processed_run["lens_results"]] == [1, 0]
    assert cancelling_client.calls == ["financial", "political"]

    with app.state.session_factory() as session:
        stored_suggestions = session.execute(
            text(
                """
                SELECT lens, review_state
                FROM analysis_suggestions
                ORDER BY lens
                """
            )
        ).mappings().all()

    assert stored_suggestions == [{"lens": "financial", "review_state": "unreviewed"}]


class ScriptedAiClient:
    def __init__(self, outcomes_by_lens: dict[str, list[list[dict[str, object]] | Exception]]) -> None:
        self._outcomes_by_lens = {lens: list(outcomes) for lens, outcomes in outcomes_by_lens.items()}
        self.calls: list[str] = []

    def analyze_resource(
        self,
        *,
        lens: str,
        markdown: str,
        logical_path: str,
    ) -> list[dict[str, object]]:
        self.calls.append(lens)
        assert logical_path == "research/market.md"
        assert markdown == "# Market\n\nDemand is rising.\n\nRules are changing."
        outcome = self._outcomes_by_lens[lens].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class CancellingAiClient:
    def __init__(self, *, cancel_run: Callable[[str], None]) -> None:
        self._cancel_run = cancel_run
        self.target_run_id: str | None = None
        self.calls: list[str] = []

    def analyze_resource(
        self,
        *,
        lens: str,
        markdown: str,
        logical_path: str,
    ) -> list[dict[str, object]]:
        self.calls.append(lens)
        assert logical_path == "research/market.md"
        assert markdown == "# Market\n\nDemand is rising.\n\nRules are changing."

        if lens == "financial":
            return [
                suggestion_payload(
                    body="Call out the demand trend as evidence of pricing power.",
                    quote_text="Demand is rising.",
                    start_offset=0,
                    end_offset=17,
                )
            ]

        if lens == "political":
            assert self.target_run_id is not None
            self._cancel_run(self.target_run_id)
            return [
                suggestion_payload(
                    body="Note the zoning pressure as a policy risk to monitor.",
                    quote_text="Rules are changing.",
                    start_offset=19,
                    end_offset=38,
                )
            ]

        raise AssertionError(f"Unexpected lens: {lens}")


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


def _cancel_analysis_run(app: object, run_id: str) -> None:
    session_factory = app.state.session_factory
    with session_factory() as session:
        service = AnalysisRunsService(
            session=session,
            storage=app.state.storage,
            ai_client=app.state.ai_client,
        )
        service.cancel_analysis_run(run_id)


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
