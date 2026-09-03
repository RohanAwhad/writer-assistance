import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  AnnotationOut,
  DumpOut,
  ExpertRunOut,
  ResourceOut,
  RoundDetailOut,
  RoundSummary,
  TreeOut,
} from "../api/types";
import WorkspaceScreen from "../screens/WorkspaceScreen";
import { error, ok, stubFetch, type FetchCall } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

const tree: TreeOut = {
  project_id: 1,
  nodes: [{ id: 11, parent_id: null, name: "brief.md", path: "brief.md", kind: "file" }],
};

const resource: ResourceOut = {
  id: 11,
  project_id: 1,
  path: "brief.md",
  content: "The rent cap binds in three districts.\n\nSecond paragraph without marks.",
  imported_at: iso,
};

const highlight: AnnotationOut = {
  id: 101,
  doc_id: 11,
  kind: "highlight",
  start_offset: 4,
  end_offset: 12,
  content: null,
  created_at: iso,
  updated_at: iso,
};

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

const runFixture: ExpertRunOut = {
  id: 501,
  round_id: 1,
  doc_id: 11,
  doc_path: "brief.md",
  lens_proposal_id: 21,
  lens_rationale: "market briefings read for claims",
  lens_title: "Financial lens",
  notes: [
    {
      id: 301,
      expert_run_id: 501,
      content: "The brief misses the rent-cap districts.",
      edited_content: null,
      review_state: "pending",
      merged: false,
      position: 0,
    },
  ],
};

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
  id: 2,
  project_id: 1,
  name: "Round 2",
  stage: "editing",
  doc_count: 1,
  created_at: iso,
  dump_id: 7,
  report_id: 9,
};

const editingDetail: RoundDetailOut = {
  id: 2,
  project_id: 1,
  name: "Round 2",
  stage: "editing",
  created_at: iso,
  updated_at: iso,
  docs: [{ id: 11, path: "brief.md" }],
  dump_id: 7,
  report_id: 9,
};

interface RouteData {
  annotations: AnnotationOut[];
  expertRuns: ExpertRunOut[];
  rounds: RoundSummary[];
}

function mountWorkspace(
  data: RouteData,
  opts?: { failFirstExpertRuns?: boolean },
): { calls: FetchCall[]; unmount: () => void } {
  const failFirstExpertRuns = opts?.failFirstExpertRuns ?? false;
  const { calls } = stubFetch((call) => {
    switch (call.url) {
      case "/api/v1/projects/1/tree":
        return ok(tree);
      case "/api/v1/rounds?project_id=1":
        return ok(data.rounds);
      case "/api/v1/rounds/1":
        return ok(readingDetail);
      case "/api/v1/rounds/2":
        return ok(editingDetail);
      case "/api/v1/rounds/1/expert-runs":
        if (
          failFirstExpertRuns &&
          calls.filter((c) => c.method === "GET" && c.url === "/api/v1/rounds/1/expert-runs").length === 1
        ) {
          return error(500, "backend hiccup");
        }
        return ok({ expert_runs: data.expertRuns });
      case "/api/v1/rounds/2/expert-runs":
        return ok({ expert_runs: [] });
      case "/api/v1/resources/11":
        return ok(resource);
      case "/api/v1/resources/11/annotations":
        return ok(data.annotations);
      case "/api/v1/resources/11/lens-proposals":
        return ok([]);
      case "/api/v1/expert-notes/301":
        return ok({ ...runFixture.notes[0]!, review_state: "accepted" });
      default:
        return error(500, `unexpected route ${call.method} ${call.url}`);
    }
  });
  const view = render(<WorkspaceScreen projectId={1} projectName="Proj" onBack={() => undefined} />);
  return { calls, unmount: view.unmount };
}

async function openDocAndRound(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(await screen.findByTestId("doc-row-brief.md"));
  await screen.findByText("Compare with the 2019 study before writing.");
  await user.click(await screen.findByTestId("round-row-1"));
  await screen.findByText(/Lenses & experts/);
}

