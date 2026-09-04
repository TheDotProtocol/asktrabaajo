"use client";
/**
 * Interview Prep — text mock-interview practice over the candidate's own
 * prep sessions. Deterministic question generation from the posted role
 * (or the candidate's skills) and explainable answer feedback. Answers
 * are never persisted by the API; sessions are metadata containers the
 * candidate owns, completes, or deletes.
 */
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { api, getAccessToken } from "@/lib/api/session";
import {
  AnswerEvaluation,
  PrepQuestion,
  PrepSession,
} from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const inputCls =
  "w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-xs font-medium hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800";
const labelCls = "text-xs uppercase tracking-wide text-neutral-400";

const categoryColor: Record<string, string> = {
  technical: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  behavioral: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  competency: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
  role_specific: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  situational: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
  career_history: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
};

export default function InterviewPrepPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<PrepSession[]>([]);
  const [active, setActive] = useState<PrepSession | null>(null);
  const [focus, setFocus] = useState("");
  const [questions, setQuestions] = useState<PrepQuestion[]>([]);
  const [qIndex, setQIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.push("/id");
      return;
    }
    try {
      const rows = await api.get<PrepSession[]>("/interview-prep/sessions");
      setSessions(rows);
      const open = rows.find((s) => s.status === "active") ?? rows[0] ?? null;
      setActive(open);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function createSession(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const focusAreas = focus
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 6);
      const session = await api.post<PrepSession>("/interview-prep/sessions", {
        focus_areas: focusAreas.length ? focusAreas : undefined,
      });
      setSessions([session, ...sessions]);
      setActive(session);
      setFocus("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function startPractice() {
    if (!active) return;
    setError("");
    setEvaluation(null);
    setBusy(true);
    try {
      const qs = await api.post<{ questions: PrepQuestion[] }>(
        `/interview-prep/sessions/${active.id}/questions`,
        { count: 5 }
      );
      setQuestions(qs.questions);
      setQIndex(0);
      setAnswer("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  const question: PrepQuestion | null = questions[qIndex] ?? null;

  async function submitAnswer() {
    if (!active || !question || !answer.trim()) return;
    setError("");
    setBusy(true);
    try {
      const ev = await api.post<AnswerEvaluation>(
        `/interview-prep/sessions/${active.id}/answers`,
        { question: question.question, answer }
      );
      setEvaluation(ev);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function nextQuestion() {
    if (qIndex + 1 < questions.length) {
      setQIndex(qIndex + 1);
      setAnswer("");
      setEvaluation(null);
    } else {
      // practice complete -> mark the session completed
      if (active) {
        try {
          const done = await api.post<PrepSession>(
            `/interview-prep/sessions/${active.id}/complete`,
            {}
          );
          setActive(done);
          setQuestions([]);
          setEvaluation(null);
          setError("Practice complete — great work. Start again or delete when done.");
          load();
        } catch (e) {
          setError(String((e as Error).message ?? e));
        }
      }
    }
  }

  async function removeSession(id: string) {
    setError("");
    try {
      await api.delete(`/interview-prep/sessions/${id}`);
      const rest = sessions.filter((s) => s.id !== id);
      setSessions(rest);
      if (active?.id === id) setActive(rest[0] ?? null);
      setQuestions([]);
      setEvaluation(null);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  const dimOrder = [
    "relevance",
    "structure",
    "evidence",
    "role_knowledge",
    "communication",
    "completeness",
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Interview Prep</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Text mock-interview practice with structured, explainable feedback.
          Your answers are never stored — sessions are containers you own,
          complete, or delete.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
          {error}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Sessions */}
        <div className={`${cardCls} md:col-span-1`}>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Your sessions
          </h2>
          <form onSubmit={createSession} className="mt-3 space-y-2">
            <input
              className={inputCls}
              placeholder="Focus areas (optional, comma-separated)"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
            />
            <button className={`${btnCls} w-full`} disabled={busy}>
              Start a prep session
            </button>
          </form>
          <ul className="mt-4 space-y-2">
            {sessions.length === 0 && (
              <li className="text-sm text-neutral-400">
                No sessions yet — start one above.
              </li>
            )}
            {sessions.map((s) => (
              <li
                key={s.id}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                  active?.id === s.id
                    ? "border-amber-400 bg-amber-50 dark:bg-amber-950/30"
                    : "border-neutral-200 dark:border-neutral-800"
                }`}
              >
                <button
                  className="text-left"
                  onClick={() => {
                    setActive(s);
                    setQuestions([]);
                    setEvaluation(null);
                  }}
                >
                  <div className="font-medium">
                    {s.status === "completed" ? "Completed session" : "Practice session"}
                  </div>
                  <div className={labelCls}>
                    {s.questions_generated} questions · {s.answers_evaluated} answers
                  </div>
                </button>
                <button
                  className={ghostBtn}
                  onClick={() => removeSession(s.id)}
                  aria-label="Delete session"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Practice area */}
        <div className={`${cardCls} md:col-span-2`}>
          {!active && (
            <p className="text-sm text-neutral-400">
              Start a session to begin mock-interview practice.
            </p>
          )}

          {active && questions.length === 0 && !evaluation && (
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
                {active.status === "active" ? "Ready to practice" : "Session complete"}
              </h2>
              <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
                {active.status === "active"
                  ? "Generate five practice questions grounded in the role requirements and your Work ID skills."
                  : "This session is complete. Start a new one to keep practicing."}
              </p>
              {active.status === "active" && (
                <button className={`${btnCls} mt-4`} onClick={startPractice} disabled={busy}>
                  {busy ? "Generating…" : "Generate questions"}
                </button>
              )}
            </div>
          )}

          {question && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${categoryColor[question.category] ?? categoryColor.career_history}`}>
                  {question.category.replace("_", " ")}
                </span>
                <span className="text-xs text-neutral-400">
                  Question {qIndex + 1} of {questions.length} · {question.difficulty}
                </span>
              </div>
              <p className="text-base font-medium">{question.question}</p>
              {question.target_skill && (
                <p className="text-xs text-neutral-500">
                  Target skill: <span className="font-medium">{question.target_skill}</span>
                </p>
              )}
              <textarea
                className={`${inputCls} min-h-32`}
                placeholder="Type your spoken answer here…"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
              <div className="flex gap-2">
                <button className={btnCls} onClick={submitAnswer} disabled={busy || !answer.trim()}>
                  {busy ? "Evaluating…" : "Evaluate my answer"}
                </button>
                {evaluation && (
                  <button className={ghostBtn} onClick={nextQuestion}>
                    {qIndex + 1 < questions.length ? "Next question" : "Complete practice"}
                  </button>
                )}
              </div>
            </div>
          )}

          {evaluation && (
            <div className="mt-6 space-y-4 border-t border-neutral-200 pt-4 dark:border-neutral-800">
              <h3 className="text-sm font-semibold">Feedback</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {dimOrder.map((dim) => {
                  const d = evaluation.dimensions[dim];
                  if (!d) return null;
                  return (
                    <div key={dim}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="capitalize text-neutral-500">
                          {dim.replace("_", " ")}
                        </span>
                        <span className="font-medium">{Math.round(d.score * 100)}%</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded bg-neutral-200 dark:bg-neutral-800">
                        <div
                          className="h-1.5 rounded bg-amber-500"
                          style={{ width: `${d.score * 100}%` }}
                        />
                      </div>
                      <p className="mt-1 text-xs text-neutral-500">{d.explanation}</p>
                    </div>
                  );
                })}
              </div>
              {evaluation.what_you_did_well.length > 0 && (
                <div className="rounded-lg bg-emerald-50 p-3 text-sm dark:bg-emerald-950/30">
                  <span className="font-medium text-emerald-700 dark:text-emerald-300">
                    Did well:
                  </span>{" "}
                  <span className="text-emerald-800 dark:text-emerald-200">
                    {evaluation.what_you_did_well.join(" ")}
                  </span>
                </div>
              )}
              {evaluation.how_to_improve.length > 0 && (
                <div className="rounded-lg bg-neutral-50 p-3 text-sm dark:bg-neutral-900">
                  <span className="font-medium">To improve:</span>{" "}
                  {evaluation.how_to_improve.join(" ")}
                </div>
              )}
              <p className="text-xs text-neutral-400">{evaluation.disclaimer}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
