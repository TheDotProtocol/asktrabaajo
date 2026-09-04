"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AthenaWorkspace } from "@/components/athena/AthenaWorkspace";
import { LoadingState } from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";

function EmployerAthenaInner() {
  const params = useSearchParams();
  const { organizationId } = useOrg();
  return <AthenaWorkspace portal="employer" from={params.get("from")} organizationId={organizationId} />;
}

export default function EmployerAthenaPage() {
  return (
    <Suspense fallback={<LoadingState label="Opening Athena HR…" />}>
      <EmployerAthenaInner />
    </Suspense>
  );
}