describe("reload hydration (UC-02/UC-04)", () => {
  it("seeds annotations from the backend when a doc opens, re-rendering highlights and notes", async () => {
    const user = userEvent.setup();
    const { calls, unmount } = mountWorkspace({
      annotations: [highlight, note],
      expertRuns: [],
      rounds: [readingSummary],
    });
    const docRow = await screen.findByTestId("doc-row-brief.md");
    await user.click(docRow);

    expect(await screen.findByText("Compare with the 2019 study before writing.")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.querySelector(".doc-mark")?.textContent).toBe("rent cap");
    });
    expect(screen.getAllByText("anchored")).toHaveLength(1);
    expect(calls.some((c) => c.url === "/api/v1/resources/11/annotations")).toBe(true);
    unmount();
  });

  it("restores expert runs for a reading round after remount and makes review actions reachable", async () => {
    const user = userEvent.setup();
    const data = { annotations: [note], expertRuns: [runFixture], rounds: [readingSummary] };
    const first = mountWorkspace(data);
    await openDocAndRound(user);

    expect(await screen.findByRole("button", { name: "Keep" })).toBeInTheDocument();
    expect(screen.getByText("The brief misses the rent-cap districts.")).toBeInTheDocument();
    expect(screen.getByText("Financial lens")).toBeInTheDocument();
    expect(
      first.calls.some((c) => c.method === "GET" && c.url === "/api/v1/rounds/1/expert-runs"),
    ).toBe(true);
    first.unmount();

    const second = mountWorkspace(data);
    await openDocAndRound(user);
    expect(await screen.findByRole("button", { name: "Keep" })).toBeInTheDocument();
    expect(screen.getByText("The brief misses the rent-cap districts.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Keep" }));
    await screen.findByText(/All notes reviewed/);
    await waitFor(() => {
      expect(
        second.calls.some((c) => c.method === "PATCH" && c.url.includes("/expert-notes/301")),
      ).toBe(true);
    });
    second.unmount();
  });

  it("tolerates empty annotation and expert-run lists without errors", async () => {
    const user = userEvent.setup();
    const { calls, unmount } = mountWorkspace({
      annotations: [],
      expertRuns: [],
      rounds: [readingSummary],
    });
    await user.click(await screen.findByTestId("doc-row-brief.md"));
    expect(await screen.findByText(/No annotations on this doc yet/)).toBeInTheDocument();

    await user.click(await screen.findByTestId("round-row-1"));
    await screen.findByText(/Lenses & experts/);
    await waitFor(() => {
      expect(calls.some((c) => c.url === "/api/v1/rounds/1/expert-runs")).toBe(true);
    });
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
    expect(screen.queryByText(/failed to load/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Round failed to load/)).not.toBeInTheDocument();
    unmount();
  });

  it("does not fetch or show runs of an editing round as actionable", async () => {
    const user = userEvent.setup();
    const { calls, unmount } = mountWorkspace({
      annotations: [note],
      expertRuns: [runFixture],
      rounds: [editingSummary],
    });
    await user.click(await screen.findByTestId("doc-row-brief.md"));
    await screen.findByText("Compare with the 2019 study before writing.");
    await user.click(await screen.findByTestId("round-row-2"));
    expect(await screen.findByText(/expert runs and curation are closed/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
    expect(calls.some((c) => c.url === "/api/v1/rounds/2/expert-runs")).toBe(false);
    unmount();
  });

  it("shows a Retry affordance after expert-run hydration fails and refetches on demand", async () => {
    const user = userEvent.setup();
    const data = { annotations: [note], expertRuns: [runFixture], rounds: [readingSummary] };
    const { calls, unmount } = mountWorkspace(data, { failFirstExpertRuns: true });
    await openDocAndRound(user);

    expect(await screen.findByText("backend hiccup")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
    expect(
      calls.filter((c) => c.method === "GET" && c.url === "/api/v1/rounds/1/expert-runs"),
    ).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Keep" })).toBeInTheDocument();
    expect(screen.getByText("The brief misses the rent-cap districts.")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        calls.filter((c) => c.method === "GET" && c.url === "/api/v1/rounds/1/expert-runs"),
      ).toHaveLength(2);
    });
    unmount();
  });
});

