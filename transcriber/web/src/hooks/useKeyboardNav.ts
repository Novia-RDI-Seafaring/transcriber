import { useEffect } from "react";
import { useStore } from "../store";

/**
 * Global keybindings:
 *   ↑/↓        — step segment selection
 *   Space      — play / pause the current clip (handled by AudioPlayer)
 *   /          — focus the search input
 *   Escape     — clear selection
 */
export function useKeyboardNav() {
  useEffect(() => {
    function isTextInput(el: EventTarget | null): boolean {
      if (!(el instanceof HTMLElement)) return false;
      const tag = el.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || el.isContentEditable;
    }

    function onKey(e: KeyboardEvent) {
      const { result, highlighted, setHighlighted } = useStore.getState();
      if (!result) return;

      if (e.key === "/" && !isTextInput(e.target)) {
        e.preventDefault();
        document.getElementById("transcript-search")?.focus();
        return;
      }

      if (e.key === "Escape") {
        useStore.getState().clearSelected();
        setHighlighted(null);
        return;
      }

      if (isTextInput(e.target)) return;

      const last = result.segments.length - 1;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = highlighted == null ? 0 : Math.min(last, highlighted + 1);
        setHighlighted(next);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const next = highlighted == null ? last : Math.max(0, highlighted - 1);
        setHighlighted(next);
      } else if (e.key === " " && highlighted != null) {
        e.preventDefault();
        const audio = document.querySelector("audio");
        if (audio) {
          if (audio.paused) void audio.play();
          else audio.pause();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
