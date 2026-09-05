"use client";

import { useEffect } from "react";

const DEFAULT_TITLE = "AskTrabaajo — The Operating System for the World of Work";
const DEFAULT_DESCRIPTION =
  "AskTrabaajo is the operating system for the world of work — connecting jobseekers, employers and government workforce intelligence through one live platform.";

export function usePageMeta({ title, description } = {}) {
  useEffect(() => {
    const prevTitle = document.title;
    document.title = title ? `${title} — AskTrabaajo` : DEFAULT_TITLE;

    const meta = document.querySelector('meta[name="description"]');
    const prevDescription = meta?.getAttribute("content") || "";
    if (meta && description) meta.setAttribute("content", description);

    return () => {
      document.title = prevTitle;
      if (meta) meta.setAttribute("content", prevDescription || DEFAULT_DESCRIPTION);
    };
  }, [title, description]);
}
