import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TreeOut } from "../api/types";
import WorkspaceScreen from "../screens/WorkspaceScreen";
import { created, error, ok, stubFetch, type FetchCall } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const emptyTree: TreeOut = { project_id: 1, nodes: [] };

const importedTree: TreeOut = {
  project_id: 1,
  nodes: [
    { id: 11, parent_id: null, name: "a.md", path: "a.md", kind: "file" },
    { id: 12, parent_id: null, name: "b.markdown", path: "b.markdown", kind: "file" },
  ],
};

function mdFile(name: string): File {
  return new File([`# ${name}`], name, { type: "text/markdown" });
}

function treeGetCount(calls: FetchCall[]): number {
  return calls.filter((c) => c.method === "GET" && c.url === "/api/v1/projects/1/tree").length;
}

interface MountOptions {
  tree?: TreeOut;
  importStatus?: "created" | "pending" | "conflict" | "rejected";
  conflictDetail?: string;
  rejectedDetail?: string;
}

function mountEmptyWorkspace(opts: MountOptions = {}): { calls: FetchCall[]; unmount: () => void } {
  let currentTree: TreeOut = opts.tree ?? emptyTree;
  const { calls } = stubFetch((call) => {
    if (call.method === "POST" && call.url.endsWith("/import")) {
      switch (opts.importStatus ?? "created") {
        case "pending":
          return new Promise(() => undefined);
        case "conflict":
          return error(409, opts.conflictDetail ?? "project already has resources");
        case "rejected":
          return error(400, opts.rejectedDetail ?? "a.txt is not a Markdown file");
        default:
          currentTree = importedTree;
          return created({ project_id: 1, imported_files: 2 });
      }
    }
    switch (call.url) {
      case "/api/v1/projects/1/tree":
        return ok(currentTree);
      case "/api/v1/rounds?project_id=1":
        return ok([]);
      default:
        return error(500, `unexpected route ${call.method} ${call.url}`);
    }
  });
  const view = render(<WorkspaceScreen projectId={1} projectName="Proj" onBack={() => undefined} />);
  return { calls, unmount: view.unmount };
}

