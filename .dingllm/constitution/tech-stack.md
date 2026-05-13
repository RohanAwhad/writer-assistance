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
