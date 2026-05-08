SHELL := /bin/bash
.PHONY: dev prod install stop

dev:
	@echo "Starting Writer's Desk (dev)..." && \
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload & \
	cd frontend && npx vite --port 5173 & \
	echo "" && \
	echo "Backend:  http://localhost:8000 (reload on)" && \
	echo "Frontend: http://localhost:5173 (HMR)" && \
	echo "Press Ctrl+C to stop." && \
	trap 'kill $$(jobs -p) 2>/dev/null; exit' INT TERM && \
	wait

prod:
	@echo "Building frontend..." && \
	cd frontend && npx tsc -b && npx vite build && cd .. && \
	echo "Starting Writer's Desk (prod)..." && \
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 & \
	cd frontend && npx vite preview --port 5173 & \
	echo "" && \
	echo "Backend:  http://localhost:8000" && \
	echo "Frontend: http://localhost:5173" && \
	echo "Press Ctrl+C to stop." && \
	trap 'kill $$(jobs -p) 2>/dev/null; exit' INT TERM && \
	wait

install:
	@cd backend && uv sync
	@cd frontend && npm install

stop:
	@echo "Killing uvicorn and vite..."
	@-pkill -f 'uvicorn app.main:app' 2>/dev/null
	@-pkill -f 'vite' 2>/dev/null
	@echo "Done."
