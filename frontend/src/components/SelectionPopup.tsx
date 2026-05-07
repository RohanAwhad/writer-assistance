import { useEffect, useState, useCallback, useRef } from "react";
import { MessageSquarePlus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SelectionPopupProps {
  containerRef: React.RefObject<HTMLElement | null>;
  onAddNote: (selectedText: string) => void;
}

export default function SelectionPopup({
  containerRef,
  onAddNote,
}: SelectionPopupProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [selectedText, setSelectedText] = useState("");
  const popupRef = useRef<HTMLDivElement>(null);

  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    if (!container.contains(selection.anchorNode)) return;

    const text = selection.toString().trim();
    if (text.length < 3) return;

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    setSelectedText(text);
    setPosition({
      top: rect.top - containerRect.top - 44,
      left: rect.left - containerRect.left + rect.width / 2,
    });
    setVisible(true);
  }, [containerRef]);

  const handleMouseDown = useCallback(
    (e: MouseEvent) => {
      if (popupRef.current && popupRef.current.contains(e.target as Node)) {
        return;
      }
      setVisible(false);
    },
    []
  );

  useEffect(() => {
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("mousedown", handleMouseDown);
    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("mousedown", handleMouseDown);
    };
  }, [handleMouseUp, handleMouseDown]);

  if (!visible) return null;

  return (
    <div
      ref={popupRef}
      className="absolute z-50 -translate-x-1/2 animate-in fade-in zoom-in-95 duration-150"
      style={{ top: position.top, left: position.left }}
    >
      <div className="flex items-center gap-1 rounded-lg border bg-popover px-2 py-1.5 shadow-lg">
        <Button
          size="sm"
          variant="ghost"
          className="h-7 gap-1.5 text-xs"
          onMouseDown={(e) => {
            e.preventDefault();
            onAddNote(selectedText);
            setVisible(false);
            window.getSelection()?.removeAllRanges();
          }}
        >
          <MessageSquarePlus className="h-3.5 w-3.5" />
          Add as Note
        </Button>
      </div>
      <div className="mx-auto h-2 w-2 -translate-y-px rotate-45 border-b border-r bg-popover" />
    </div>
  );
}
