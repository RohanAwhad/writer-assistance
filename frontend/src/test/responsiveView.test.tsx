import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  AnnotationOut,
  ProjectDetail,
  ProjectOut,
  RoundDetailOut,
  RoundSummary,
  TreeOut,
} from "../api/types";
import App from "../App";
import WorkspaceScreen from "../screens/WorkspaceScreen";
import { ok, stubFetch, type FetchCall, type StubResponse } from "./fetchMock";
import { installMatchMedia } from "./matchMediaMock";

// INT-009 responsive-view suite (§11.1, R-082..R-085): jsdom has no layout
// engine and vitest runs css:false, so these tests prove JS-observable
// narrow-mode behavior through a mocked matchMedia (SD-34). Overflow-free
// layout itself is the §11.2 steps 24..26 manual leg.

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

const projectDetail: ProjectDetail = {
  id: 1,
  name: "Proj",
  ai_provider: "deepseek",
  resource_count: 1,
  round_count: 1,
  created_at: iso,
  updated_at: iso,
};

const projectOut: ProjectOut = {
  id: 1,
  name: "Proj",
  ai_provider: "deepseek",
  created_at: iso,
  updated_at: iso,
};

const tree: TreeOut = {
  project_id: 1,
  nodes: [{ id: 11, parent_id: null, name: "brief.md", path: "brief.md", kind: "file" }],
};

const emptyTree: TreeOut = { project_id: 1, nodes: [] };

const docText = "The rent cap binds in three districts.\n\nSecond paragraph without marks.";

const note: AnnotationOut = {
  id: 102,
  doc_id: 11,
  kind: "note",
  start_offset: null,
  end_offset: null,
  content: "Compare with the 2019 study before writing.",
  created_at: iso,
  updated_at: iso,
};

const emptyDump = { round_id: 1, dump_id: null, saved: false, entries: [] };

const readingSummary: RoundSummary = {
  id: 1,
  project_id: 1,
  name: "Round 1",
  stage: "reading",
  doc_count: 1,
  created_at: iso,
  dump_id: null,
  report_id: null,
};

const readingDetail: RoundDetailOut = {
  id: 1,
  project_id: 1,
  name: "Round 1",
  stage: "reading",
  created_at: iso,
  updated_at: iso,
  docs: [{ id: 11, path: "brief.md" }],
  dump_id: null,
  report_id: null,
};

const editingSummary: RoundSummary = {
  id: 1,
  project_id: 1,
  name: "Round 1",
  stage: "editing",
  doc_count: 1,
  created_at: iso,
  dump_id: 7,
  report_id: 9,
};

const editingDetail: RoundDetailOut = {
  id: 1,
  project_id: 1,
  name: "Round 1",
  stage: "editing",
  created_at: iso,
  updated_at: iso,
  docs: [{ id: 11, path: "brief.md" }],
  dump_id: 7,
  report_id: 9,
};

type Scenario = "reading" | "editing" | "empty";

function routeHandler(scenario: Scenario): (call: FetchCall) => StubResponse {
  return (call: FetchCall) => {
    switch (call.url) {
      case "/api/v1/projects":
        return ok([projectOut]);
      case "/api/v1/projects/1":
        return ok(projectDetail);
      case "/api/v1/projects/1/provider":
        return ok({ ...projectDetail, ai_provider: (call.body as { provider: string }).provider });
      case "/api/v1/projects/1/tree":
        return ok(scenario === "empty" ? emptyTree : tree);
      case "/api/v1/rounds?project_id=1":
        if (scenario === "empty") return ok([]);
        return ok(scenario === "editing" ? [editingSummary] : [readingSummary]);
      case "/api/v1/rounds/1":
        return ok(scenario === "editing" ? editingDetail : readingDetail);
      case "/api/v1/rounds/1/dump":
        return ok(emptyDump);
      case "/api/v1/rounds/1/expert-runs":
        return ok({ expert_runs: [] });
      case "/api/v1/reports/9":
        return ok({ id: 9, round_id: 1, created_at: iso, blocks: [] });
      case "/api/v1/resources/11":
        return ok({
          id: 11,
          project_id: 1,
          path: "brief.md",
          content: docText,
          imported_at: iso,
        });
      case "/api/v1/resources/11/annotations":
        return ok([note]);
      case "/api/v1/resources/11/lens-proposals":
        return ok([]);
      case "/api/v1/annotations/102":
        return { status: 204, json: null };
      default:
        return { status: 500, json: { detail: `unexpected route ${call.method} ${call.url}` } };
    }
  };
}

function mountWorkspace(
  scenario: Scenario,
  opts?: { onBack?: () => void },
): { calls: FetchCall[] } {
  const { calls } = stubFetch(routeHandler(scenario));
  render(
    <WorkspaceScreen
      projectId={1}
      projectName="Proj"
      onBack={opts?.onBack ?? (() => undefined)}
    />,
  );
  return { calls };
}

async function openNavOverlay(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(await screen.findByRole("button", { name: "Resources & rounds" }));
  await screen.findByTestId("doc-row-brief.md");
}