describe("curate-entry annotation prefetch", () => {
  const treeThree: TreeOut = {
    project_id: 1,
    nodes: [
      { id: 11, parent_id: null, name: "brief.md", path: "brief.md", kind: "file" },
      { id: 12, parent_id: null, name: "notes.md", path: "notes.md", kind: "file" },
      { id: 13, parent_id: null, name: "final.md", path: "final.md", kind: "file" },
    ],
  };

  const resourceTwo: ResourceOut = {
    id: 12,
    project_id: 1,
    path: "notes.md",
    content: "Draft notes for the report.",
    imported_at: iso,
  };

  const resourceThree: ResourceOut = {
    id: 13,
    project_id: 1,
    path: "final.md",
    content: "Final draft under review.",
    imported_at: iso,
  };

  const noteTwo: AnnotationOut = {
    id: 103,
    doc_id: 13,
    kind: "note",
    start_offset: null,
    end_offset: null,
    content: "Compare with the 2019 study before writing.",
    created_at: iso,
    updated_at: iso,
  };

  const emptyDump: DumpOut = { round_id: 1, dump_id: null, saved: false, entries: [] };

  function curateRound(docs: RoundDetailOut["docs"]): RoundDetailOut {
    return { ...readingDetail, docs };
  }

  function curateSummary(docCount: number): RoundSummary {
    return { ...readingSummary, doc_count: docCount };
  }

  it("prefetches annotations for the round's unopened docs on curate entry and seeds the pools", async () => {
    const user = userEvent.setup();
    const roundDetail = curateRound([
      { id: 11, path: "brief.md" },
      { id: 12, path: "notes.md" },
      { id: 13, path: "final.md" },
    ]);
    const { calls } = stubFetch((call) => {
      switch (call.url) {
        case "/api/v1/projects/1/tree":
          return ok(treeThree);
        case "/api/v1/rounds?project_id=1":
          return ok([curateSummary(3)]);
        case "/api/v1/rounds/1":
          return ok(roundDetail);
        case "/api/v1/rounds/1/dump":
          return ok(emptyDump);
        case "/api/v1/resources/11":
          return ok(resource);
        case "/api/v1/resources/11/annotations":
          return ok([highlight]);
        case "/api/v1/resources/12":
          return ok(resourceTwo);
        case "/api/v1/resources/12/annotations":
          return ok([]);
        case "/api/v1/resources/13":
          return ok(resourceThree);
        case "/api/v1/resources/13/annotations":
          return ok([noteTwo]);
        default:
          return error(500, `unexpected route ${call.method} ${call.url}`);
      }
    });
    render(<WorkspaceScreen projectId={1} projectName="Proj" onBack={() => undefined} />);

    await user.click(await screen.findByTestId("round-row-1"));
    const curateButton = await screen.findByRole("button", { name: "Curate dump" });
    await waitFor(() => expect(curateButton).toBeEnabled());
    await user.click(curateButton);

    expect(await screen.findByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(await screen.findByText("rent cap")).toBeInTheDocument();
    expect(await screen.findByText("Compare with the 2019 study before writing.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Highlights to dump" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Your notes to dump" })).toBeInTheDocument();

    await waitFor(() => {
      const getCount = (url: string): number =>
        calls.filter((c) => c.method === "GET" && c.url === url).length;
      expect(getCount("/api/v1/resources/11")).toBe(1);
      expect(getCount("/api/v1/resources/11/annotations")).toBe(1);
      expect(getCount("/api/v1/resources/12")).toBe(1);
      expect(getCount("/api/v1/resources/12/annotations")).toBe(1);
      expect(getCount("/api/v1/resources/13")).toBe(1);
      expect(getCount("/api/v1/resources/13/annotations")).toBe(1);
    });
  });

  it("does not duplicate annotation fetches for docs already opened when entering curate", async () => {
    const user = userEvent.setup();
    const roundDetail = curateRound([
      { id: 11, path: "brief.md" },
      { id: 12, path: "notes.md" },
    ]);
    const { calls } = stubFetch((call) => {
      switch (call.url) {
        case "/api/v1/projects/1/tree":
          return ok({ project_id: 1, nodes: treeThree.nodes.slice(0, 2) });
        case "/api/v1/rounds?project_id=1":
          return ok([curateSummary(2)]);
        case "/api/v1/rounds/1":
          return ok(roundDetail);
        case "/api/v1/rounds/1/dump":
          return ok(emptyDump);
        case "/api/v1/rounds/1/expert-runs":
          return ok({ expert_runs: [] });
        case "/api/v1/resources/11":
          return ok(resource);
        case "/api/v1/resources/11/annotations":
          return ok([note]);
        case "/api/v1/resources/11/lens-proposals":
          return ok([]);
        case "/api/v1/resources/12":
          return ok(resourceTwo);
        case "/api/v1/resources/12/annotations":
          return ok([]);
        default:
          return error(500, `unexpected route ${call.method} ${call.url}`);
      }
    });
    render(<WorkspaceScreen projectId={1} projectName="Proj" onBack={() => undefined} />);

    await user.click(await screen.findByTestId("doc-row-brief.md"));
    await screen.findByText("Compare with the 2019 study before writing.");

    await user.click(await screen.findByTestId("round-row-1"));
    const curateButton = await screen.findByRole("button", { name: "Curate dump" });
    await waitFor(() => expect(curateButton).toBeEnabled());
    await user.click(curateButton);

    expect(await screen.findByText("Curate the notes dump · Round 1")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Add Your notes to dump" })).toBeInTheDocument();

    const getCount = (url: string): number =>
      calls.filter((c) => c.method === "GET" && c.url === url).length;
    await waitFor(() => expect(getCount("/api/v1/resources/12/annotations")).toBe(1));
    expect(getCount("/api/v1/resources/11")).toBe(1);
    expect(getCount("/api/v1/resources/11/annotations")).toBe(1);
    expect(getCount("/api/v1/resources/12")).toBe(1);
  });
});
