# Product Development Roadmap

This roadmap breaks down the development lifecycle into logical phases, ensuring that core functionality is validated before moving to complex AI interactions.

## Phase 1: Foundation & Workspace Assembly
**Objective:** Build the core CRUD operations and the research interface. No AI integration yet.
* [ ] **Epic 1: Project Management**
    * Initialize Go backend repository and React frontend.
    * Implement SQLite database schema for Projects and Files.
    * Create API endpoints for creating/listing projects.
* [ ] **Epic 2: Resource Ingestion & Viewing**
    * Implement file upload system (saving to local FS).
    * Build the Frontend Markdown Viewer component.
* [ ] **Epic 3: Manual Note-Taking**
    * Implement text-selection highlighting in the UI.
    * Build the side-panel for users to add and save manual notes tied to specific highlights.

## Phase 2: The Co-Reading AI & Vector Pipeline
**Objective:** Introduce the AI "Lenses" and semantic search capabilities.
* [ ] **Epic 4: RAG Pipeline Setup**
    * Integrate Chroma DB into the Go backend.
    * Create a background worker that chunks and embeds uploaded Markdown files into Chroma upon upload.
* [ ] **Epic 5: AI Orchestration Service - Lens Engine**
    * Implement the `ServiceRouter` and `ITaskEngine` interface in Go.
    * Build the `LensGenerator` engine.
    * Create system prompts for various expert personas (e.g., Financial, Tech, Political).
* [ ] **Epic 6: UI Integration for AI Notes**
    * Update frontend to trigger Lens Analysis.
    * Build the UI for the user to review, accept, or discard AI-generated notes into the "master dump".

## Phase 3: The Synthesis Bridge
**Objective:** Enable the one-click generation of the foundational draft.
* [ ] **Epic 7: Draft Compiler Engine**
    * Build the `DraftCompiler` engine in the Go backend.
    * Design a complex synthesis prompt that ingests the curated master notes and instructions to output a cohesive Markdown document.
* [ ] **Epic 8: Draft Generation UI**
    * Implement the "Create Report" trigger.
    * Parse the LLM Markdown output into discrete JSON paragraph blocks and save to the SQLite database.

## Phase 4: Block-Based Editing & AI Refinement
**Objective:** Shift to the Editor Mode and implement paragraph-level AI tools.
* [ ] **Epic 9: Custom Block Editor**
    * Build the Block-Based Editor UI where each paragraph is an editable unit.
    * Implement real-time saving of block edits to the backend.
* [ ] **Epic 10: Tone & Critique Engines**
    * Build the `ToneEngine` (returning 5 variations) and `CritiqueEngine` (Red Teaming) in Go.
    * Implement frontend context menus on blocks to trigger these engines.
    * Add Server-Sent Events (SSE) or WebSockets to stream AI responses directly into the editor UI for a snappy user experience.

## Phase 5: Scale, Polish & Production
**Objective:** Prepare the application for broader use and deployment.
* [ ] **Epic 11: Production Infrastructure**
    * Migrate SQLite to PostgreSQL.
    * Migrate Local FS to AWS S3 / Object Storage.
    * Containerize the application using Docker.
* [ ] **Epic 12: Advanced Features (Post-MVP)**
    * Custom User-Defined Lenses (allowing users to write their own system prompts for personas).
    * Exporting final drafts to PDF/Word.
