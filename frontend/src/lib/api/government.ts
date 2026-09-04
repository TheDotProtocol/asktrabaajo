import { api } from "@/lib/api/session";

export type CohortStatus = "ok" | "suppressed" | "insufficient_cohort";

export type CohortCell = {
  value: number | null;
  status: CohortStatus | string;
  label?: string;
};

export type Bucket = {
  key: string;
  value: number | null;
  status: CohortStatus | string;
};

export type BucketSet = {
  buckets: Bucket[];
  any_suppressed?: boolean;
  visible_sum?: number | null;
  unit?: string;
};

export type GovernmentFilters = {
  country?: string;
  state_province?: string;
  city?: string;
  industry?: string;
  skill?: string;
};

export type IntelligenceEnvelope = {
  privacy: string;
  privacy_threshold: number;
  freshness: string;
  generated_at: string;
  period: string;
  filters: Record<string, string>;
  status: string;
  message?: string;
  cards?: Record<string, CohortCell>;
  top_skills?: BucketSet;
  emerging_skills?: { status: string; message: string };
  group_by?: string;
  buckets?: Bucket[];
  any_suppressed?: boolean;
  supply?: BucketSet;
  demand?: BucketSet;
  gaps?: Array<{
    key: string;
    demand?: number;
    supply?: number | null;
    gap?: number | null;
    status: string;
    message?: string;
  }>;
  note?: string;
  unit?: string;
  active_employers?: CohortCell;
  kind?: string;
  title?: string;
  workforce?: CohortCell;
};

export type GovernmentSettings = {
  privacy: string;
  privacy_threshold: number;
  freshness: string;
  dataset_scope: string;
  individual_lookup: boolean;
  consent_disclosure: string;
  investment_workflows: string;
  government_industry_outreach: string;
  memberships: Array<{
    organization_id: string;
    organization_name: string;
    role: string;
  }>;
};

function qs(filters: GovernmentFilters, extra: Record<string, string> = {}) {
  const params = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const governmentApi = {
  overview: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/overview${qs(filters)}`),
  workforce: (groupBy: string, filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/workforce${qs(filters, { group_by: groupBy })}`),
  geography: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/workforce/geography${qs(filters)}`),
  employment: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/workforce/employment${qs(filters)}`),
  skills: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/skills${qs(filters)}`),
  industries: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/industries${qs(filters)}`),
  opportunities: (groupBy: string, filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/opportunities${qs(filters, { group_by: groupBy })}`),
  companies: (filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/companies${qs(filters)}`),
  report: (kind: string, filters: GovernmentFilters = {}) =>
    api.get<IntelligenceEnvelope>(`/government/reports/${kind}${qs(filters)}`),
  exportJson: (kind: string, filters: GovernmentFilters = {}) =>
    api.get<{ rows: Array<Record<string, unknown>>; privacy: string }>(
      `/government/exports/${kind}${qs(filters, { format: "json" })}`
    ),
  settings: () => api.get<GovernmentSettings>("/government/settings"),
};
