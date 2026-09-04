"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AthenaWorkspace } from "@/components/athena/AthenaWorkspace";
import { LoadingState } from "@/components/candidate/ui";
import { governmentMemberships } from "@/lib/api/portal";
import { useCanonicalAuth } from "@/context/AuthContext";

function GovernmentAthenaInner() {
  const params = useSearchParams();
  const { me } = useCanonicalAuth();
  const orgId = governmentMemberships(me)[0]?.organization_id;
  return (
    <AthenaWorkspace
      portal="government"
      from={params.get("from")}
      organizationId={orgId}
    />
  );
}

export default function GovernmentAthenaPage() {
  return (
    <Suspense fallback={<LoadingState label="Opening Government Athena…" />}>
      <GovernmentAthenaInner />
    </Suspense>
  );
}
