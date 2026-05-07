import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ai import (
    generate_critique,
    generate_lenses,
    generate_lens_notes,
    generate_report,
    generate_tone_variations,
)
from app.db import execute, fetch_all, fetch_one, init_db


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class NoteCreate(BaseModel):
    content: str
    resource_id: int | None = None
    lens_id: int | None = None
    note_type: str = "user"
    highlight: str = ""


class NotesFromLens(BaseModel):
    lens_id: int
    note_ids: list[int]


class BlockUpdate(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/api/projects")
async def list_projects():
    return await fetch_all("SELECT * FROM projects ORDER BY created_at DESC")


@app.post("/api/projects")
async def create_project(body: ProjectCreate):
    project_id = await execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (body.name, body.description),
    )
    return await fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):
    return await fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int):
    await execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/resources")
async def list_resources(project_id: int):
    return await fetch_all(
        "SELECT id, project_id, filename, path, created_at FROM resources WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )


@app.post("/api/projects/{project_id}/resources")
async def upload_resources(project_id: int, files: list[UploadFile]):
    created = []
    for f in files:
        content = (await f.read()).decode("utf-8")
        resource_id = await execute(
            "INSERT INTO resources (project_id, filename, path, content) VALUES (?, ?, ?, ?)",
            (project_id, f.filename, f.filename, content),
        )
        row = await fetch_one("SELECT * FROM resources WHERE id = ?", (resource_id,))
        created.append(row)
    return created


@app.get("/api/resources/{resource_id}")
async def get_resource(resource_id: int):
    return await fetch_one("SELECT * FROM resources WHERE id = ?", (resource_id,))


@app.delete("/api/resources/{resource_id}")
async def delete_resource(resource_id: int):
    await execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Lenses
# ---------------------------------------------------------------------------

@app.post("/api/resources/{resource_id}/lenses/generate")
async def generate_lenses_for_resource(resource_id: int):
    resource = await fetch_one("SELECT * FROM resources WHERE id = ?", (resource_id,))

    lenses_data = await generate_lenses(resource["content"], resource["filename"])

    # generate notes for all lenses in parallel
    notes_coros = [
        generate_lens_notes(resource["content"], lens["name"], lens["perspective"])
        for lens in lenses_data
    ]
    all_notes = await asyncio.gather(*notes_coros)

    result = []
    for lens, notes in zip(lenses_data, all_notes):
        for note in notes:
            note["status"] = "pending"
        lens_id = await execute(
            "INSERT INTO lenses (resource_id, name, perspective, notes) VALUES (?, ?, ?, ?)",
            (resource_id, lens["name"], lens["perspective"], json.dumps(notes)),
        )
        row = await fetch_one("SELECT * FROM lenses WHERE id = ?", (lens_id,))
        row["notes"] = json.loads(row["notes"])
        result.append(row)

    return result


@app.get("/api/resources/{resource_id}/lenses")
async def list_lenses(resource_id: int):
    rows = await fetch_all(
        "SELECT * FROM lenses WHERE resource_id = ? ORDER BY created_at",
        (resource_id,),
    )
    for row in rows:
        row["notes"] = json.loads(row["notes"])
    return rows


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/notes")
async def list_notes(project_id: int):
    return await fetch_all(
        "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )


@app.post("/api/projects/{project_id}/notes")
async def create_note(project_id: int, body: NoteCreate):
    note_id = await execute(
        "INSERT INTO notes (project_id, resource_id, lens_id, content, note_type, highlight) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, body.resource_id, body.lens_id, body.content, body.note_type, body.highlight),
    )
    return await fetch_one("SELECT * FROM notes WHERE id = ?", (note_id,))


@app.post("/api/projects/{project_id}/notes/from-lens")
async def accept_lens_notes(project_id: int, body: NotesFromLens):
    lens = await fetch_one("SELECT * FROM lenses WHERE id = ?", (body.lens_id,))
    lens_notes: list[dict] = json.loads(lens["notes"])

    resource_id = lens["resource_id"]
    created = []
    for idx in body.note_ids:
        if lens_notes[idx].get("status") == "accepted":
            continue
        note_data = lens_notes[idx]
        note_id = await execute(
            "INSERT INTO notes (project_id, resource_id, lens_id, content, note_type, highlight) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, resource_id, body.lens_id, note_data["content"], "lens", note_data.get("highlight", "")),
        )
        row = await fetch_one("SELECT * FROM notes WHERE id = ?", (note_id,))
        created.append(row)
        lens_notes[idx]["status"] = "accepted"

    await execute(
        "UPDATE lenses SET notes = ? WHERE id = ?",
        (json.dumps(lens_notes), body.lens_id),
    )
    return created


class DiscardLensNotes(BaseModel):
    lens_id: int
    note_ids: list[int]


@app.post("/api/projects/{project_id}/notes/discard-lens")
async def discard_lens_notes(project_id: int, body: DiscardLensNotes):
    lens = await fetch_one("SELECT * FROM lenses WHERE id = ?", (body.lens_id,))
    lens_notes: list[dict] = json.loads(lens["notes"])

    for idx in body.note_ids:
        lens_notes[idx]["status"] = "discarded"

    await execute(
        "UPDATE lenses SET notes = ? WHERE id = ?",
        (json.dumps(lens_notes), body.lens_id),
    )
    return {"ok": True}


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    await execute("DELETE FROM notes WHERE id = ?", (note_id,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/reports/generate")
async def generate_project_report(project_id: int):
    project = await fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    notes = await fetch_all(
        "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at",
        (project_id,),
    )

    notes_for_ai = [{"content": n["content"], "highlight": n["highlight"]} for n in notes]
    blocks_data = await generate_report(notes_for_ai, project["name"])

    report_id = await execute(
        "INSERT INTO reports (project_id, title) VALUES (?, ?)",
        (project_id, f"Report: {project['name']}"),
    )

    for position, block in enumerate(blocks_data):
        await execute(
            "INSERT INTO report_blocks (report_id, position, content, block_type) VALUES (?, ?, ?, ?)",
            (report_id, position, block["content"], block["block_type"]),
        )

    return await _get_report_with_blocks(report_id)


@app.get("/api/reports/{report_id}")
async def get_report(report_id: int):
    return await _get_report_with_blocks(report_id)


@app.put("/api/reports/{report_id}/blocks/{block_id}")
async def update_block(report_id: int, block_id: int, body: BlockUpdate):
    await execute(
        "UPDATE report_blocks SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND report_id = ?",
        (body.content, block_id, report_id),
    )
    return await fetch_one("SELECT * FROM report_blocks WHERE id = ?", (block_id,))


@app.post("/api/reports/{report_id}/blocks/{block_id}/tone-variations")
async def get_tone_variations(report_id: int, block_id: int):
    block = await fetch_one("SELECT * FROM report_blocks WHERE id = ? AND report_id = ?", (block_id, report_id))
    full_report = await _build_report_text(report_id)
    return await generate_tone_variations(block["content"], full_report)


@app.post("/api/reports/{report_id}/blocks/{block_id}/critique")
async def get_critique(report_id: int, block_id: int):
    block = await fetch_one("SELECT * FROM report_blocks WHERE id = ? AND report_id = ?", (block_id, report_id))
    full_report = await _build_report_text(report_id)
    return await generate_critique(block["content"], full_report)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_report_with_blocks(report_id: int) -> dict:
    report = await fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    blocks = await fetch_all(
        "SELECT * FROM report_blocks WHERE report_id = ? ORDER BY position",
        (report_id,),
    )
    report["blocks"] = blocks
    return report


async def _build_report_text(report_id: int) -> str:
    blocks = await fetch_all(
        "SELECT content, block_type FROM report_blocks WHERE report_id = ? ORDER BY position",
        (report_id,),
    )
    parts = []
    for b in blocks:
        if b["block_type"] == "heading":
            parts.append(f"## {b['content']}")
        else:
            parts.append(b["content"])
    return "\n\n".join(parts)
