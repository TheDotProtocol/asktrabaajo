"use client";
/**
 * AI Interview (candidate side) — secure session entry + consent + live
 * question flow. The entry token is never stored client-side after entry;
 * every request carries it as X-Interview-Token and the backend re-validates
 * the SHA-256 hash plus person ownership on every call.
 *
 * No facial/emotion analysis, no lie detection, no recording. Voice/video
 * controls only appear when the session media profile enables them.
 */
import { FormEvent, useCallback, useState } from "react";

import { btnCls, cardCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  AiInterviewCandidateFeedback,
  AiInterviewQuestionOut,
  AiInterviewResponseOut,
  AiInterviewSessionView,
  AiInterviewStartOut,
} from "@/lib/api/types";

const ghostCls =
  "rounded border border-neutral-300 px-4 py-2 text-sm hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800";

type Stage =
  | "lobby"
  | "consent"
  | "in_progress"
  | "paused"
  | "completed"
  | "error";

export default function AiInterviewPage() {
  const [token, setToken] = useState("");
  const [session, setSession] = useState<AiInterviewSessionView | null>(null);
  const [stage, setStage] = useState<Stage>("lobby");
  const [intro, setIntro] = useState<AiInterviewStartOut | null>(null);
  const [question, setQuestion] = useState<AiInterviewQuestionOut | null>(null);
  const [answer, setAnswer] = useState("");
  const [lastEval, setLastEval] = useState<AiInterviewResponseOut | null>(null);
  const [feedback, setFeedback] = useState<AiInterviewCandidateFeedback | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [micConsent, setMicConsent] = useState(false);
  const [cameraConsent, setCameraConsent] = useState(false);
  const [answered, setAnswered] = useState(0);

  const hdrs = useCallback(
    () => ({ "X-Interview-Token": token }),
    [token]
  );

  const enter = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const view = await api.post<AiInterviewSessionView>("/ai-interviews/claim", {
        entry_token: token,
      });
      setSession(view);
      if (view.status === "consent_required" || view.status === "ready") {
        setStage("consent");
      } else if (view.status === "expired" || view.status === "completed" || view.status === "cancelled") {
        setStage("completed");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const grantConsent = async () => {
    setBusy(true);
    try {
      await api.post(
        `/ai-interviews/${session?.session_id}/consent`,
        { mic: micConsent, camera: cameraConsent, recording: false },
        hdrs()
      );
      setNotice(
        "Consent recorded. This interview is text-first; no recording is made."
      );
      await startInterview();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const startInterview = async () => {
    const s = await api.post<AiInterviewStartOut>(
      `/ai-interviews/${session?.session_id}/start`,
      undefined,
      hdrs()
    );
    setIntro(s);
    setStage("in_progress");
    setAnswered(0);
    await fetchQuestion();
  };

  const fetchQuestion = async () => {
    const q = await api.get<AiInterviewQuestionOut | AiInterviewResponseOut>(
      `/ai-interviews/${session?.session_id}/next-question`,
      hdrs()
    );
    if ("question_id" in q) {
      setQuestion(q as AiInterviewQuestionOut);
    } else {
      handleDone(q as AiInterviewResponseOut);
    }
  };

  const handleDone = async (out?: AiInterviewResponseOut) => {
    setQuestion(null);
    setStage("completed");
    try {
      const fb = await api.get<AiInterviewCandidateFeedback>(
        `/ai-interviews/${session?.session_id}/feedback`,
        hdrs()
      );
      setFeedback(fb);
    } catch {
      // feedback appears once the report exists
    }
    if (out?.note) setNotice(out.note);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!question) return;
    setBusy(true);
    setError("");
    try {
      const out = await api.post<AiInterviewResponseOut>(
        `/ai-interviews/${session?.session_id}/responses`,
        { question_id: question.question_id, answer },
        hdrs()
      );
      setLastEval(out);
      setAnswered((n) => n + 1);
      setAnswer("");
      if (out.next) {
        setQuestion(out.next);
      } else {
        await handleDone(out);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const repeat = async () => {
    if (!question) return;
    try {
      const q = await api.post<AiInterviewQuestionOut>(
        `/ai-interviews/${session?.session_id}/repeat`,
        { question_id: question.question_id },
        hdrs()
      );
      setQuestion(q);
      setNotice("Question repeated — this never counts against you.");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const pauseFlow = async () => {
    try {
      await api.post(`/ai-interviews/${session?.session_id}/pause`, undefined, hdrs());
      setStage("paused");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const resumeFlow = async () => {
    setStage("in_progress");
    await fetchQuestion();
  };

  const complete = async () => {
    try {
      const out = await api.post<AiInterviewResponseOut>(
        `/ai-interviews/${session?.session_id}/complete`,
        undefined,
        hdrs()
      );
      await handleDone(out);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const withdraw = async () => {
    try {
      await api.post(
        `/ai-interviews/${session?.session_id}/consent/withdraw`,
        undefined,
        hdrs()
      );
      setNotice("Consent withdrawn — the interview has been stopped.");
      setStage("completed");
      setQuestion(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold">AI Interview</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          An Athena-conducted structured interview. It is not a human
          interviewer, it does not record you by default, and it never makes a
          hiring decision — an authorized human reviews the report.
        </p>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          {notice}
        </div>
      )}

      {stage === "lobby" && (
        <form onSubmit={enter} className={`${cardCls} space-y-3`}>
          <p className="text-sm text-neutral-500">
            Enter the interview token your invitation provided to begin.
          </p>
          <input
            className={inputCls}
            placeholder="Interview token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button className={btnCls} disabled={busy || token.length < 8}>
            {busy ? "Checking…" : "Enter interview"}
          </button>
        </form>
      )}

      {stage === "consent" && session && (
        <div className={`${cardCls} space-y-4`}>
          <h2 className="font-medium">
            {session.opportunity_title ?? "AI Interview"} —{" "}
            {session.company_name ?? "the employer"}
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            About {session.duration_minutes} minutes · up to{" "}
            {session.question_count} questions · language {session.language}.
            Answers are evaluated on job-relevant dimensions only. No
            recording is made.
          </p>
          {session.voice_enabled && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={micConsent}
                onChange={(e) => setMicConsent(e.target.checked)}
              />{" "}
              I consent to microphone use for voice answers
            </label>
          )}
          {session.video_enabled && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={cameraConsent}
                onChange={(e) => setCameraConsent(e.target.checked)}
              />{" "}
              I consent to camera use for this interview
            </label>
          )}
          <div className="flex gap-2">
            <button
              className={btnCls}
              onClick={grantConsent}
              disabled={busy || (session.voice_enabled && !micConsent)}
            >
              I consent — start the interview
            </button>
            <button className={ghostCls} onClick={withdraw}>
              Decline and stop
            </button>
          </div>
        </div>
      )}

      {stage === "in_progress" && session && intro && (
        <div className="space-y-4">
          {question ? (
            <>
              <div className={`${cardCls} space-y-3`}>
                <div className="flex items-center justify-between text-xs text-neutral-500">
                  <span>
                    {question.category.replace("_", " ")} · {question.competency}
                  </span>
                  <span>
                    {question.is_follow_up ? "Follow-up" : "Question"} · answered{" "}
                    {answered}
                  </span>
                </div>
                <p className="text-lg">{question.question}</p>
                {question.reason && (
                  <p className="text-xs text-neutral-500">{question.reason}</p>
                )}
                <form onSubmit={submit} className="space-y-2">
                  <textarea
                    className={inputCls}
                    rows={4}
                    placeholder="Type your answer…"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button
                      className={btnCls}
                      disabled={busy || answer.trim().length < 2}
                    >
                      {busy ? "Evaluating…" : "Submit answer"}
                    </button>
                    <button
                      type="button"
                      className={ghostCls}
                      onClick={repeat}
                      disabled={busy}
                    >
                      Repeat question
                    </button>
                    <button
                      type="button"
                      className={ghostCls}
                      onClick={pauseFlow}
                      disabled={busy}
                    >
                      Pause
                    </button>
                    <button
                      type="button"
                      className={ghostCls}
                      onClick={complete}
                      disabled={busy}
                    >
                      Finish early
                    </button>
                  </div>
                </form>
              </div>
              {lastEval?.evaluation && (
                <div className={`${cardCls} space-y-2 text-sm`}>
                  <h3 className="font-medium">Feedback on your last answer</h3>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {Object.entries(lastEval.evaluation.dimensions).map(
                      ([dim, d]) => (
                        <div key={dim} className="rounded bg-neutral-50 p-2 dark:bg-neutral-800">
                          <div className="flex justify-between text-xs">
                            <span>{dim}</span>
                            <span className="font-medium">{d.score}/5</span>
                          </div>
                          <p className="mt-1 text-xs text-neutral-500">
                            {d.explanation}
                          </p>
                        </div>
                      )
                    )}
                  </div>
                  <p className="text-xs text-neutral-400">
                    {lastEval.evaluation.disclaimer}
                  </p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-neutral-500">Loading…</p>
          )}
        </div>
      )}

      {stage === "paused" && (
        <div className={`${cardCls} space-y-3`}>
          <h2 className="font-medium">Interview paused</h2>
          <p className="text-sm text-neutral-500">
            The interview clock keeps running against the configured duration.
          </p>
          <button className={btnCls} onClick={resumeFlow}>
            Resume
          </button>
        </div>
      )}

      {stage === "completed" && feedback && (
        <div className={`${cardCls} space-y-3`}>
          <h2 className="font-medium">Interview complete</h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            {feedback.note}
          </p>
          {feedback.strengths.length > 0 && (
            <ul className="list-inside list-disc text-sm">
              {feedback.strengths.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          )}
          {feedback.preparation_areas.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">Preparation areas</h3>
              <ul className="list-inside list-disc text-sm text-neutral-600 dark:text-neutral-300">
                {feedback.preparation_areas.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-neutral-400">
            An authorized human reviewer will follow up about next steps.
          </p>
        </div>
      )}
    </div>
  );
}
