import type {
  AnnotationOut,
  ExpertRunOut,
  LensProposalOut,
  ResourceOut,
  RoundDetailOut,
  RoundSummary,
  TreeNodeOut,
} from "../../api/types";

export interface DocData {
  resource: ResourceOut;
  annotations: AnnotationOut[];
}

export interface LensDocState {
  status: "loading" | "ready" | "error";
  proposals: LensProposalOut[];
  error: string | null;
}

export type ExpertDocState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "ready"; runs: ExpertRunOut[] };

export interface RoundDetailCache {
  [roundId: number]: RoundDetailOut | null;
}

export function roundDocsMap(round: RoundDetailOut | null): Map<number, string> {
  const map = new Map<number, string>();
  if (round !== null) {
    for (const d of round.docs) map.set(d.id, d.path);
  }
  return map;
}

export function treeFiles(nodes: TreeNodeOut[]): TreeNodeOut[] {
  return nodes.filter((n) => n.kind === "file");
}

export function roundSummaryById(
  rounds: RoundSummary[] | null,
  roundId: number | null,
): RoundSummary | null {
  if (rounds === null || roundId === null) return null;
  return rounds.find((r) => r.id === roundId) ?? null;
}
