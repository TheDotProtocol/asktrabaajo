export type AthenaPortal = "candidate" | "employer";

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

export function sessionPurpose(portal: AthenaPortal, from: AthenaFrom): string {
  const surface = from.replaceAll("-", " ");
  if (portal === "candidate") {
    return `Candidate Employment OS. User opened Athena from ${surface}. Use only jobseeker tools and the professional digest.`;
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
    const bySurface: Partial<Record<AthenaFrom, SuggestedPrompt[]>> = {
      career: [
        { label: "Review my career direction", message: "Review my career direction using Career Advisor." },
        { label: "What skills should I build next?", message: "What skills should I build next based on my Work ID?" },
      ],
      opportunities: [
        { label: "Find my strongest matches", message: "Find my strongest job matches." },
        { label: "Why am I a strong match?", message: "Why would I be a strong match for roles like these?" },
      ],
      applications: [
        { label: "Why am I not getting interviews?", message: "Analyze my applications and tell me why I may not be getting interviews." },
      ],
      interviews: [
        { label: "Help me prepare", message: "Help me prepare for my upcoming interviews." },
      ],
      "work-id": [
        { label: "Review my Work ID", message: "Summarize my Work ID and what is still incomplete." },
      ],
    };
    return (
      bySurface[from] ?? [
        { label: "Find my strongest job matches", message: "Find my strongest job matches." },
        { label: "What skills should I build next?", message: "What skills should I build next?" },
        { label: "Review my career direction", message: "Review my career direction." },
        { label: "Help me prepare for an interview", message: "Help me prepare for an interview." },
      ]
    );
  }
  const bySurface: Partial<Record<AthenaFrom, SuggestedPrompt[]>> = {
    pipeline: [{ label: "What needs attention?", message: "What applications need attention in our pipeline?" }],
    candidates: [{ label: "Strongest candidates", message: "Show me the strongest discoverable candidates." }],
    jobs: [{ label: "Which candidates match this job?", message: "Which candidates match our open jobs?" }],
    interviews: [{ label: "Review upcoming interviews", message: "Help me review upcoming interviews." }],
  };
  return (
    bySurface[from] ?? [
      { label: "Show strongest candidates", message: "Show me the strongest discoverable candidates." },
      { label: "What applications need attention?", message: "What applications need attention?" },
      { label: "Review upcoming interviews", message: "Help me review upcoming interviews." },
      { label: "Which candidates match our jobs?", message: "Which candidates match our open jobs?" },
    ]
  );
}

export function degradedLinks(portal: AthenaPortal): { href: string; label: string; body: string }[] {
  if (portal === "candidate") {
    return [
      { href: "/jobseeker/career", label: "Career Advisor", body: "Deterministic paths, gaps, and matches from your Work ID." },
      { href: "/jobseeker/opportunities", label: "Opportunities", body: "Search the live catalogue and apply with confirmation." },
      { href: "/id/work-id", label: "Work ID", body: "Keep the professional record Athena would use." },
      { href: "/jobseeker/interview-prep", label: "Interview Prep", body: "Structured practice without a live model." },
    ];
  }
  return [
    { href: "/company/candidates", label: "Talent Graph", body: "Discover candidates the organization is allowed to see." },
    { href: "/company/pipeline", label: "Pipeline", body: "Review applications and make human hiring decisions." },
    { href: "/company/interviews", label: "Interviews", body: "Upcoming and past interviews for this organization." },
    { href: "/company/jobs", label: "Jobs", body: "Draft, publish, pause, and close roles." },
  ];
}

export function confirmButtonLabel(tool: string, summary: string): string {
  const count = (summary.match(/[0-9a-f-]{36}/gi) || []).length;
  if (tool === "apply_to_opportunities") {
    return count > 0 ? `Apply to ${count} selected jobs` : "Apply to the selected jobs";
  }
  if (tool === "apply_to_opportunity") return "Apply to this opportunity";
  if (tool === "send_message") return "Send this message";
  if (tool === "create_outreach") return "Send this outreach request";
  return "Confirm this action";
}

export function providerStateLabel(state: string): string {
  if (state === "available") return "Available";
  if (state === "temporarily_unavailable") return "Temporarily unavailable";
  if (state === "not_configured") return "Not configured";
  return "Limited";
}