async function openImportDialog(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(await screen.findByRole("button", { name: /^Import$/ }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText("Import Markdown files")).toBeInTheDocument();
  return dialog;
}

async function pickFiles(
  user: ReturnType<typeof userEvent.setup>,
  dialog: HTMLElement,
  files: File[],
): Promise<HTMLElement> {
  const input = within(dialog).getByTestId("import-file-input");
  await user.upload(input, files);
  return input;
}

describe("Markdown file-picker import (INT-008 R-079..R-081)", () => {
  it("opens the picker dialog without any path field and uploads the picked files as one multipart import, then refreshes the tree", async () => {
    const user = userEvent.setup();
    const { calls, unmount } = mountEmptyWorkspace();
    const dialog = await openImportDialog(user);

    const input = within(dialog).getByTestId("import-file-input");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute("accept", ".md,.markdown");
    expect(input).toHaveAttribute("multiple");
    expect(within(dialog).queryByRole("textbox")).not.toBeInTheDocument();

    const clickSpy = vi.spyOn(input, "click").mockImplementation(() => undefined);
    await user.click(within(dialog).getByRole("button", { name: "Choose files…" }));
    expect(clickSpy).toHaveBeenCalledTimes(1);

    const importConfirm = within(dialog).getByRole("button", { name: /^Import$/ });
    expect(importConfirm).toBeDisabled();

    const fileA = mdFile("a.md");
    const fileB = mdFile("b.markdown");
    await pickFiles(user, dialog, [fileA, fileB]);
    expect(await within(dialog).findByText(/2 files selected/)).toBeInTheDocument();
    expect(within(dialog).getByText("a.md")).toBeInTheDocument();
    expect(within(dialog).getByText("b.markdown")).toBeInTheDocument();
    expect(importConfirm).toBeEnabled();

    const treeGetsBefore = treeGetCount(calls);
    await user.click(importConfirm);

    const uploadCall = calls.find((c) => c.method === "POST" && c.url === "/api/v1/projects/1/import");
    expect(uploadCall).toBeDefined();
    expect(uploadCall?.body).toBeInstanceOf(FormData);
    const form = uploadCall?.body as FormData;
    expect(form.getAll("files").map((f) => (f as File).name)).toEqual(["a.md", "b.markdown"]);
    expect(uploadCall?.headers).toEqual({ Accept: "application/json" });

    await screen.findByTestId("doc-row-a.md");
    expect(screen.getByTestId("doc-row-b.markdown")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Import/ })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(treeGetCount(calls)).toBe(treeGetsBefore + 1);
    });
    unmount();
  });

  it("shows a busy state while the upload is in flight", async () => {
    const user = userEvent.setup();
    const { unmount } = mountEmptyWorkspace({ importStatus: "pending" });
    const dialog = await openImportDialog(user);
    await pickFiles(user, dialog, [mdFile("a.md")]);

    await user.click(within(dialog).getByRole("button", { name: /^Import$/ }));
    expect(await within(dialog).findByRole("button", { name: "Importing…" })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "Choose files…" })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    unmount();
  });

  it("surfaces a 409 on a second import inline and does not re-snapshot the tree", async () => {
    const user = userEvent.setup();
    const detail = "project already has resources — import is a one-shot action";
    const { calls, unmount } = mountEmptyWorkspace({ importStatus: "conflict", conflictDetail: detail });
    const dialog = await openImportDialog(user);
    const treeGetsBefore = treeGetCount(calls);
    await pickFiles(user, dialog, [mdFile("a.md")]);

    await user.click(within(dialog).getByRole("button", { name: /^Import$/ }));
    expect(await within(dialog).findByText(detail)).toBeInTheDocument();
    expect(screen.queryByTestId("doc-row-a.md")).not.toBeInTheDocument();
    expect(treeGetCount(calls)).toBe(treeGetsBefore);
    expect(within(dialog).getByRole("button", { name: /^Import$/ })).toBeEnabled();
    unmount();
  });

  it("surfaces a 400 rejection inline with the server detail", async () => {
    const user = userEvent.setup();
    const detail = "a.txt is not a Markdown file — nothing was imported";
    const { calls, unmount } = mountEmptyWorkspace({ importStatus: "rejected", rejectedDetail: detail });
    const dialog = await openImportDialog(user);
    const treeGetsBefore = treeGetCount(calls);
    await pickFiles(user, dialog, [mdFile("a.md")]);

    await user.click(within(dialog).getByRole("button", { name: /^Import$/ }));
    expect(await within(dialog).findByText(detail)).toBeInTheDocument();
    expect(screen.queryByTestId("doc-row-a.md")).not.toBeInTheDocument();
    expect(treeGetCount(calls)).toBe(treeGetsBefore);
    unmount();
  });

  it("offers no Import affordance once the project already has resources (snapshot-once)", async () => {
    mountEmptyWorkspace({ tree: importedTree });
    await screen.findByTestId("doc-row-a.md");
    expect(screen.queryByRole("button", { name: /Import/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("resets stale files and errors when the dialog closes and reopens", async () => {
    const user = userEvent.setup();
    const detail = "a.txt is not a Markdown file — nothing was imported";
    const { unmount } = mountEmptyWorkspace({ importStatus: "rejected", rejectedDetail: detail });
    let dialog = await openImportDialog(user);
    await pickFiles(user, dialog, [mdFile("a.md")]);
    expect(within(dialog).getByText("a.md")).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: /^Import$/ }));
    expect(await within(dialog).findByText(detail)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    dialog = await openImportDialog(user);
    expect(within(dialog).queryByText(detail)).not.toBeInTheDocument();
    expect(within(dialog).queryByText("a.md")).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/files selected/)).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /^Import$/ })).toBeDisabled();
    unmount();
  });
});
