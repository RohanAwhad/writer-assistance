import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AiProvider, ProjectDetail } from "../api/types";
import ProviderSelector from "../components/ProviderSelector";
import { error, ok, stubFetch, type FetchCall, type StubResponse } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

function projectDetail(ai_provider: AiProvider): ProjectDetail {
  return {
    id: 1,
    name: "essays",
    ai_provider,
    resource_count: 2,
    round_count: 1,
    created_at: iso,
    updated_at: iso,
  };
}

async function combobox(): Promise<HTMLSelectElement> {
  return (await screen.findByRole("combobox", { name: "AI provider" })) as HTMLSelectElement;
}

function stubGatedFetch(handler: (call: FetchCall, index: number) => StubResponse): {
  calls: FetchCall[];
  releaseNextPut: () => void;
} {
  const calls: FetchCall[] = [];
  const releases: Array<() => void> = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    let body: unknown = null;
    if (typeof init?.body === "string" && init.body.length > 0) {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    const call: FetchCall = { url, method, body };
    calls.push(call);
    if (method === "PUT") {
      await new Promise<void>((resolve) => {
        releases.push(resolve);
      });
    }
    const response = handler(call, calls.length - 1);
    const status = response.status ?? 200;
    const jsonBody = response.json !== undefined ? JSON.stringify(response.json) : "{}";
    return new Response(jsonBody, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn as unknown as typeof fetch);
  return {
    calls,
    releaseNextPut: () => {
      releases.shift()?.();
    },
  };
}

describe("provider selector (R-071)", () => {
  it("renders the project's provider from the fetched payload (fresh project: deepseek) and offers both providers", async () => {
    stubFetch(() => ok(projectDetail("deepseek")));
    render(<ProviderSelector projectId={1} />);

    const select = await combobox();
    expect(select).toHaveValue("deepseek");
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(2);
    expect(screen.getByRole("option", { name: "DeepSeek" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Anthropic Vertex" })).toBeInTheDocument();
  });

  it("switching issues PUT /projects/{id}/provider and updates the select from the response", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        expect(call.url).toBe("/api/v1/projects/1/provider");
        expect(call.body).toEqual({ provider: "vertex" });
        return ok(projectDetail("vertex"));
      }
      return ok(projectDetail("deepseek"));
    });
    render(<ProviderSelector projectId={1} />);

    const select = await combobox();
    expect(select).toHaveValue("deepseek");
    await user.selectOptions(select, "vertex");
    await waitFor(() => expect(select).toHaveValue("vertex"));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
    expect(screen.getByRole("option", { name: "DeepSeek" })).toBeInTheDocument();
  });

  it("re-mounts with the persisted provider fetched from the project payload (reload keeps the choice)", async () => {
    const user = userEvent.setup();
    let stored: AiProvider = "deepseek";
    const first = stubFetch((call) => {
      if (call.method === "PUT") {
        stored = (call.body as { provider: AiProvider }).provider;
        return ok(projectDetail(stored));
      }
      return ok(projectDetail(stored));
    });
    const firstView = render(<ProviderSelector projectId={1} />);
    const select = await combobox();
    expect(select).toHaveValue("deepseek");
    await user.selectOptions(select, "vertex");
    await waitFor(() => expect(select).toHaveValue("vertex"));
    expect(stored).toBe("vertex");
    firstView.unmount();

    const { calls } = stubFetch(() => ok(projectDetail(stored)));
    render(<ProviderSelector projectId={1} />);
    const reloaded = await combobox();
    expect(reloaded).toHaveValue("vertex");
    expect(calls.map((c) => c.method)).toEqual(["GET"]);
    expect(first.calls.filter((c) => c.method === "PUT")).toHaveLength(1);
  });

  it("keeps the previous provider and surfaces the backend error when the PUT fails", async () => {
    const user = userEvent.setup();
    let failing = true;
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        if (failing) {
          failing = false;
          return error(500, "backend hiccup");
        }
        return ok(projectDetail("vertex"));
      }
      return ok(projectDetail("deepseek"));
    });
    render(<ProviderSelector projectId={1} />);

    const select = await combobox();
    await user.selectOptions(select, "vertex");
    expect(await screen.findByText("backend hiccup")).toBeInTheDocument();
    expect(select).toHaveValue("deepseek");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);

    await user.selectOptions(select, "vertex");
    await waitFor(() => expect(select).toHaveValue("vertex"));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2);
  });

  it("disables the select while a PUT is pending, then re-enables with the response value", async () => {
    const user = userEvent.setup();
    const { calls, releaseNextPut } = stubGatedFetch((call) => {
      if (call.method === "PUT") {
        return ok(projectDetail("vertex"));
      }
      return ok(projectDetail("deepseek"));
    });
    render(<ProviderSelector projectId={1} />);

    const select = await combobox();
    expect(select).toHaveValue("deepseek");
    await user.selectOptions(select, "vertex");
    await waitFor(() => expect(select).toBeDisabled());
    expect(screen.getByText("Saving…")).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);

    releaseNextPut();
    await waitFor(() => expect(select).toBeEnabled());
    await waitFor(() => expect(select).toHaveValue("vertex"));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
  });

  it("shows an inline error with a Retry affordance on payload-load failure and recovers on retry", async () => {
    const user = userEvent.setup();
    let failing = true;
    const { calls } = stubFetch(() => {
      if (failing) {
        failing = false;
        return error(503, "provider load failed");
      }
      return ok(projectDetail("vertex"));
    });
    render(<ProviderSelector projectId={1} />);

    expect(await screen.findByText("provider load failed")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "AI provider" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    const select = await screen.findByRole("combobox", { name: "AI provider" });
    expect(select).toHaveValue("vertex");
    expect(calls.filter((c) => c.method === "GET")).toHaveLength(2);
  });
});
