import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ProjectOut } from "../api/types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/fields";
import { EmptyHint, InlineError } from "../components/ui/feedback";
import { Separator } from "../components/ui/misc";

interface ProjectsScreenProps {
  onOpenProject: (projectId: number, projectName: string) => void;
}

export default function ProjectsScreen({ onOpenProject }: ProjectsScreenProps) {
  const [projects, setProjects] = useState<ProjectOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ProjectOut | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setProjects(await api.listProjects());
    } catch (err) {
      setProjects(null);
      setError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleCreate = async (): Promise<void> => {
    setCreateError(null);
    setCreating(true);
    try {
      const created = await api.createProject(createName.trim());
      setCreateOpen(false);
      setCreateName("");
      onOpenProject(created.id, created.name);
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (deleteTarget === null) return;
    setDeleteError(null);
    setDeleting(true);
    try {
      await api.deleteProject(deleteTarget.id);
      setDeleteTarget(null);
      await refresh();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Writer Assistant</h1>
          <p className="text-sm text-muted-foreground">Projects — each holds a read-only Markdown tree you read and annotate.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New project</Button>
      </div>
      <Separator className="my-6" />
      {error !== null && <InlineError message={error} />}
      {projects === null && error === null && <EmptyHint>Loading projects…</EmptyHint>}
      {projects !== null && projects.length === 0 && (
        <EmptyHint>No projects yet. Create one, then import a local Markdown tree inside it.</EmptyHint>
      )}
      <div className="mt-4 flex flex-col gap-3">
        {projects?.map((project) => (
          <Card key={project.id}>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <button type="button" className="text-left" onClick={() => onOpenProject(project.id, project.name)}>
                <CardTitle className="hover:underline">{project.name}</CardTitle>
                <CardDescription>project #{project.id}</CardDescription>
              </button>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => onOpenProject(project.id, project.name)}>
                  Open
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(project)}>
                  Delete
                </Button>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>
              Create the project; resources are imported in the workspace by pointing at a local Markdown tree.
            </DialogDescription>
          </DialogHeader>
          {createError !== null && <InlineError message={createError} />}
          <Input
            aria-label="Project name"
            placeholder="Project name"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCreate();
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button disabled={createName.trim().length === 0 || creating} onClick={() => void handleCreate()}>
              {creating ? "Creating…" : "Create and open"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription>
              This permanently deletes project <Badge variant="secondary">{deleteTarget?.name}</Badge> — its
              imported resources, annotations, rounds, dumps and reports. Files on disk are untouched.
            </DialogDescription>
          </DialogHeader>
          {deleteError !== null && <InlineError message={deleteError} />}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={deleting} onClick={() => void handleDelete()}>
              {deleting ? "Deleting…" : "Delete project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
