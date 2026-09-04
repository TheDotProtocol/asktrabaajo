"use client";

import { useEffect, useState } from "react";

import { PageHeader, cardCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { AthenaStatus } from "@/lib/api/types";

export default function AdminAthenaPage() {
  const [status, setStatus] = useState<AthenaStatus | null>(null);
  const [modes, setModes] = useState<string[]>([]);

  useEffect(() => {
    api.get<AthenaStatus>("/athena/status").then(setStatus).catch(() => setStatus(null));
    api.get<string[]>("/athena/modes").then(setModes).catch(() => setModes([]));
  }, []);

  const platform = modes.includes("platform_operator");

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Athena"
        title="Platform intelligence"
        subtitle="Platform-operator Athena is architecture-only. This page does not invent admin AI, enforcement tools, or private-data access."
      />
      <div className={cardCls}>
        <p className="text-xl font-semibold text-white">
          {status?.available
            ? "Live intelligence is configured, but platform-operator tools are not registered."
            : "Athena intelligence is currently unavailable."}
        </p>
        <p className="mt-3 text-sm text-[#9ca3af]">
          {platform
            ? "Your account may open a platform_operator session. The backend still refuses enforcement, moderation, and private-data tools."
            : "This account does not have platform-operator Athena mode."}
        </p>
        <p className="mt-3 text-sm text-[#6b7280]">
          Candidate and Employer Athena remain the working products. Do not use this screen as a
          second AI service.
        </p>
      </div>
    </div>
  );
}
