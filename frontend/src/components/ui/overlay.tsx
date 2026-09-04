import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Button } from "./button";

interface OverlayPanelProps {
  side: "left" | "right";
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/**
 * INT-009 (SD-32): a full-height fixed overlay panel for narrow (phone/tablet)
 * widths, opened from a control on the content surface. Closed panels are not
 * rendered at all, so jsdom tests observe reachability through presence.
 */
export function OverlayPanel({ side, title, onClose, children }: OverlayPanelProps) {
  return (
    <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/40" aria-hidden="true" onClick={onClose} />
      <div
        className={cn(
          "absolute inset-y-0 flex w-[min(85vw,22.5rem)] flex-col bg-background shadow-xl",
          side === "left" ? "left-0 border-r" : "right-0 border-l",
        )}
      >
        <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b pl-4 pr-2">
          <h2 className="truncate text-sm font-semibold">{title}</h2>
          <Button variant="ghost" size="sm" aria-label={`Close ${title}`} onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
