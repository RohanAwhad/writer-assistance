"""Project and resource-tree routes (F1/F2; spec §6)."""

from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile

from app.deps import DbDep, ResourceAiDep
from app.errors import PayloadTooLargeError
from app.schemas import (
    AnnotationOut,
    AnnotationUpdate,
    HighlightCreate,
    ImportResult,
    LensProposalOut,
    LensProposalStatusUpdate,
    NoteCreate,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProviderUpdate,
    ResourceOut,
    TreeOut,
)
from app.services import annotations, lenses, projects, resources

router = APIRouter(tags=["projects"])

UploadFilesDep = Annotated[
    list[UploadFile], File(description="Markdown file parts (field `files`)")
]
_CAP_EXCEEDED_DETAIL = "import upload exceeds the 10 MiB cap"
_READ_CHUNK = 64 * 1024


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(db: DbDep, body: ProjectCreate) -> ProjectOut:
    return projects.create_project(db, body.name)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: DbDep) -> list[ProjectOut]:
    return projects.list_projects(db)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(db: DbDep, project_id: int) -> ProjectDetail:
    return projects.get_project(db, project_id)


@router.put("/projects/{project_id}", response_model=ProjectOut)
def rename_project(db: DbDep, project_id: int, body: ProjectCreate) -> ProjectOut:
    return projects.rename_project(db, project_id, body.name)


@router.put("/projects/{project_id}/provider", response_model=ProjectOut)
def update_project_provider(db: DbDep, project_id: int, body: ProviderUpdate) -> ProjectOut:
    return projects.set_project_provider(db, project_id, body.provider)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(db: DbDep, project_id: int) -> Response:
    projects.delete_project(db, project_id)
    return Response(status_code=204)


@router.post("/projects/{project_id}/import", response_model=ImportResult, status_code=201)
async def import_uploads(
    db: DbDep, request: Request, project_id: int, files: UploadFilesDep
) -> ImportResult:
    """Browser-upload import (R-079): multipart ``files`` parts -> snapshot.

    The cap (SD-29) is enforced on the parsed upload content while it is read
    here — starlette has already parsed/spooled the full multipart body by the
    time this route runs — so an over-cap request raises 413 before any
    validation or persistence; a rejected request persists nothing.
    """
    cap = int(request.app.state.import_cap_bytes)
    uploads: list[tuple[str, bytes]] = []
    total = 0
    for part in files:
        content = bytearray()
        while True:
            chunk = await part.read(_READ_CHUNK)
            if not chunk:
                break
            content += chunk
            total += len(chunk)
            if total > cap:
                raise PayloadTooLargeError(_CAP_EXCEEDED_DETAIL)
        uploads.append((part.filename or "", bytes(content)))
    return projects.import_uploads(db, project_id, uploads)


@router.get("/projects/{project_id}/tree", response_model=TreeOut)
def get_tree(db: DbDep, project_id: int) -> TreeOut:
    return projects.get_tree(db, project_id)


@router.get("/resources/{resource_id}", response_model=ResourceOut)
def get_resource(db: DbDep, resource_id: int) -> ResourceOut:
    return resources.get_resource(db, resource_id)


@router.post("/resources/{resource_id}/highlights", response_model=AnnotationOut, status_code=201)
def create_highlight(db: DbDep, resource_id: int, body: HighlightCreate) -> AnnotationOut:
    return annotations.create_highlight(db, resource_id, body)


@router.post("/resources/{resource_id}/notes", response_model=AnnotationOut, status_code=201)
def create_note(db: DbDep, resource_id: int, body: NoteCreate) -> AnnotationOut:
    return annotations.create_note(db, resource_id, body)


@router.get("/resources/{resource_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(db: DbDep, resource_id: int) -> list[AnnotationOut]:
    return annotations.list_annotations(db, resource_id)


@router.put("/annotations/{annotation_id}", response_model=AnnotationOut)
def update_annotation(db: DbDep, annotation_id: int, body: AnnotationUpdate) -> AnnotationOut:
    return annotations.update_annotation(db, annotation_id, body)


@router.delete("/annotations/{annotation_id}", status_code=204)
def delete_annotation(db: DbDep, annotation_id: int) -> Response:
    annotations.delete_annotation(db, annotation_id)
    return Response(status_code=204)


@router.post(
    "/resources/{resource_id}/lens-proposals",
    response_model=list[LensProposalOut],
    status_code=201,
)
def propose_lenses(db: DbDep, ai: ResourceAiDep, resource_id: int) -> list[LensProposalOut]:
    return lenses.propose_lenses(db, ai, resource_id)


@router.get("/resources/{resource_id}/lens-proposals", response_model=list[LensProposalOut])
def list_lens_proposals(db: DbDep, resource_id: int) -> list[LensProposalOut]:
    return lenses.list_lens_proposals(db, resource_id)


@router.patch("/lens-proposals/{proposal_id}", response_model=LensProposalOut)
def update_lens_proposal_status(
    db: DbDep, proposal_id: int, body: LensProposalStatusUpdate
) -> LensProposalOut:
    return lenses.update_lens_proposal_status(db, proposal_id, body.status)
