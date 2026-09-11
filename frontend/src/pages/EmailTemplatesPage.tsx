import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { EmailTemplate, EmailTemplateInput, Student, EmailPreview, BatchSendResult, DashboardRow } from "../api/client";

export default function EmailTemplatesPage() {
  const { courseId, assignmentId } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [dashboardRows, setDashboardRows] = useState<DashboardRow[]>([]);
  const [error, setError] = useState("");
  const [assignmentName, setAssignmentName] = useState("");

  // Form state
  const [editId, setEditId] = useState<number | null>(null);
  const [formName, setFormName] = useState("");
  const [formSubject, setFormSubject] = useState("");
  const [formBody, setFormBody] = useState("");

  // Preview state
  const [previewTemplateId, setPreviewTemplateId] = useState<number | null>(null);
  const [previewStudentId, setPreviewStudentId] = useState<number | null>(null);
  const [preview, setPreview] = useState<EmailPreview | null>(null);

  // Batch send state
  const [sendTemplateId, setSendTemplateId] = useState<number | null>(null);
  const [sendCheckName, setSendCheckName] = useState("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<BatchSendResult | null>(null);
  const [confirmSend, setConfirmSend] = useState(false);

  const load = () => {
    api.emailTemplates.list(cid, aid).then(setTemplates).catch((e) => setError(e.message));
    api.students.list(cid).then(setStudents).catch(() => {});
    api.submissions.dashboard(cid, aid).then(setDashboardRows).catch(() => {});
  };

  useEffect(() => {
    api.assignments.get(cid, aid).then((a) => setAssignmentName(a.name)).catch(() => {});
    load();
  }, [cid, aid]);

  const resetForm = () => {
    setEditId(null);
    setFormName("");
    setFormSubject("");
    setFormBody("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data: EmailTemplateInput = {
      name: formName,
      subject_template: formSubject,
      body_template: formBody,
    };
    try {
      if (editId) {
        await api.emailTemplates.update(cid, aid, editId, data);
      } else {
        await api.emailTemplates.create(cid, aid, data);
      }
      resetForm();
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEdit = (t: EmailTemplate) => {
    setEditId(t.id);
    setFormName(t.name);
    setFormSubject(t.subject_template);
    setFormBody(t.body_template);
  };

  const handleDelete = async (id: number) => {
    try {
      await api.emailTemplates.delete(cid, aid, id);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handlePreview = async () => {
    if (!previewTemplateId || !previewStudentId) return;
    try {
      const result = await api.emailTemplates.preview(cid, aid, previewTemplateId, previewStudentId);
      setPreview(result);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSend = async () => {
    if (!sendTemplateId || !sendCheckName) return;
    setSending(true);
    setSendResult(null);
    try {
      const result = await api.emailTemplates.send(cid, aid, sendTemplateId, sendCheckName);
      setSendResult(result);
      setConfirmSend(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  // Gather unique check names from dashboard data
  const checkNames = new Set<string>();
  for (const row of dashboardRows) {
    for (const cr of row.check_results) {
      checkNames.add(cr.check_name);
    }
  }
  const sortedCheckNames = Array.from(checkNames).sort();

  // Count failures for the selected check
  const failedCount = sendCheckName
    ? dashboardRows.filter((row) =>
        row.check_results.some((cr) => cr.check_name === sendCheckName && !cr.passed)
      ).length
    : 0;

  return (
    <div>
      <Link
        to={`/courses/${cid}/assignments/${aid}/dashboard`}
        style={{ textDecoration: "none", color: "#666", fontSize: 13 }}
      >
        &larr; Dashboard
      </Link>
      <h2 style={{ marginTop: 8 }}>
        {assignmentName || "Assignment"} — Email Templates
      </h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>dismiss</button>
        </div>
      )}

      {/* Template Form */}
      <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>{editId ? "Edit Template" : "New Template"}</h3>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: 4 }}>Name (problem type)</label>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="e.g. Lint failure, Test failure"
              style={{ width: "100%", maxWidth: 400 }}
              required
            />
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: 4 }}>Subject Template</label>
            <input
              value={formSubject}
              onChange={(e) => setFormSubject(e.target.value)}
              placeholder="e.g. {assignment_name}: {check_name} feedback"
              style={{ width: "100%", maxWidth: 600 }}
              required
            />
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: 4 }}>Body Template</label>
            <textarea
              value={formBody}
              onChange={(e) => setFormBody(e.target.value)}
              placeholder="Hi {student_name}, your check {check_name} failed..."
              rows={6}
              style={{ width: "100%", maxWidth: 600 }}
              required
            />
          </div>
          <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
            Placeholders: {"{student_name}"}, {"{student_id}"}, {"{student_email}"}, {"{github_username}"}, {"{repo_url}"}, {"{assignment_name}"}, {"{course_name}"}, {"{check_name}"}, {"{check_message}"}, {"{check_details}"}
          </div>
          <button type="submit">{editId ? "Update" : "Create"}</button>
          {editId && (
            <button type="button" onClick={resetForm} style={{ marginLeft: 8 }}>Cancel</button>
          )}
        </form>
      </div>

      {/* Templates List */}
      {templates.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h3>Templates</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Name</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Subject</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id}>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{t.name}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee", fontSize: 13, color: "#555" }}>
                    {t.subject_template}
                  </td>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                    <button onClick={() => handleEdit(t)} style={{ marginRight: 8 }}>Edit</button>
                    <button onClick={() => handleDelete(t.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview Section */}
      {templates.length > 0 && students.length > 0 && (
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Preview Email</h3>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
            <select
              value={previewTemplateId ?? ""}
              onChange={(e) => { setPreviewTemplateId(Number(e.target.value) || null); setPreview(null); }}
            >
              <option value="">Select template...</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <select
              value={previewStudentId ?? ""}
              onChange={(e) => { setPreviewStudentId(Number(e.target.value) || null); setPreview(null); }}
            >
              <option value="">Select student...</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.student_id})</option>
              ))}
            </select>
            <button onClick={handlePreview} disabled={!previewTemplateId || !previewStudentId}>
              Preview
            </button>
          </div>
          {preview && (
            <div style={{ background: "#f9f9f9", padding: 12, borderRadius: 4 }}>
              <div style={{ marginBottom: 8 }}>
                <strong>Subject:</strong> {preview.subject}
              </div>
              <div style={{ whiteSpace: "pre-wrap" }}>
                <strong>Body:</strong>
                <div style={{ marginTop: 4 }}>{preview.body}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Batch Send Section */}
      {templates.length > 0 && sortedCheckNames.length > 0 && (
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Batch Send Emails</h3>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
            <div>
              <label style={{ display: "block", fontWeight: 500, marginBottom: 4, fontSize: 13 }}>Failed Check</label>
              <select
                value={sendCheckName}
                onChange={(e) => { setSendCheckName(e.target.value); setSendResult(null); setConfirmSend(false); }}
              >
                <option value="">Select check...</option>
                {sortedCheckNames.map((cn) => (
                  <option key={cn} value={cn}>{cn}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontWeight: 500, marginBottom: 4, fontSize: 13 }}>Template</label>
              <select
                value={sendTemplateId ?? ""}
                onChange={(e) => { setSendTemplateId(Number(e.target.value) || null); setSendResult(null); setConfirmSend(false); }}
              >
                <option value="">Select template...</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>

          {sendCheckName && sendTemplateId && (
            <div style={{ marginBottom: 12 }}>
              <p style={{ fontSize: 13, margin: "0 0 8px 0" }}>
                {failedCount} student(s) failed the "{sendCheckName}" check and will receive an email.
              </p>
              {!confirmSend ? (
                <button onClick={() => setConfirmSend(true)} disabled={failedCount === 0}>
                  Send Emails
                </button>
              ) : (
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{ color: "#c62828", fontWeight: 500 }}>
                    Confirm sending {failedCount} email(s)?
                  </span>
                  <button onClick={handleSend} disabled={sending}>
                    {sending ? "Sending..." : "Confirm Send"}
                  </button>
                  <button onClick={() => setConfirmSend(false)}>Cancel</button>
                </div>
              )}
            </div>
          )}

          {sendResult && (
            <div style={{
              padding: 12,
              borderRadius: 4,
              background: sendResult.failed > 0 ? "#fff3e0" : "#e8f5e9",
              marginTop: 8,
            }}>
              <div>Sent: {sendResult.sent}, Failed: {sendResult.failed}</div>
              {sendResult.errors.length > 0 && (
                <ul style={{ margin: "8px 0 0 0", paddingLeft: 20, fontSize: 13 }}>
                  {sendResult.errors.map((err, i) => (
                    <li key={i} style={{ color: "#c62828" }}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
