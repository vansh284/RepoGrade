import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  PeerAssignment,
  BatchSendResult,
  PeerEvalImportResult,
} from "../api/client";

export default function PeerEvaluationsPage() {
  const { courseId, assignmentId } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [assignments, setAssignments] = useState<PeerAssignment[]>([]);
  const [error, setError] = useState("");
  const [assignmentName, setAssignmentName] = useState("");
  const [count, setCount] = useState(2);
  const [generating, setGenerating] = useState(false);

  // Email state
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [confirmSend, setConfirmSend] = useState(false);
  const [sendResult, setSendResult] = useState<BatchSendResult | null>(null);
  const [sending, setSending] = useState(false);

  // Import state
  const fileRef = useRef<HTMLInputElement>(null);
  const [importResult, setImportResult] = useState<PeerEvalImportResult | null>(
    null,
  );

  const load = () => {
    api.peerAssignments
      .list(cid, aid)
      .then(setAssignments)
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    api.assignments
      .get(cid, aid)
      .then((a) => setAssignmentName(a.name))
      .catch(() => {});
    load();
  }, [cid, aid]);

  const handleGenerate = async () => {
    if (
      assignments.length > 0 &&
      !confirm(
        "This will replace existing peer assignments. Continue?",
      )
    ) {
      return;
    }
    setGenerating(true);
    try {
      const result = await api.peerAssignments.generate(cid, aid, count);
      setAssignments(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleSendEmails = async () => {
    setSending(true);
    setSendResult(null);
    try {
      const result = await api.peerAssignments.sendEmails(
        cid,
        aid,
        emailSubject,
        emailBody,
      );
      setSendResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSending(false);
      setConfirmSend(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportResult(null);
    try {
      const result = await api.peerAssignments.importEvaluations(
        cid,
        aid,
        file,
      );
      setImportResult(result);
    } catch (err: any) {
      setError(err.message);
    }
    e.target.value = "";
  };

  return (
    <div>
      <Link
        to={`/courses/${cid}/assignments/${aid}/dashboard`}
        style={{ textDecoration: "none", color: "#666", fontSize: 13 }}
      >
        &larr; Dashboard
      </Link>
      <h2 style={{ marginTop: 8 }}>
        {assignmentName || "Assignment"} — Peer Evaluations
      </h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      {/* ── Generate ────────────────────────────────────────── */}
      <div
        style={{
          border: "1px solid #ddd",
          padding: 16,
          borderRadius: 4,
          marginBottom: 24,
        }}
      >
        <h3 style={{ marginBottom: 12 }}>Generate Peer Assignments</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label>
            Reviews per student:{" "}
            <input
              type="number"
              min={1}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              style={{ width: 60 }}
            />
          </label>
          <button onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : "Generate"}
          </button>
        </div>
      </div>

      {/* ── Peer Assignment Table ───────────────────────────── */}
      {assignments.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h3>Peer Assignment Mapping ({assignments.length})</h3>
            <a href={api.peerAssignments.exportUrl(cid, aid)} download>
              <button type="button">Export CSV</button>
            </a>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th
                    style={{
                      textAlign: "left",
                      borderBottom: "1px solid #ccc",
                      padding: 8,
                    }}
                  >
                    Evaluator
                  </th>
                  <th
                    style={{
                      textAlign: "left",
                      borderBottom: "1px solid #ccc",
                      padding: 8,
                    }}
                  >
                    Evaluee
                  </th>
                  <th
                    style={{
                      textAlign: "left",
                      borderBottom: "1px solid #ccc",
                      padding: 8,
                    }}
                  >
                    Repo URL
                  </th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((pa) => (
                  <tr key={pa.id}>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      {pa.evaluator_name}
                    </td>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      {pa.evaluee_name}
                    </td>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      <a
                        href={pa.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#1a73e8" }}
                      >
                        {pa.repo_url}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Send Notification Emails ────────────────────────── */}
      {assignments.length > 0 && (
        <div
          style={{
            border: "1px solid #ddd",
            padding: 16,
            borderRadius: 4,
            marginBottom: 24,
          }}
        >
          <h3 style={{ marginBottom: 12 }}>Send Notification Emails</h3>
          <p style={{ fontSize: 13, color: "#666", marginBottom: 12 }}>
            Placeholders: {"{student_name}"}, {"{repo_url_1}"},{" "}
            {"{repo_url_2}"}, etc.
          </p>
          <div style={{ marginBottom: 8 }}>
            <input
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              placeholder="Subject"
              style={{ width: "100%" }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <textarea
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              placeholder="Email body..."
              rows={6}
              style={{ width: "100%", fontFamily: "inherit" }}
            />
          </div>
          {!confirmSend ? (
            <button
              onClick={() => setConfirmSend(true)}
              disabled={!emailSubject || !emailBody}
            >
              Send Emails
            </button>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleSendEmails}
                disabled={sending}
                style={{ background: "#c62828", color: "#fff" }}
              >
                {sending ? "Sending..." : "Confirm Send"}
              </button>
              <button onClick={() => setConfirmSend(false)}>Cancel</button>
            </div>
          )}
          {sendResult && (
            <div style={{ marginTop: 12, fontSize: 13 }}>
              Sent: {sendResult.sent}, Failed: {sendResult.failed}
              {sendResult.errors.length > 0 && (
                <ul style={{ color: "#c62828", marginTop: 4 }}>
                  {sendResult.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Import Peer Evaluations ─────────────────────────── */}
      <div
        style={{
          border: "1px solid #ddd",
          padding: 16,
          borderRadius: 4,
          marginBottom: 24,
        }}
      >
        <h3 style={{ marginBottom: 12 }}>Import Peer Evaluations</h3>
        <p style={{ fontSize: 13, color: "#666", marginBottom: 12 }}>
          CSV columns: evaluator_name, evaluee_github, [grading component
          names...], feedback
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={() => fileRef.current?.click()}>
            Import CSV
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            onChange={handleImport}
            style={{ display: "none" }}
          />
          <a
            href={api.peerAssignments.exportEvaluationsUrl(cid, aid)}
            download
          >
            <button type="button">Export Evaluations CSV</button>
          </a>
        </div>
        {importResult && (
          <div style={{ marginTop: 12, fontSize: 13 }}>
            <span style={{ color: "#2e7d32" }}>
              Imported: {importResult.imported}
            </span>
            {importResult.errors.length > 0 && (
              <ul style={{ marginTop: 4 }}>
                {importResult.errors.map((err, i) => (
                  <li
                    key={i}
                    style={{
                      color: err.error.includes("Unrecognized")
                        ? "#e65100"
                        : "#c62828",
                    }}
                  >
                    Row {err.row}: {err.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