describe("phone width 390px — narrow navigation overlay and surfaces (R-082)", () => {
  it("renders resources/rounds as an overlay from a content-surface control; selecting a resource opens it as the active doc", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("reading");

    expect(screen.queryByTestId("doc-row-brief.md")).not.toBeInTheDocument();
    expect(screen.queryByTestId("round-row-1")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resources & rounds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Annotate & round" })).toBeInTheDocument();

    await openNavOverlay(user);
    expect(screen.getByRole("dialog", { name: "Resources & rounds" })).toBeInTheDocument();
    expect(screen.getByTestId("round-row-1")).toBeInTheDocument();

    await user.click(screen.getByTestId("doc-row-brief.md"));
    expect(await screen.findByText("The rent cap binds in three districts.")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByTestId("doc-row-brief.md")).not.toBeInTheDocument();
    });
  });

  it("keeps the annotation/round panes behind their own overlay, openable and closable", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("reading");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("doc-row-brief.md"));
    await screen.findByText("The rent cap binds in three districts.");

    expect(screen.queryByText("Annotations")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Annotate & round" }));
    expect(await screen.findByRole("dialog", { name: "Annotate & round" })).toBeInTheDocument();
    expect(screen.getByText("Annotations")).toBeInTheDocument();
    expect(screen.getByText("Compare with the 2019 study before writing.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close Annotate & round" }));
    expect(screen.queryByText("Annotations")).not.toBeInTheDocument();
  });

  it("selecting a round from the overlay exposes the round-stage mode controls on the content surface", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("reading");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("round-row-1"));
    await waitFor(() => {
      expect(screen.queryByTestId("round-row-1")).not.toBeInTheDocument();
    });

    expect(await screen.findByTestId("round-stage-name")).toHaveTextContent("Round 1");
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("reading");
    expect(screen.getByRole("button", { name: "Read & annotate" })).toBeInTheDocument();
    const curateButton = screen.getByRole("button", { name: "Curate dump" });
    expect(curateButton).toBeEnabled();
    const reportButton = screen.getByRole("button", { name: "Report" });
    expect(reportButton).toBeDisabled();
  });

  it("header back control returns to the projects list", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    stubFetch(routeHandler("reading"));
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByRole("button", { name: "Resources & rounds" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Projects" }));
    expect(await screen.findByRole("heading", { name: "Writer Assistant" })).toBeInTheDocument();
  });

  it("opens the round-stage surfaces (curate) and the import, new-round and delete dialogs at this width", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("reading");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("round-row-1"));
    const curateButton = await screen.findByRole("button", { name: "Curate dump" });
    await waitFor(() => expect(curateButton).toBeEnabled());

    await user.click(curateButton);
    expect(
      await screen.findByText("Curate the notes dump · Round 1"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Read & annotate" }));

    await openNavOverlay(user);
    await user.click(screen.getByRole("button", { name: "New round" }));
    expect(await screen.findByRole("heading", { name: "New reading round" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create round" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("heading", { name: "New reading round" })).not.toBeInTheDocument();
  });

  it("opens the delete-report dialog through the report mode at this width", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("editing");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("round-row-1"));
    await user.click(await screen.findByRole("button", { name: "Report" }));

    expect(await screen.findByText("Report editor")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete report" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Delete report?" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Delete report" })).toBeInTheDocument();
  });

  it("opens the import dialog on an empty project at this width", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("empty");

    await user.click(await screen.findByRole("button", { name: "Resources & rounds" }));
    await user.click(await screen.findByRole("button", { name: "Import" }));

    expect(await screen.findByRole("heading", { name: "Import Markdown files" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose files…" })).toBeInTheDocument();
    const importButton = screen.getByRole("button", { name: "Import" });
    expect(importButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
  });
});

describe("tablet width 820px — reachable modes/actions (R-083)", () => {
  it("reaches round modes and their actions through visible controls at tablet width", async () => {
    const user = userEvent.setup();
    installMatchMedia("tablet");
    mountWorkspace("reading");

    expect(screen.getByRole("button", { name: "Resources & rounds" })).toBeInTheDocument();
    expect(screen.queryByTestId("doc-row-brief.md")).not.toBeInTheDocument();

    await openNavOverlay(user);
    await user.click(screen.getByTestId("doc-row-brief.md"));
    await screen.findByText("The rent cap binds in three districts.");
    await openNavOverlay(user);
    await user.click(screen.getByTestId("round-row-1"));

    const curateButton = await screen.findByRole("button", { name: "Curate dump" });
    await waitFor(() => expect(curateButton).toBeEnabled());
    await user.click(curateButton);
    expect(await screen.findByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save dump" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate report" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Read & annotate" }));

    await user.click(screen.getByRole("button", { name: "Annotate & round" }));
    const proposeButton = await screen.findByRole("button", {
      name: "Propose lenses for this doc",
    });
    expect(proposeButton).toBeEnabled();
    await user.click(proposeButton);
    expect(screen.getByRole("button", { name: /Run experts \(0 selected\)/ })).toBeDisabled();
  });
});

describe("desktop width 1280px — unchanged three-pane arrangement (desktop regression guard, SD-31)", () => {
  it("renders the resources/rounds sidebar and the annotation/round pane side-by-side with the content", async () => {
    const user = userEvent.setup();
    installMatchMedia("desktop");
    mountWorkspace("reading");

    expect(screen.queryByTestId("narrow-surface-controls")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resources & rounds" })).not.toBeInTheDocument();

    const docRow = await screen.findByTestId("doc-row-brief.md");
    const roundRow = screen.getByTestId("round-row-1");
    expect(docRow).toBeInTheDocument();
    expect(roundRow).toBeInTheDocument();

    await user.click(docRow);
    expect(await screen.findByText("Annotations")).toBeInTheDocument();
    expect(screen.getByText("Compare with the 2019 study before writing.")).toBeInTheDocument();

    await user.click(roundRow);
    expect(await screen.findByText("Lenses & experts · Round 1")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Propose lenses for this doc" }),
    ).toBeInTheDocument();
  });
});

describe("width-change preservation across phone → tablet → desktop (R-084)", () => {
  it("flips the arrangement without reload, without losing doc/round/mode and without writes", async () => {
    const user = userEvent.setup();
    const install = installMatchMedia("phone");
    const onBack = vi.fn();
    const { calls } = mountWorkspace("reading", { onBack });

    await openNavOverlay(user);
    await user.click(screen.getByTestId("doc-row-brief.md"));
    await screen.findByText("The rent cap binds in three districts.");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("round-row-1"));
    await screen.findByTestId("round-stage-name");

    const curateButton = await screen.findByRole("button", { name: "Curate dump" });
    await waitFor(() => expect(curateButton).toBeEnabled());
    await user.click(curateButton);
    expect(await screen.findByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);

    act(() => install.setWidth("tablet"));
    expect(screen.getByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(screen.getByTestId("round-stage-name")).toHaveTextContent("Round 1");
    expect(screen.getByRole("button", { name: "Resources & rounds" })).toBeInTheDocument();
    expect(screen.queryByTestId("doc-row-brief.md")).not.toBeInTheDocument();

    act(() => install.setWidth("desktop"));
    expect(screen.getByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(screen.getByTestId("round-stage-name")).toHaveTextContent("Round 1");
    expect(screen.queryByRole("button", { name: "Resources & rounds" })).not.toBeInTheDocument();
    expect(screen.getByTestId("doc-row-brief.md")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => install.setWidth("phone"));
    expect(screen.getByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(screen.getByTestId("round-stage-name")).toHaveTextContent("Round 1");
    expect(screen.getByRole("button", { name: "Resources & rounds" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Read & annotate" }));
    expect(screen.getByText("The rent cap binds in three districts.")).toBeInTheDocument();
    const resourceGets = calls.filter(
      (c) => c.method === "GET" && c.url === "/api/v1/resources/11",
    );
    expect(resourceGets).toHaveLength(1);

    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);
    expect(onBack).not.toHaveBeenCalled();
  });
});

describe("touch reachability at phone width (R-085)", () => {
  it("annotation delete control is present and operable by a plain click with no hover precondition", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    const { calls } = mountWorkspace("reading");

    await openNavOverlay(user);
    await user.click(screen.getByTestId("doc-row-brief.md"));
    await screen.findByText("The rent cap binds in three districts.");

    await user.click(screen.getByRole("button", { name: "Annotate & round" }));
    const deleteButton = await screen.findByRole("button", { name: "Delete annotation" });
    expect(deleteButton).toBeInTheDocument();
    expect(screen.getByText("Compare with the 2019 study before writing.")).toBeInTheDocument();

    await user.click(deleteButton);
    await waitFor(() => {
      expect(calls.some((c) => c.method === "DELETE" && c.url === "/api/v1/annotations/102")).toBe(
        true,
      );
    });
    await waitFor(() => {
      expect(screen.queryByText("Compare with the 2019 study before writing.")).not.toBeInTheDocument();
    });
  });

  it("dialog footer actions are reachable as rendered buttons at phone width", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    mountWorkspace("reading");

    await openNavOverlay(user);
    await user.click(screen.getByRole("button", { name: "New round" }));
    await screen.findByRole("heading", { name: "New reading round" });
    const cancel = screen.getByRole("button", { name: "Cancel" });
    const create = screen.getByRole("button", { name: "Create round" });
    expect(cancel).toBeEnabled();
    expect(create).toBeEnabled();
    await user.click(cancel);
    expect(screen.queryByRole("heading", { name: "New reading round" })).not.toBeInTheDocument();
  });
});

describe("provider selector at phone width (R-082)", () => {
  it("renders and operates the provider <select> at a mocked phone width", async () => {
    const user = userEvent.setup();
    installMatchMedia("phone");
    const { calls } = mountWorkspace("empty");

    const select = (await screen.findByRole("combobox", {
      name: "AI provider",
    })) as HTMLSelectElement;
    expect(select).toHaveValue("deepseek");
    await user.selectOptions(select, "vertex");
    await waitFor(() => expect(select).toHaveValue("vertex"));
    const puts = calls.filter((c) => c.method === "PUT" && c.url === "/api/v1/projects/1/provider");
    expect(puts).toHaveLength(1);
  });
});
