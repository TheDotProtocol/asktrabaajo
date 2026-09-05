"use client";

import AudiencePage from "@/marketing/pages/audiences/AudiencePage";
import { AUDIENCE_PAGES } from "@/marketing/pages/audiences/content";

export default function Page() {
  return <AudiencePage data={AUDIENCE_PAGES.institutions} />;
}
