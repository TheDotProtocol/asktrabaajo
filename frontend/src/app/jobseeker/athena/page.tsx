"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AthenaWorkspace } from "@/components/athena/AthenaWorkspace";
import { LoadingState } from "@/components/candidate/ui";

function CandidateAthenaInner() {
  const params = useSearchParams();
  return <AthenaWorkspace portal="candidate" from={params.get("from")} />;
}

export default function CandidateAthenaPage() {
  return (
    <Suspense fallback={<LoadingState label="Opening Athena…" />}>
      <CandidateAthenaInner />
    </Suspense>
  );
}
