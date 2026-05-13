# System Architecture & Technology Stack

This document outlines the foundational technologies chosen for the AI-augmented writing web application. The stack is optimized for high concurrency (essential for orchestrating multiple LLM calls), rapid prototyping, and clear separation of concerns.

## 1. Frontend Layer (Client Application)
* **Framework:** React.js (or Vue.js) deployed as a Single Page Application (SPA).
* **Core UI Components:**
    * **Markdown Renderer:** A robust library (e.g., `react-markdown`) to display read-only resource files cleanly.
    * **Block-Based Editor:** A custom implementation (potentially leveraging frameworks like ProseMirror, Slate.js, or BlockNote) that treats paragraphs as discrete JSON/data blocks rather than a single rich-text blob.
* **State Management:** Redux or Zustand for handling complex transitions between "Research Mode" and "Editor Mode", and managing the curated note state.

## 2. Backend Layer (Application Server)
* **Language:** Golang (Go).
    * *Rationale:* Go's lightweight goroutines are perfectly suited for I/O-bound tasks, such as firing off parallel requests to external LLM providers (e.g., generating 5 tone variations simultaneously) without blocking threads. Its strict static typing ensures reliable Data Transfer Objects (DTOs).
* **API Framework:** Standard `net/http` or a lightweight router like `chi` or `Gin` for building the REST API.
* **Architecture Pattern:** Service-Oriented Architecture, specifically using the **Strategy Pattern** for the AI Orchestration Service (routing tasks via an `ITaskEngine` interface).

## 3. Data Storage Layer
To maintain modularity, the data layer is divided into three distinct stores based on data shape and access patterns:
* **Relational Database (Metadata & State):** SQLite (Phase 1) transitioning to PostgreSQL (Phase 3+).
    * *Usage:* Stores User profiles, Project structures, manual notes, curated AI notes, draft block sequences, and standard metadata.
* **Object Storage (Immutable Resources):** Local File System (Phase 1) transitioning to AWS S3 / Cloudflare R2 (Production).
    * *Usage:* Stores the raw, read-only `.md` resource files uploaded by the user.
* **Vector Database (AI Knowledge Base):** Chroma DB.
    * *Usage:* Stores text embeddings of the resource files and notes. Essential for the Retrieval-Augmented Generation (RAG) pipeline, allowing the AI to query context semantically.

## 4. AI Orchestration Service
* **LLM Providers:** OpenAI API (GPT-4o) and/or Anthropic API (Claude 3.5 Sonnet). Abstracted behind an `LLMAdapter` to prevent vendor lock-in.
* **Prompt Management:** System prompts stored externally (YAML/DB) and injected dynamically by a Prompt Manager component.

### Dependency Policy: Minimal External Dependencies
* **No vendor SDKs.** Do not use OpenAI SDK, Anthropic SDK, Chroma SDK, or any provider-specific client library.
* **Raw HTTP only.** All external service communication (LLM providers, Chroma, S3) goes through Go's standard `net/http` with a shared `http.Client`.
* *Rationale:* SDKs add transitive dependencies, version churn, and hide the actual HTTP contract. Raw HTTP keeps the dependency tree shallow, makes the VCR fixture pattern trivial (just record/replay HTTP), and ensures we fully understand what goes over the wire.
* **Allowed external deps:** Router library (`chi`/`Gin`), SQLite driver, standard tooling. Keep `go.mod` lean.

## 5. Testing Strategy

### Philosophy
No mocks. Every test exercises real code paths. External services (LLM providers, Chroma DB) are handled via **recorded HTTP fixtures** (the VCR/cassette pattern), not mocks or live calls.

### VCR / Recorded Fixture Pattern
All components that make HTTP calls (`LLMAdapter`, `RAGEngine`) accept an injected `http.Client`. In tests, a custom `http.RoundTripper` replays saved HTTP responses from disk instead of hitting the network.

* **Recording:** Run a one-time recording pass against real APIs (LLM providers, Chroma) to capture actual HTTP responses. Store them as JSON files under `testdata/fixtures/`.
* **Replaying:** Tests inject the fixture-serving `http.Client`. The full code path executes for real—routing, prompt assembly, request building, response parsing—only the network transport is swapped.
* **Re-recording:** When prompts, request shapes, or API versions change, re-record fixtures via `go test -run TestRecord -tags record` or a helper script.

### What This Gives Us
* **Deterministic:** Same response every time, no flaky tests from non-deterministic LLM output.
* **Fast:** No network calls, no API keys needed in CI.
* **Real data shapes:** Catches serialization/deserialization bugs that mocks would hide.
* **No mocking:** All application code runs for real. Only the HTTP transport layer is swapped.
* **No Docker in CI:** Even Chroma interactions use recorded fixtures. Docker is only needed during the one-time recording step.

### Test Structure
* **Integration tests (one per engine):** Full request flow through `ServiceRouter` -> engine -> `PromptManager` -> `RAGEngine` -> `LLMAdapter` -> fixture response. Validates the entire chain produces a valid `TaskResponse`.
* **PromptManager unit tests:** Pure logic, no external calls. Tests template loading from real YAML files and variable injection.
* **Router tests:** Unknown `task_type` returns error. Known types route to correct engine.
* **Assertions on structure, not content:** Since LLM output is non-deterministic, tests assert on response shape (fields present, status ok, non-empty, correct types) rather than exact text.

### Test Data Layout
```
testdata/
  fixtures/
    lens_openai_response.json
    draft_openai_response.json
    tone_openai_response.json
    critique_openai_response.json
    chroma_embed_response.json
    chroma_query_response.json
  resources/
    sample_article.md          # small .md file for RAG ingestion tests
```
