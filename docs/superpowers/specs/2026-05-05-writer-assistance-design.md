# Writer Assistance Design

Date: 2026-05-05
Status: Draft for user review

## Summary

`writer-assistance` is a single-user web app for research-assisted writing. A user uploads markdown source documents into a project, reads them in a rendered workspace, creates quote-anchored notes, triggers AI analysis that first discovers document-specific expert lenses and then generates visible note suggestions, and curates an approved note set. The AI system then generates an initial report draft from the approved notes. The user edits that draft as paragraph blocks, can request tone alternatives or argumentative critique per block, and can export the final report as markdown.

The first implementation slice focuses on the reading workspace and the domain model that supports later AI suggestion review, report generation, editing, and export. The recommended architecture is a modular monolith with asynchronous background jobs. In `v1`, persistence is disk-based behind a storage abstraction so the system can later evolve to object storage and caching without rewriting the application core.

## Goals

- Build a web app for writing blogs, articles, letters, reports, and docs from source material.
- Treat uploaded markdown resources as immutable reference material.
- Support collaborative reading between the user and AI expert lenses.
- Make AI suggestions visible, reviewable, and optional.
- Ensure only user-owned notes feed report generation.
- Generate the initial report draft with AI, then hand control to the user in a block editor.
- Export the completed report as markdown.

## Non-Goals For V1

- Multi-user collaboration, shared projects, or permissions.
- Editing uploaded source resources after upload.
- Raw-markdown editing as the primary reading surface.
- Automatic surgical AI patching of an existing report after new notes arrive.
- Premature infrastructure complexity such as distributed microservices, MinIO, or Redis in `v1`.

## Product Scope

### User Workflow

1. Create a project.
2. Upload markdown resources organized in folders and subfolders.
3. Read rendered markdown resources without editing them.
4. Create quote-anchored notes and highlights from the rendered text.
5. Review visible AI expert suggestions tied to source context.
6. Accept, discard, or edit AI suggestions into user-owned notes.
7. Generate an AI-authored report draft from the current user-owned notes.
8. Edit the draft as paragraph blocks.
9. Use per-block AI tools for tone alternatives and critique.
10. Export the final report as markdown.

### Project Model

- A `project` is the top-level workspace for one writing effort.
- Each project contains uploaded markdown `resources`.
- Resources preserve user folder structure and remain read-only after upload.
- New resources can be uploaded later into the same project.
- Notes taken from later uploads become part of the project's note pool.

### Reading Workspace

The reading workspace has three primary surfaces:

- `project/resource tree`: browses folders and markdown files
- `rendered document viewer`: shows the selected resource as rendered markdown
- `notes review panel`: shows user notes and AI suggestions

The rendered document viewer is the authoritative reading surface in `v1`. The user highlights visible rendered content, not raw markdown source.

## Core Product Rules

### Immutable Resources

- Uploaded markdown files are immutable source material.
- The app may derive rendered or indexed representations from a resource, but it must never mutate the original uploaded markdown.

### Quote-Anchored Notes

- `v1` supports quote-only annotations.
- Each annotation is created from a text span in rendered markdown.
- Each annotation stores the quoted text and enough anchor metadata to relocate the note to the source region later.
- File-level or project-level freeform notes are deferred.

### AI Suggestions

- AI-generated suggestions are visible first-class artifacts in the UI.
- Each resource's first analysis run discovers open-ended, document-specific expert lenses with a short name and description.
- Discovered lenses are read-only in `v1`.
- Suggestions are grouped by the discovered lenses for that run.
- Each suggestion is tied back to source context so the user can inspect where it came from.
- In `v1`, AI analysis is explicitly user-triggered from the reading workspace for the current resource.
- The first run for a resource automatically performs lens discovery and then suggestion generation.
- Subsequent lens regeneration is explicit through a separate user action.
- Automatic project-wide suggestion generation is deferred.
- The AI panel shows only the latest analysis run for the current resource.
- User notes and AI suggestions stay separate by default.
- Accepting a suggestion converts it into a user-owned note.
- Accepted suggestions persist in the notes panel as normal user-owned notes even if a later run replaces the AI panel view.
- The system preserves provenance so accepted notes can still be traced back to their AI origin.
- Discarding a suggestion removes it from the active workflow but keeps a reversible record where practical.

### Report Generation

- Report generation reads only user-owned notes.
- User-owned notes include:
  - notes created directly by the user
  - AI suggestions the user explicitly accepted, optionally after editing
- The initial report draft is generated by the AI system.
- Each generated draft is stored as a distinct `report version`.

### Report Staleness

- Users may upload more resources after a report exists.
- Users may read those new resources and add more notes.
- If new notes arrive after draft creation, the existing report is marked `stale`.
- `v1` does not surgically rewrite existing report blocks from new notes.
- The user explicitly creates a new revised draft version from the full current note set when ready.

