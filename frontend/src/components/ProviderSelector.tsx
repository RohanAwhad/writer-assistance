import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AiProvider } from "../api/types";
import { Button } from "./ui/button";
import { Busy, InlineError } from "./ui/feedback";

interface ProviderSelectorProps {
  projectId: number;
}

const PROVIDER_OPTIONS: AiProvider[] = ["deepseek", "vertex"];

const PROVIDER_LABELS: Record<AiProvider, string> = {
  deepseek: "DeepSeek",
  vertex: "Anthropic Vertex",
};

export default function ProviderSelector({ projectId }: ProviderSelectorProps) {
  const [provider, setProvider] = useState<AiProvider | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const unmountedRef = useRef(false);

  useEffect(() => {
    unmountedRef.current = false;
    return () => {
      unmountedRef.current = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setProvider(null);
    setLoadError(null);
    api
      .getProject(projectId)
      .then((project) => {
        if (!cancelled) setProvider(project.ai_provider);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof ApiError ? err.detail : (err as Error).message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, reloadKey]);

  const handleChange = async (next: AiProvider): Promise<void> => {
    setSaveError(null);
    setSaving(true);
    try {
      const updated = await api.updateProjectProvider(projectId, next);
      if (unmountedRef.current) return;
      setProvider(updated.ai_provider);
    } catch (err) {
      if (unmountedRef.current) return;
      setSaveError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      if (!unmountedRef.current) setSaving(false);
    }
  };

  return (
    <>
      {loadError !== null ? (
        <div className="flex flex-wrap items-center gap-2">
          <InlineError message={loadError} />
          <Button size="sm" variant="outline" onClick={() => setReloadKey((prev) => prev + 1)}>
            Retry
          </Button>
        </div>
      ) : provider === null ? (
        <Busy>Loading provider…</Busy>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">AI provider</span>
          <select
            aria-label="AI provider"
            title="Live AI provider used for this project's calls"
            className="h-7 rounded-md border border-input bg-transparent px-2 text-xs"
            value={provider}
            disabled={saving}
            onChange={(e) => void handleChange(e.target.value as AiProvider)}
          >
            {PROVIDER_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {PROVIDER_LABELS[option]}
              </option>
            ))}
          </select>
          {saving && <Busy>Saving…</Busy>}
          {saveError !== null && <InlineError message={saveError} />}
        </div>
      )}
    </>
  );
}
