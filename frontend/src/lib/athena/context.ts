export type AthenaPortal = "candidate" | "employer" | "government";

export type AthenaFrom =
  | "home"
  | "work-id"
  | "career"
  | "opportunities"
  | "applications"
  | "interviews"
  | "offers"
  | "pipeline"
  | "candidates"
  | "jobs"
  | "profile";

const FROM_VALUES: AthenaFrom[] = [
  "home",
  "work-id",
  "career",
  "opportunities",
  "applications",
  "interviews",
  "offers",
  "pipeline",
  "candidates",
  "jobs",
  "profile",
];

export function parseAthenaFrom(value: string | null): AthenaFrom {
  if (value && (FROM_VALUES as string[]).includes(value)) return value as AthenaFrom;
  return "home";
}

const CONTEXT_LABEL: Record<AthenaFrom, string> = {
  home: "Command center",
  "work-id": "Work ID",
  career: "Career Advisor",
  opportunities: "Opportunities",
  applications: "Applications",
  interviews: "Interviews",
  offers: "Offers",
  pipeline: "Recruitment pipeline",
  candidates: "Talent Graph",
  jobs: "Jobs",
  profile: "Company profile",
};

export function contextLabel(from: AthenaFrom): string {
  return CONTEXT_LABEL[from];
}

export function sessionPurpose(portal: AthenaPortal, from: AthenaFrom): string {
  const surface = from.replaceAll("-", " ");
  if (portal === "candidate") {
    return `Candidate Employment OS. User opened Athena from ${surface}. Use only jobseeker tools and the professional digest.`;
  }
  if (portal === "government") {
    return `Government workforce intelligence. User opened Athena from ${surface}. Use only government aggregate tools. Never search people or Work IDs. If a cohort is below the privacy threshold, say it is too small to report.`;
  }
  return `Employer Employment OS. User opened Athena from ${surface}. Use only organization-scoped tools.`;
}

export interface SuggestedPrompt {
  label: string;
  message: string;
  href?: string;
}

export function suggestedPrompts(portal: AthenaPortal, from: AthenaFrom): SuggestedPrompt[] {
  if (portal === "candidate") {
    const core: SuggestedPrompt[] = [
      { label: "Find my strongest job matches", message: "Find my strongest job matches." },
      { label: "What skills should I build next?", message: "What skills should I build next?" },
      { label: "Help me prepare for an interview", message: "Help me prepare for an interview." },
      { label: "Review my career direction", message: "Review my career direction." },
    ];
    if (from === "applications") {
      return [
        { label: "Why am I not getting interviews?", message: "Analyze my applications and tell me why I may not be getting interviews." },
        ...core.slice(0, 3),
      ];
    }
    if (from === "work-id") {
      return [
        { label: "Review my Work ID", message: "Summarize my Work ID and what is still incomplete." },
        ...core.slice(0, 3),
      ];
    }
    return core;
  }
  if (portal === "government") {
    return [
      { label: "Summarize the workforce", message: "Give me a privacy-safe workforce summary." },
      { label: "Where are the skill gaps?", message: "Which skills show hiring demand above observed supply?" },
      { label: "Hiring demand by industry", message: "What is observed hiring demand by industry?" },
      { label: "Workforce by city", message: "Show aggregate workforce by city. Suppress small cohorts." },
    ];
  }
  const core: SuggestedPrompt[] = [
    { label: "Find the strongest candidates", message: "Show me the strongest discoverable candidates." },
    { label: "What applications need attention?", message: "What applications need attention?" },
    { label: "Review today's interviews", message: "Help me review upcoming interviews." },
    { label: "Show candidates matching this role", message: "Which candidates match our open jobs?" },
  ];
  return core;
}

export function degradedLinks(portal: AthenaPortal): { href: string; label: string; body: string }[] {
  if (portal === "candidate") {
    return [
      { href: "/jobseeker/career", label: "Career Advisor", body: "Deterministic paths, gaps, and matches from your Work ID." },
      { href: "/jobseeker/opportunities", label: "Opportunities", body: "Search the live catalogue and apply with confirmation." },
      { href: "/jobseeker/applications", label: "Applications", body: "Track the controlled application lifecycle." },
      { href: "/jobseeker/interview-prep", label: "Interview Prep", body: "Structured practice without a live model." },
      { href: "/id/work-id", label: "Work ID", body: "Keep the professional record Athena would use." },
    ];
  }
  if (portal === "government") {
    return [
      { href: "/government", label: "Command Center", body: "Live aggregate cards without individual records." },
      { href: "/government/skills", label: "Skills", body: "Supply, demand, and suppressed-safe gaps." },
      { href: "/government/reports", label: "Reports", body: "Reproducible aggregate reports and exports." },
    ];
  }
  return [
    { href: "/company/candidates", label: "Talent Graph", body: "Discover candidates the organization is allowed to see." },
    { href: "/company/pipeline", label: "Pipeline", body: "Review applications and make human hiring decisions." },
    { href: "/company/interviews", label: "Interviews", body: "Upcoming and past interviews for this organization." },
    { href: "/company/jobs", label: "Jobs", body: "Draft, publish, pause, and close roles." },
  ];
}

export function confirmCount(summary: string): number {
  return (summary.match(/[0-9a-f-]{36}/gi) || []).length;
}

export function confirmButtonLabel(tool: string, summary: string): string {
  const count = confirmCount(summary);
  if (tool === "apply_to_opportunities") {
    return count > 0 ? `Apply to ${count} selected jobs` : "Apply to the selected jobs";
  }
  if (tool === "apply_to_opportunity") return "Apply to this opportunity";
  if (tool === "send_message") return "Send this message";
  if (tool === "create_outreach") {
    return count > 0 ? `Send outreach to ${count} candidate${count === 1 ? "" : "s"}` : "Send this outreach request";
  }
  return "Confirm this action";
}

export function confirmConsequence(tool: string): string {
  if (tool === "apply_to_opportunity" || tool === "apply_to_opportunities") {
    return "This creates real applications on your Work ID. The backend will apply only the exact opportunities in this confirmation.";
  }
  if (tool === "send_message") {
    return "The message is sent through AskTrabaajo on an existing conversation. Raw personal contact details are not exposed.";
  }
  if (tool === "create_outreach") {
    return "The candidate receives a request they can accept or decline. Nothing is sent around the platform.";
  }
  return "The backend will re-authorize this exact scope before anything runs.";
}

export function phaseLabel(phase: "idle" | "understanding" | "preparing" | "confirming" | "executing"): string {
  if (phase === "understanding") return "Understanding request";
  if (phase === "preparing") return "Preparing results";
  if (phase === "confirming") return "Waiting for confirmation";
  if (phase === "executing") return "Executing action";
  return "";
}

export function providerStateLabel(state: string): string {
  if (state === "available") return "Available";
  if (state === "temporarily_unavailable") return "Temporarily unavailable";
  if (state === "not_configured") return "Not configured";
  return "Limited";
}
