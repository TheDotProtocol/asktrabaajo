"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { DocumentRequestRow, PersonDocumentOut } from "@/lib/api/types";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<PersonDocumentOut[] | null>(null);
  const [requests, setRequests] = useState<DocumentRequestRow[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("resume");

  const load = useCallback(async () => {
    try {
      setDocs(await api.get<PersonDocumentOut[]>("/documents"));
      setRequests(await api.get<DocumentRequestRow[]>("/jobseeker/document-requests"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createDoc(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/documents", { name, doc_type: docType });
      setNotice("Document record created. File bytes stay in controlled storage — employers see nothing until you grant access.");
      setName("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Remove this document from your Work ID?")) return;
    try {
      await api.delete(`/documents/${id}`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function decideRequest(id: string, action: "approve" | "decline") {
    try {
      await api.post(`/jobseeker/document-requests/${id}/${action}`);
      setNotice(`Request ${action}d.`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (error && !docs) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!docs) return <LoadingState />;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Controlled disclosure"
        title="Documents"
        subtitle="You own every file. Companies only receive a document after you approve a request or create a grant. Nothing is shared automatically."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}

      <form onSubmit={createDoc} className={`${cardCls} grid gap-3 sm:grid-cols-3`}>
        <input className={inputCls} placeholder="Document name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className={inputCls} placeholder="Type (resume, certificate…)" value={docType} onChange={(e) => setDocType(e.target.value)} required />
        <button className={btnCls} type="submit">Register document</button>
      </form>

      {docs.length === 0 ? (
        <EmptyState
          title="No documents yet"
          body="Register a document record when you are ready. Employers cannot browse your files."
        />
      ) : (
        <ul className="space-y-3">
          {docs.map((doc) => (
            <li key={doc.id} className={`${cardCls} flex flex-wrap items-center justify-between gap-3`}>
              <div>
                <p className="font-medium">{doc.name}</p>
                <p className="text-xs text-[#9ca3af]">{doc.doc_type}</p>
              </div>
              <div className="flex items-center gap-3">
                <StatusPill status={doc.verification_status} />
                <button type="button" className={ghostBtnCls} onClick={() => void remove(doc.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold">Employer requests</h2>
        {requests.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No pending disclosure requests.</p>
        ) : (
          <ul className="space-y-3">
            {requests.map((req) => (
              <li key={req.id} className={`${cardCls} flex flex-wrap items-center justify-between gap-3`}>
                <div>
                  <p className="text-sm">{req.document_type ?? "Document"}</p>
                  <p className="text-xs text-[#9ca3af]">{req.status}</p>
                </div>
                {req.status === "pending" && (
                  <div className="flex gap-2">
                    <button type="button" className={btnCls} onClick={() => void decideRequest(req.id, "approve")}>
                      Approve
                    </button>
                    <button type="button" className={ghostBtnCls} onClick={() => void decideRequest(req.id, "decline")}>
                      Decline
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