## Architecture

### Recommended Approach

Use a modular monolith with:

- one frontend application
- one backend application
- one database
- asynchronous background jobs for AI and heavier document processing

This keeps delivery fast for a single-user `v1` while preserving strong internal boundaries and a path to future extraction if needed.

### Why This Approach

- Faster to build and validate than service-oriented decomposition.
- Lower operational complexity for an early product.
- Easier to reason about for a single-user system.
- Still compatible with future evolution of storage, caching, and job processing.

### Deferred Architectural Complexity

The following are explicitly deferred beyond `v1`:

- MinIO or equivalent object storage
- Redis or equivalent cache layer
- service decomposition
- multi-user tenancy and collaboration

## Storage Strategy

### V1

- Use local disk for persistence and temporary files.
- Wrap all storage access behind a storage abstraction.
- Keep uploaded markdown resources, rendered derivatives, and temporary processing artifacts isolated by project.

### Future Evolution

The storage abstraction should make it possible to later move to:

- object storage such as MinIO for persisted resources and exports
- a cache layer such as Redis if scale or performance justifies it

The design should not assume that local disk remains the permanent storage implementation.

## Backend Modules

The modular monolith should be organized around the following bounded areas:

- `projects`
  - create projects
  - list projects
  - project-level metadata
- `resources`
  - upload markdown files
  - preserve folder structure
  - track resource metadata and storage paths
  - render or prepare resources for reading
- `annotations`
  - store quote-anchored user notes and highlights
  - link notes to resource spans
- `analysis_runs`
  - discover document-specific expert lenses
  - enqueue per-resource analysis runs
  - persist discovered lenses and suggestions
  - track lens discovery, generation, and review state
- `reports`
  - generate AI-authored draft versions from user-owned notes
  - store report content and block structure
  - track report staleness
- `exports`
  - serialize a selected report version into markdown for download

## Domain Model

### Project

- id
- title
- created_at
- updated_at

### Resource

- id
- project_id
- logical_path
- original_filename
- storage_location
- content_hash
- upload_status
- created_at

### Annotation

- id
- project_id
- resource_id
- quote_text
- anchor_metadata
- body
- origin_type (`user` or `accepted_ai`)
- provenance_source_id
- created_at
- updated_at

### Analysis Run

- id
- project_id
- resource_id
- lens_discovery_status (`queued`, `running`, `succeeded`, `failed`)
- discovered_lenses (list of `{ name, description }`)
- generation_status (`queued`, `running`, `succeeded`, `completed_with_failures`, `failed`, `cancelled`)
- error_summary
- created_at
- updated_at

### Analysis Run Lens Result

- id
- analysis_run_id
- lens_name
- generation_status (`queued`, `running`, `succeeded`, `failed`, `cancelled`)
- failure_reason
- created_at
- updated_at

### AI Suggestion

- id
- analysis_run_lens_result_id or equivalent
- project_id
- resource_id
- lens_name
- source_context
- suggestion_body
- review_status (`unreviewed`, `accepted`, `discarded`)
- created_at
- updated_at

### Report Version

- id
- project_id
- source_note_snapshot_id or equivalent generation reference
- markdown_body
- block_representation
- status (`pending`, `ready`, `failed`, `stale`)
- created_at

### Export

- id
- report_version_id
- export_format (`md`)
- storage_location
- created_at

## Reading Workspace Behavior

### Resource Navigation

- The resource tree must reflect uploaded folder structure.
- Selecting a file opens it in the rendered document viewer.
- The interface should make it obvious that resources are reference material, not editable documents.

### Highlighting And Annotation

- The user selects text in rendered markdown.
- The system creates a quote-anchored annotation record.
- The note review panel should immediately show the new note.
- The original resource remains unchanged.

### AI Suggestion Review

- Before the first run, the UI shows a single `Run analysis` action and no lens checklist.
- When the first run starts, the UI progresses through `Discovering lenses...` and then `Generating suggestions...`.
- AI suggestion generation runs asynchronously after lens discovery succeeds.
- After discovery succeeds, the UI shows the discovered lenses as a read-only list with names and short descriptions.
- Suggestions appear in the AI panel when ready.
- Suggestions are filterable or groupable by discovered lens.
- The AI panel always reflects only the latest analysis run for the selected resource.
- If some lenses fail during suggestion generation, the UI exposes those failures and offers `Retry failed lenses`.
- `Retry failed lenses` reuses the existing discovered lenses and reruns only failed suggestion generation.
- `Regenerate lenses` creates a fresh run with new lens discovery and replaces the current AI panel view.
- The user can inspect source context before taking action.
- The user can:
  - accept a suggestion as-is
  - accept and edit it into their own note
  - discard it

## Report Generation And Editor

