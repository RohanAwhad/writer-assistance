"""Run database migrations. Idempotent — safe to run multiple times.

Adds 'status' field to each note object in the lenses.notes JSON column.
Notes that were already added to the notes table are marked 'accepted',
all others are marked 'pending'.
"""

import asyncio
import json
import aiosqlite
from app.db import DB_PATH


async def backfill_note_status(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT id, notes FROM lenses")
    lenses = await cursor.fetchall()

    for lens_id, notes_json in lenses:
        lens_notes: list[dict] = json.loads(notes_json)

        if lens_notes and "status" in lens_notes[0]:
            print(f"  lens {lens_id}: already has status, skipping")
            continue

        # find which notes were accepted (exist in notes table for this lens)
        cursor2 = await db.execute(
            "SELECT content FROM notes WHERE lens_id = ? AND note_type = 'lens'",
            (lens_id,),
        )
        accepted_contents = {row[0] for row in await cursor2.fetchall()}

        for note in lens_notes:
            if note["content"] in accepted_contents:
                note["status"] = "accepted"
            else:
                note["status"] = "pending"

        await db.execute(
            "UPDATE lenses SET notes = ? WHERE id = ?",
            (json.dumps(lens_notes), lens_id),
        )
        accepted_count = sum(1 for n in lens_notes if n["status"] == "accepted")
        print(f"  lens {lens_id}: {accepted_count}/{len(lens_notes)} marked accepted")


async def migrate() -> None:
    db = await aiosqlite.connect(str(DB_PATH))
    await backfill_note_status(db)
    await db.commit()
    await db.close()


if __name__ == "__main__":
    print("Running migrations...")
    asyncio.run(migrate())
    print("Done.")
