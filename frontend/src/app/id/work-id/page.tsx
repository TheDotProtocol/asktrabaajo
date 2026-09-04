"use client";
/**
 * Work ID — the persistent professional identity.
 * All writes go to canonical /work-id/* and /documents. Verification
 * states are rendered truthfully; nothing is shown as verified unless
 * the backend says so.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AthenaAskLink } from "@/components/athena/AthenaAskLink";
import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { api, fetchMe } from "@/lib/api/session";
import {
  CompletionOut,
  CredentialOut,
  EducationOut,
  EmploymentOut,
  ExperienceOut,
  MeResponse,
  PersonDocumentOut,
  ProfileOut,
  UserSkillOut,
  WorkIdSummary,
} from "@/lib/api/types";

type WSection = "experience" | "education" | "employment" | "credential" | "skill";

export default function WorkIdPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [work, setWork] = useState<WorkIdSummary | null>(null);
  const [completion, setCompletion] = useState<CompletionOut | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [add, setAdd] = useState<WSection | null>(null);

  const refresh = useCallback(async () => {
    const current = await fetchMe();
    setMe(current);
    if (!current) return;
    const [w, c] = await Promise.all([
      api.get<WorkIdSummary>("/work-id"),
      api.get<CompletionOut>("/work-id/completion"),
    ]);
    setWork(w);
    setCompletion(c);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function saveProfile(fields: Partial<ProfileOut>) {
    try {
      const body: Record<string, string | undefined> = {
        headline: fields.headline ?? undefined,
        city: fields.city ?? undefined,
        phone: fields.phone ?? undefined,
        summary: fields.summary ?? undefined,
      };
      await api.put<ProfileOut>(
        "/work-id/profile",
        Object.fromEntries(Object.entries(body).filter(([, v]) => v !== undefined))
      );
      setNotice("Profile saved. Employers only see what your privacy settings allow.");
      await refresh();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function submitAdd(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError("");
    const fd = new FormData(ev.currentTarget);
    const value = (name: string) => String(fd.get(name) ?? "");
    try {
      if (add === "experience") {
        await api.post("/work-id/experiences", {
          company_name: value("company_name"),
          title: value("title"),
          department: value("department") || undefined,
          location: value("location") || undefined,
          start_date: value("start_date"),
          is_current: true,
        });
      } else if (add === "education") {
        await api.post("/work-id/educations", {
          institution: value("institution"),
          level: value("level") || undefined,
          degree: value("degree") || undefined,
          field_of_study: value("field_of_study") || undefined,
        });
      } else if (add === "employment") {
        await api.post("/work-id/employments", {
          company_name: value("company_name"),
          title: value("title"),
          department: value("department") || undefined,
          employment_type: "full_time",
          start_date: value("start_date"),
          is_current: true,
        });
      } else if (add === "credential") {
        await api.post("/work-id/credentials", {
          name: value("name"),
          issuer: value("issuer") || undefined,
          credential_type: "certification",
        });
      } else if (add === "skill") {
        await api.put("/work-id/skills", {
          skill_name: value("skill_name"),
          level: value("level") || "intermediate",
        });
      }
      setAdd(null);
      setNotice("Saved to your Work ID.");
      await refresh();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function remove(kind: string, id: string, skillId?: string) {
    try {
      if (kind === "skill") {
        await api.delete(`/work-id/skills/${skillId}`);
      } else if (kind === "documents") {
        await api.delete(`/documents/${id}`);
      } else {
        await api.delete(`/work-id/${kind}s/${id}`);
      }
      await refresh();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!me || !work) {
    return <LoadingState label="Opening your Work ID…" />;
  }

  const percent = completion?.percent ?? 0;
  const missing = completion?.missing ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Professional identity"
        title="Work ID"
        subtitle="This is your persistent professional identity — not a job-board profile. Completeness improves matching. Verification is truthful."
        actions={
          <div className="flex flex-wrap gap-2">
            <AthenaAskLink portal="candidate" from="work-id" />
            <Link href="/jobseeker/privacy" className={ghostBtnCls}>
              Visibility
            </Link>
          </div>
        }
      />

      {error && <ErrorBanner message={error} onRetry={() => void refresh()} />}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}

      <section className={`${cardCls} grid gap-6 lg:grid-cols-3`}>
        <div className="lg:col-span-2">
          <p className={labelCls}>Identity</p>
          <h2 className="mt-2 text-2xl font-semibold">{me.full_name}</h2>
          <p className="mt-1 text-sm text-[#9ca3af]">
            {work.person.headline || "Add a headline so employers understand who you are."}
          </p>
          <p className="mt-2 text-xs text-[#6b7280]">
            {work.person.city || "Location not set"} · {me.email}
          </p>
        </div>
        <div>
          <p className={labelCls}>Completeness</p>
          <p className="mt-2 text-4xl font-semibold">{percent}%</p>
          <div className="mt-3 h-1.5 overflow-hidden rounded bg-[#0b0c0d]">
            <div className="h-full bg-[#d4af37]" style={{ width: `${percent}%` }} />
          </div>
          {missing.length > 0 ? (
            <p className="mt-3 text-xs text-[#9ca3af]">Still needed: {missing.join(", ")}</p>
          ) : (
            <p className="mt-3 text-xs text-emerald-400">Record is in good shape.</p>
          )}
        </div>
      </section>

      <section className={cardCls}>
        <h2 className="text-sm font-semibold">Profile</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className={labelCls}>Headline</label>
            <input className={inputCls} defaultValue={work.person.headline ?? ""} name="headline" placeholder="e.g. Platform Engineer" />
          </div>
          <div>
            <label className={labelCls}>City</label>
            <input className={inputCls} defaultValue={work.person.city ?? ""} name="city" />
          </div>
        </div>
        <div className="mt-3">
          <label className={labelCls}>Summary</label>
          <textarea className={inputCls} defaultValue={work.person.summary ?? ""} name="summary" rows={3} />
        </div>
        <div className="mt-3">
          <label className={labelCls}>Phone (private — never shown to employers automatically)</label>
          <input className={inputCls} defaultValue={work.person.phone ?? ""} name="phone" />
        </div>
        <button
          type="button"
          className={`${btnCls} mt-4`}
          onClick={() =>
            saveProfile({
              headline: (document.querySelector('[name="headline"]') as HTMLInputElement)?.value ?? work.person.headline ?? "",
              city: (document.querySelector('[name="city"]') as HTMLInputElement)?.value ?? undefined,
              summary: (document.querySelector('[name="summary"]') as HTMLTextAreaElement)?.value ?? undefined,
              phone: (document.querySelector('[name="phone"]') as HTMLInputElement)?.value ?? undefined,
            })
          }
        >
          Save profile
        </button>
      </section>

      <section className={cardCls}>
        <h2 className="text-sm font-semibold">Add to Work ID</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {(
            [
              ["experience", "Experience"],
              ["education", "Education"],
              ["employment", "Employment"],
              ["credential", "Credential"],
              ["skill", "Skill"],
            ] as [WSection, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={add === key ? btnCls : ghostBtnCls}
              onClick={() => setAdd(add === key ? null : key)}
            >
              + {label}
            </button>
          ))}
        </div>
        {add && (
          <form onSubmit={submitAdd} className="mt-4 grid gap-3 sm:grid-cols-2">
            {add === "experience" && (
              <>
                <Field label="Company" name="company_name" />
                <Field label="Title" name="title" />
                <Field label="Department" name="department" optional />
                <Field label="Location" name="location" optional />
                <Field label="Start date" name="start_date" type="date" />
              </>
            )}
            {add === "education" && (
              <>
                <Field label="Institution" name="institution" />
                <Field label="Level" name="level" optional placeholder="undergraduate" />
                <Field label="Degree" name="degree" optional />
                <Field label="Field of study" name="field_of_study" optional />
              </>
            )}
            {add === "employment" && (
              <>
                <Field label="Company" name="company_name" />
                <Field label="Title" name="title" />
                <Field label="Department" name="department" optional />
                <Field label="Start date" name="start_date" type="date" />
              </>
            )}
            {add === "credential" && (
              <>
                <Field label="Credential name" name="name" />
                <Field label="Issuer" name="issuer" optional />
              </>
            )}
            {add === "skill" && (
              <>
                <Field label="Skill" name="skill_name" />
                <Field label="Level" name="level" optional placeholder="advanced" />
              </>
            )}
            <div className="sm:col-span-2">
              <button className={btnCls} type="submit">
                Save
              </button>
            </div>
          </form>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Experience">
          {work.experiences.length === 0 ? (
            <Empty hint="Add roles you have actually held." />
          ) : (
            <ul className="space-y-3">
              {work.experiences.map((x: ExperienceOut) => (
                <li key={x.id} className="flex items-start justify-between gap-3 text-sm">
                  <div>
                    <p className="font-medium">{x.title} @ {x.company_name}</p>
                    <StatusPill status={x.verification_status ?? "unverified"} />
                  </div>
                  <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("experience", x.id)}>
                    remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Education">
          {work.educations.length === 0 ? (
            <Empty hint="Degrees and programmes belong here." />
          ) : (
            <ul className="space-y-3">
              {work.educations.map((x: EducationOut) => (
                <li key={x.id} className="flex justify-between gap-3 text-sm">
                  <span>{x.degree || x.level || "Study"} @ {x.institution}</span>
                  <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("education", x.id)}>
                    remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Employment">
          {work.employments.length === 0 ? (
            <Empty hint="Formal employment records, separate from experience notes." />
          ) : (
            <ul className="space-y-3">
              {work.employments.map((x: EmploymentOut) => (
                <li key={x.id} className="flex justify-between gap-3 text-sm">
                  <span>{x.title} @ {x.company_name}</span>
                  <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("employment", x.id)}>
                    remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Skills">
          {work.skills.length === 0 ? (
            <Empty hint="Skills feed matching and Career Advisor." />
          ) : (
            <ul className="space-y-3">
              {work.skills.map((x: UserSkillOut) => (
                <li key={x.id} className="flex justify-between gap-3 text-sm">
                  <span>
                    {x.name} <span className="text-[#6b7280]">({x.level})</span>
                  </span>
                  <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("skill", x.id, x.skill_id)}>
                    remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Credentials">
          {work.credentials.length === 0 ? (
            <Empty hint="Licences and certificates. Status is never invented." />
          ) : (
            <ul className="space-y-3">
              {work.credentials.map((x: CredentialOut) => (
                <li key={x.id} className="flex items-start justify-between gap-3 text-sm">
                  <div>
                    <p className="font-medium">{x.name}</p>
                    <StatusPill status={x.status} />
                  </div>
                  <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("credential", x.id)}>
                    remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <DocumentsSection refresh={refresh} remove={remove} />
      </div>
    </div>
  );
}

function Field({
  label,
  name,
  type = "text",
  optional,
  placeholder,
}: {
  label: string;
  name: string;
  type?: string;
  optional?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className={labelCls}>
        {label} {optional && <span className="font-normal text-[#6b7280]">(optional)</span>}
      </label>
      <input className={inputCls} name={name} type={type} placeholder={placeholder} />
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={cardCls}>
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Empty({ hint }: { hint: string }) {
  return <p className="text-sm text-[#6b7280]">{hint}</p>;
}

function DocumentsSection({
  refresh,
  remove,
}: {
  refresh: () => Promise<void>;
  remove: (kind: string, id: string, skillId?: string) => Promise<void>;
}) {
  const [docs, setDocs] = useState<PersonDocumentOut[]>([]);

  const load = useCallback(async () => {
    try {
      setDocs(await api.get<PersonDocumentOut[]>("/documents"));
    } catch {
      setDocs([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addDoc(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const fd = new FormData(ev.currentTarget);
    await api.post("/documents", {
      name: String(fd.get("name") ?? "document"),
      doc_type: String(fd.get("doc_type") ?? "other"),
      mime_type: "application/octet-stream",
    });
    await load();
    await refresh();
  }

  return (
    <section className={cardCls}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Documents</h2>
        <Link href="/jobseeker/documents" className="text-xs text-[#d4af37] hover:underline">
          Full vault
        </Link>
      </div>
      <p className="mb-3 text-xs text-[#6b7280]">
        Files stay private until you grant access. Registering a record does not share it.
      </p>
      <form className="mb-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]" onSubmit={addDoc}>
        <input className={inputCls} name="name" placeholder="Document name" />
        <input className={inputCls} name="doc_type" placeholder="resume, certificate…" />
        <button className={btnCls} type="submit">
          Add
        </button>
      </form>
      {docs.length === 0 ? (
        <Empty hint="No documents registered." />
      ) : (
        <ul className="space-y-2">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-2 text-sm">
              <span>
                {d.name} <span className="text-[#6b7280]">({d.doc_type})</span>
              </span>
              <div className="flex items-center gap-2">
                <StatusPill status={d.verification_status} />
                <button type="button" className="text-xs text-[#9ca3af] hover:text-red-300" onClick={() => void remove("documents", d.id)}>
                  archive
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