### Initial Draft Generation

- The AI system generates the first draft from the current set of user-owned notes.
- A generation run creates a new report version rather than overwriting prior versions.
- The source for generation is the accepted note set at the time the job starts.

### Editor Model

- After draft generation, the UI shifts into an editor experience.
- The unit of editing is the paragraph block.
- Manual typing is the default editing path and user edits always win.
- AI editing tools are advisory, not auto-applied.

### Per-Block AI Tools

Each paragraph block supports:

- `change tone`
  - generate 5 alternative rewrites
  - use surrounding report context
- `challenge my argument`
  - critique assumptions, evidence gaps, weak reasoning, and unclear claims
  - help the user strengthen the argument

The output of these tools is presented as suggestions for the user to adopt or ignore.

### Export

- The user can download the current report version as markdown.
- Export serializes the report's current state into `.md`.

## Data Flow

### Resource Upload

1. User uploads markdown files through the UI.
2. Backend stores files on disk through the storage abstraction.
3. Backend creates `resource` records.
4. Resource tree updates to reflect newly available files.

### Reading And Notes

1. User opens a resource.
2. Backend returns a rendered or prepared representation for the viewer.
3. User highlights rendered text and creates an annotation.
4. Backend stores the annotation with quote and anchor metadata.

### AI Suggestion Flow

1. User explicitly triggers AI analysis for the current resource from the reading workspace.
2. Backend creates an analysis run and starts lens discovery if this is the first run for that resource or the user explicitly requested lens regeneration.
3. On discovery success, backend persists the discovered lens names and descriptions, then starts per-lens suggestion generation.
4. If discovery fails, the run records that failure and suggestion generation does not start.
5. `GET /resources/{resource_id}/analysis-runs/latest` returns the latest run, including discovered lenses, per-lens generation status, and suggestions.
6. User reviews only the latest run's suggestions in the AI panel.
7. Accepting a suggestion creates or updates a user-owned note and keeps it visible in the notes panel even if later runs replace the AI panel view.
8. `Retry failed lenses` reruns only failed suggestion generation against the existing discovered lenses.
9. `Regenerate lenses` creates a fresh run with new discovery and replaces the active AI panel view for that resource.

### Report Flow

1. User triggers report generation.
2. Backend creates a report generation job.
3. The job reads only user-owned notes.
4. The AI system produces a draft.
5. Backend stores the result as a new report version.
6. Editor opens the new version.

### Stale Report Flow

1. A report version exists.
2. User adds new resources and/or notes.
3. Backend marks existing report versions as `stale` where appropriate.
4. User explicitly triggers a revised draft version.

## Failure Handling

### Upload And Parsing Failures

- If one file fails during upload or parsing, that file is marked failed.
- Other files in the same batch may still succeed.
- The UI should surface which files failed and why where possible.

### AI Suggestion Failures

- If lens discovery fails, the failure is visible in the UI and suggestion generation does not start.
- If one or more discovered lenses fail during suggestion generation, those failures are visible in the UI.
- The UI offers `Retry failed lenses` only for failed suggestion generation, without rediscovering lenses.
- The UI offers an explicit `Regenerate lenses` action when the user wants a fresh discovered lens set.

### Report Generation Failures

- If report generation fails, no partial draft replaces the current report.
- The existing report version remains intact.
- The UI offers an explicit retry button for report generation.

### Reversibility

- Discard-like actions on AI suggestions should be reversible where practical.

## Testing Strategy

The implementation plan should cover tests for:

- project creation
- markdown upload and folder-structure preservation
- rendered resource viewing
- quote-anchored annotation creation
- first-run AI lens discovery
- latest-run AI panel replacement behavior
- retrying failed lenses without rediscovery
- regenerating lenses with a fresh discovered lens set
- AI suggestion persistence and state transitions
- accepting and discarding AI suggestions
- accepted AI notes persisting across later runs
- report generation into a new version
- stale report marking when notes change
- markdown export of a selected report version

## Open Items Deferred Beyond V1

- How best to map newly added notes to existing report blocks for surgical updates
- Whether users need file-level or project-level notes in addition to quote-only notes
- Whether users should eventually edit, pin, or reuse discovered lens sets
- Whether the editor should eventually support richer block types than paragraphs

## Implementation Guidance

The implementation plan should begin with the reading workspace slice but should choose data structures and interfaces that do not block the later addition of:

- persisted AI suggestion review
- AI-authored report generation
- paragraph-block editing
- markdown export

The recommended sequence is:

1. Establish application skeleton and modular boundaries.
2. Implement project creation and markdown upload.
3. Implement resource browsing and rendered reading.
4. Implement quote-anchored user annotations.
5. Implement AI lens discovery, suggestion job flow, and review states.
6. Implement report generation and versioning.
7. Implement block editor affordances and markdown export.

