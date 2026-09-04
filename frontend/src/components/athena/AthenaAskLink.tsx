import Link from "next/link";

import { ghostBtnCls } from "@/components/candidate/ui";
import { AthenaFrom, AthenaPortal } from "@/lib/athena/context";

export function AthenaAskLink({
  portal,
  from,
  label = "Ask Athena",
}: {
  portal: AthenaPortal;
  from: AthenaFrom;
  label?: string;
}) {
  const href = `${portal === "candidate" ? "/jobseeker/athena" : "/company/athena"}?from=${from}`;
  return (
    <Link href={href} className={ghostBtnCls}>
      {label}
    </Link>
  );
}
