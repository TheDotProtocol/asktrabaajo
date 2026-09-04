"use client";
/**
 * Work DNA — the assessment and its structured result.
 *
 * The assessment seeks to understand the person across working style,
 * communication, risk, learning, motivation, leadership, environment.
 * Results are shown as named dimensions with confidence — never one
 * reductive score, never a claim the answers cannot support.
 */
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, PageHeader, btnCls, cardCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { DnaProfile, DnaQuestion } from "@/lib/api/types";
const optionCls = (selected: boolean) =>
  `block w-full rounded-lg border px-4 py-2.5 text-left text-sm transition ${
    selected
      ? "border-[#d4af37] bg-[#d4af37]/10 text-white"
      : "border-[#23272a] hover:border-[#d4af37]/50"
  }`;

export default function WorkDnaPage() {
  const [questions, setQuestions] = useState<DnaQuestion[]>([]);
  const [profile, setProfile] = useState<DnaProfile | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      setQuestions(await api.get<DnaQuestion[]>("/jobseeker/work-dna/questions"));
      const existing = await api.get<DnaProfile | null>("/jobseeker/work-dna");
      setProfile(existing);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const created = await api.post<DnaProfile>("/jobseeker/work-dna/assessments", {
        answers,
      });
      setProfile(created);
      setNotice("Work DNA profile updated.");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  const answered = Object.keys(answers).length;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Professional characteristics"
        title="Work DNA"
        subtitle="An evolving understanding of how you work — not a personality test, and never an inference about protected characteristics."
      />

      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <ErrorBanner message={error} />}

      {!profile && questions.length === 0 && (
        <EmptyState
          title="Work DNA is not available yet"
          body="Questions come from the canonical API. When they load, answer honestly — results stay yours."
        />
      )}

      {/* Current profile */}
      {profile && profile.dimensions && profile.dimensions.length > 0 && (
        <section className={cardCls}>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Your profile</h2>
            <span className="text-xs text-neutral-400">
              v{profile.version} · {profile.completed_at ? new Date(profile.completed_at).toLocaleDateString() : ""}
            </span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {profile.dimensions.map((d) => (
              <div key={d.key} className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
                <div className="flex items-baseline justify-between">
                  <p className="text-sm font-medium">{d.label}</p>
                  <p className="text-xs text-neutral-400">
                    {(d.signal * 100).toFixed(0)}% · {(d.confidence * 100).toFixed(0)}% confidence
                  </p>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded bg-neutral-100 dark:bg-neutral-800">
                  <div className="h-full bg-amber-500" style={{ width: `${d.signal * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Assessment */}
      <section className={cardCls}>
        <h2 className="text-sm font-semibold">
          {profile ? "Refresh your profile" : "Take the assessment"}
        </h2>
        <div className="mt-4 space-y-6">
          {questions.map((q) => (
            <fieldset key={q.key}>
              <legend className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
                {q.question}
              </legend>
              <div className="mt-2 space-y-2">
                {q.options.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={optionCls(answers[q.key] === opt.value)}
                    onClick={() =>
                      setAnswers((prev) => ({ ...prev, [q.key]: opt.value }))
                    }
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </fieldset>
          ))}
        </div>
        <div className="mt-6 flex items-center justify-between">
          <p className="text-xs text-neutral-400">
            {answered} of {questions.length} answered
          </p>
          <button
            type="button"
            className={btnCls}
            disabled={busy || answered < 3}
            onClick={submit}
          >
            {busy ? "Building profile…" : "Build my Work DNA profile"}
          </button>
        </div>
      </section>
    </div>
  );
}
