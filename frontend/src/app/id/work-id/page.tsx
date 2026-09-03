"use client";
/**
 * Work ID proof flow — profile + education/skills/experience/credentials/
 * employment/documents through the canonical API. Functional validation
 * only; no visual polish (Figma is the visual source of truth).
 */
import { useCallback, useEffect, useState } from "react";

import { api, fetchMe } from "@/lib/api/session";
import {
  CompletionOut,
  CredentialOut,
  EducationOut,
  EmploymentOut,
  ExperienceOut,
  MeResponse,
  ProfileOut,
  UserSkillOut,
  WorkIdSummary,
} from "@/lib/api/types";

const inputCls =
  "w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-3 py-1.5 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const subBtnCls =
  "rounded border border-neutral-300 px-2 py-1 text-xs dark:border-neutral-700";
const rowCls = "rounded-lg border border-neutral-200 p-4 dark:border-neutral-800";
const labelCls = "mb-1 block text-xs font-medium text-neutral-500";

type WSection = "experience" | "education" | "employment" | "credential" | "skill";

interface AddForm {
  section: WSection | null;
}

export default function WorkIdPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [work, setWork] = useState<WorkIdSummary | null>(null);
  const [completion, setCompletion] = useState<CompletionOut | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [add, setAdd] = useState<AddForm>({ section: null });

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
    refresh();
  }, [refresh]);

  async function saveProfile(fields: Partial<ProfileOut>) {
    try {
      const body: Record<string, string | undefined> = {
        headline: fields.headline ?? undefined,
        city: fields.city ?? undefined,
        phone: fields.phone ?? undefined,
        summary: fields.summary ?? undefined,
      };
      await api.put<ProfileOut>("/work-id/profile", Object.fromEntries(
        Object.entries(body).filter(([, v]) => v !== undefined)
      ));
      setNotice("Profile saved.");
      await refresh();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function submitAdd(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError("");
    const form = ev.currentTarget;
    const fd = new FormData(form);
    const value = (name: string) => String(fd.get(name) ?? "");
    try {
      if (add.section === "experience") {
        await api.post("/work-id/experiences", {
          company_name: value("company_name"),
          title: value("title"),
          department: value("department") || undefined,
          location: value("location") || undefined,
          start_date: value("start_date"),
          is_current: true,
        });
      } else if (add.section === "education") {
        await api.post("/work-id/educations", {
          institution: value("institution"),
          level: value("level") || undefined,
          degree: value("degree") || undefined,
          field_of_study: value("field_of_study") || undefined,
        });
      } else if (add.section === "employment") {
        await api.post("/work-id/employments", {
          company_name: value("company_name"),
          title: value("title"),
          department: value("department") || undefined,
          employment_type: "full_time",
          start_date: value("start_date"),
          is_current: true,
        });
      } else if (add.section === "credential") {
        await api.post("/work-id/credentials", {
          name: value("name"),
          issuer: value("issuer") || undefined,
          credential_type: "certification",
        });
      } else if (add.section === "skill") {
        await api.put("/work-id/skills", {
          skill_name: value("skill_name"),
          level: value("level") || "intermediate",
        });
      }
      setAdd({ section: null });
      setNotice("Saved.");
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
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p>Sign in first — <a className="underline" href="/id">go to identity</a>.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Work ID</h1>
          <p className="text-sm text-neutral-500">
            The persistent professional identity of {me.full_name}
          </p>
        </div>
        <a className="text-sm text-neutral-500 underline" href="/id">
          Back to identity
        </a>
      </div>

      {completion && (
        <p className="mb-4 text-sm">
          Profile completion:{" "}
          <strong>{completion.percent}%</strong>
          {completion.missing.length > 0 && (
            <span className="text-neutral-500">
              {" "}
              — missing: {completion.missing.join(", ")}
            </span>
          )}
        </p>
      )}
      {notice && <p className="mb-3 text-sm text-emerald-700">{notice}</p>}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {/* Profile */}
      <section className={`${rowCls} mb-4`}>
        <h2 className="mb-3 font-medium">Profile</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Headline</label>
            <input
              className={inputCls}
              defaultValue={work.person.headline ?? ""}
              name="headline"
              placeholder="e.g. Platform Engineer"
            />
          </div>
          <div>
            <label className={labelCls}>City</label>
            <input
              className={inputCls}
              defaultValue={work.person.city ?? ""}
              name="city"
            />
          </div>
        </div>
        <div className="mt-2">
          <label className={labelCls}>Summary</label>
          <textarea
            className={inputCls}
            defaultValue={work.person.summary ?? ""}
            name="summary"
            rows={2}
          />
        </div>
        <div className="mt-2">
          <label className={labelCls}>Phone (private)</label>
          <input
            className={inputCls}
            defaultValue={work.person.phone ?? ""}
            name="phone"
          />
        </div>
        <div className="mt-3">
          <button
            className={btnCls}
            onClick={() =>
              saveProfile({
                headline:
                  (document.querySelector('[name="headline"]') as HTMLInputElement)
                    ?.value ?? work.person.headline ?? "",
                city: (document.querySelector('[name="city"]') as HTMLInputElement)
                  ?.value ?? undefined,
                summary:
                  (document.querySelector('[name="summary"]') as HTMLTextAreaElement)
                    ?.value ?? undefined,
                phone: (document.querySelector('[name="phone"]') as HTMLInputElement)
                  ?.value ?? undefined,
              })
            }
          >
            Save profile
          </button>
        </div>
      </section>

      {/* Add forms */}
      <section className={`${rowCls} mb-4`}>
        <h2 className="mb-2 font-medium">Add to Work ID</h2>
        <div className="mb-3 flex flex-wrap gap-2">
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
              className={subBtnCls}
              onClick={() => setAdd({ section: add.section === key ? null : key })}
            >
              + {label}
            </button>
          ))}
        </div>

        {add.section && (
          <form onSubmit={submitAdd} className="grid grid-cols-2 gap-3">
            {add.section === "experience" && (
              <>
                <Field label="Company" name="company_name" />
                <Field label="Title" name="title" />
                <Field label="Department" name="department" optional />
                <Field label="Location" name="location" optional />
                <Field label="Start date" name="start_date" type="date" />
              </>
            )}
            {add.section === "education" && (
              <>
                <Field label="Institution" name="institution" />
                <Field label="Level" name="level" optional placeholder="undergraduate" />
                <Field label="Degree" name="degree" optional />
                <Field label="Field of study" name="field_of_study" optional />
              </>
            )}
            {add.section === "employment" && (
              <>
                <Field label="Company" name="company_name" />
                <Field label="Title" name="title" />
                <Field label="Department" name="department" optional />
                <Field label="Start date" name="start_date" type="date" />
              </>
            )}
            {add.section === "credential" && (
              <>
                <Field label="Credential name" name="name" />
                <Field label="Issuer" name="issuer" optional />
              </>
            )}
            {add.section === "skill" && (
              <>
                <Field label="Skill" name="skill_name" />
                <Field label="Level" name="level" optional placeholder="advanced" />
              </>
            )}
            <div className="col-span-2">
              <button className={btnCls} type="submit">
                Save
              </button>
            </div>
          </form>
        )}
      </section>

      {/* Sections */}
      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Experience">
          <ul className="space-y-2">
            {work.experiences.length === 0 && <Empty />}
            {work.experiences.map((x: ExperienceOut) => (
              <li key={x.id} className="flex justify-between gap-2 text-sm">
                <span>
                  {x.title} @ {x.company_name}
                  {x.verification_status !== "unverified" && " ✓"}
                </span>
                <button className="text-xs text-red-600" onClick={() => remove("experience", x.id)}>
                  remove
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Education">
          <ul className="space-y-2">
            {work.educations.length === 0 && <Empty />}
            {work.educations.map((x: EducationOut) => (
              <li key={x.id} className="flex justify-between gap-2 text-sm">
                <span>
                  {x.degree || x.level || "Study"} @ {x.institution}
                </span>
                <button className="text-xs text-red-600" onClick={() => remove("education", x.id)}>
                  remove
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Employment">
          <ul className="space-y-2">
            {work.employments.length === 0 && <Empty />}
            {work.employments.map((x: EmploymentOut) => (
              <li key={x.id} className="flex justify-between gap-2 text-sm">
                <span>
                  {x.title} @ {x.company_name}
                </span>
                <button className="text-xs text-red-600" onClick={() => remove("employment", x.id)}>
                  remove
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Skills">
          <ul className="space-y-2">
            {work.skills.length === 0 && <Empty />}
            {work.skills.map((x: UserSkillOut) => (
              <li key={x.id} className="flex justify-between gap-2 text-sm">
                <span>
                  {x.name} <span className="text-neutral-500">({x.level})</span>
                </span>
                <button
                  className="text-xs text-red-600"
                  onClick={() => remove("skill", x.id, x.skill_id)}
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Credentials">
          <ul className="space-y-2">
            {work.credentials.length === 0 && <Empty />}
            {work.credentials.map((x: CredentialOut) => (
              <li key={x.id} className="flex justify-between gap-2 text-sm">
                <span>
                  {x.name}
                  <span className="ml-1 text-neutral-500">[{x.status}]</span>
                </span>
                <button className="text-xs text-red-600" onClick={() => remove("credential", x.id)}>
                  remove
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <DocumentsSection refresh={refresh} remove={remove} />
      </div>
    </main>
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
        {label} {optional && <span className="font-normal">(optional)</span>}
      </label>
      <input className={inputCls} name={name} type={type} placeholder={placeholder} />
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`${rowCls}`}>
      <h2 className="mb-2 font-medium">{title}</h2>
      {children}
    </section>
  );
}

function Empty() {
  return <li className="text-sm text-neutral-400">Nothing yet.</li>;
}

function DocumentsSection({
  refresh,
  remove,
}: {
  refresh: () => Promise<void>;
  remove: (kind: string, id: string, skillId?: string) => Promise<void>;
}) {
  const [docs, setDocs] = useState<
    { id: string; name: string; doc_type: string }[]
  >([]);

  const load = useCallback(async () => {
    try {
      setDocs(await api.get("/documents"));
    } catch {
      setDocs([]);
    }
  }, []);

  useEffect(() => {
    load();
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
    <section className={rowCls}>
      <h2 className="mb-2 font-medium">Documents</h2>
      <form className="mb-2 flex gap-2" onSubmit={addDoc}>
        <input className={inputCls} name="name" placeholder="Document name" />
        <input className={inputCls} name="doc_type" placeholder="type (resume…)" />
        <button className={btnCls} type="submit">
          Add
        </button>
      </form>
      <ul className="space-y-2">
        {docs.length === 0 && <Empty />}
        {docs.map((d) => (
          <li key={d.id} className="flex justify-between gap-2 text-sm">
            <span>
              {d.name} <span className="text-neutral-500">({d.doc_type})</span>
            </span>
            <button
              className="text-xs text-red-600"
              onClick={() => remove("documents", d.id)}
            >
              archive
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
