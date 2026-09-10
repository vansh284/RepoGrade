import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { Student, ImportResult } from "../api/client";

type StudentForm = {
  name: string;
  student_id: string;
  email: string;
  github_username: string;
};

const emptyForm: StudentForm = { name: "", student_id: "", email: "", github_username: "" };

export default function StudentsPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const cid = Number(courseId);

  const [students, setStudents] = useState<Student[]>([]);
  const [courseName, setCourseName] = useState("");
  const [form, setForm] = useState<StudentForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<StudentForm>(emptyForm);
  const [error, setError] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => {
    api.students.list(cid).then(setStudents).catch((e) => setError(e.message));
  };

  useEffect(() => {
    api.courses.get(cid).then((c) => setCourseName(c.name)).catch((e) => setError(e.message));
    load();
  }, [cid]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.student_id.trim()) return;
    try {
      await api.students.create(cid, {
        name: form.name.trim(),
        student_id: form.student_id.trim(),
        email: form.email.trim(),
        github_username: form.github_username.trim(),
      });
      setForm(emptyForm);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdate = async (id: number) => {
    if (!editForm.name.trim() || !editForm.student_id.trim()) return;
    try {
      await api.students.update(cid, id, {
        name: editForm.name.trim(),
        student_id: editForm.student_id.trim(),
        email: editForm.email.trim(),
        github_username: editForm.github_username.trim(),
      });
      setEditingId(null);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Remove this student?")) return;
    try {
      await api.students.delete(cid, id);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await api.students.import(cid, file);
      setImportResult(result);
      load();
    } catch (err: any) {
      setError(err.message);
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const startEdit = (s: Student) => {
    setEditingId(s.id);
    setEditForm({
      name: s.name,
      student_id: s.student_id,
      email: s.email,
      github_username: s.github_username,
    });
  };

  return (
    <div>
      <Link to="/" style={{ textDecoration: "none", color: "#666", fontSize: 13 }}>
        &larr; Courses
      </Link>
      <h2 style={{ marginTop: 8 }}>{courseName} — Students</h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>dismiss</button>
        </div>
      )}

      {importResult && (
        <div style={{ marginBottom: 16, padding: 12, background: "#f0f7ff", borderRadius: 4 }}>
          <strong>Import:</strong> {importResult.imported} added
          {importResult.errors.length > 0 && (
            <span>, {importResult.errors.length} error(s)</span>
          )}
          {importResult.errors.map((err, i) => (
            <div key={i} style={{ color: "red", fontSize: 13 }}>
              Row {err.row}: {err.error}
            </div>
          ))}
          <button onClick={() => setImportResult(null)} style={{ marginTop: 4 }}>dismiss</button>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <button onClick={() => fileRef.current?.click()}>Import CSV</button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={handleImport}
          style={{ display: "none" }}
        />
        <a href={api.students.exportUrl(cid)} download>
          <button type="button">Export CSV</button>
        </a>
      </div>

      <form onSubmit={handleCreate} style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Name"
          style={{ width: 160 }}
        />
        <input
          value={form.student_id}
          onChange={(e) => setForm({ ...form, student_id: e.target.value })}
          placeholder="Student ID"
          style={{ width: 120 }}
        />
        <input
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          placeholder="Email"
          style={{ width: 200 }}
        />
        <input
          value={form.github_username}
          onChange={(e) => setForm({ ...form, github_username: e.target.value })}
          placeholder="GitHub Username"
          style={{ width: 160 }}
        />
        <button type="submit">Add Student</button>
      </form>

      {students.length === 0 ? (
        <p>No students yet. Add one above or import a CSV.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Name", "Student ID", "Email", "GitHub Username", "Actions"].map((h) => (
                  <th key={h} style={{ textAlign: h === "Actions" ? "right" : "left", borderBottom: "1px solid #ccc", padding: 8 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id}>
                  {editingId === s.id ? (
                    <>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                        <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} style={{ width: "100%" }} />
                      </td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                        <input value={editForm.student_id} onChange={(e) => setEditForm({ ...editForm, student_id: e.target.value })} style={{ width: "100%" }} />
                      </td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                        <input value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} style={{ width: "100%" }} />
                      </td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                        <input value={editForm.github_username} onChange={(e) => setEditForm({ ...editForm, github_username: e.target.value })} style={{ width: "100%" }} />
                      </td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right", whiteSpace: "nowrap" }}>
                        <button onClick={() => handleUpdate(s.id)}>Save</button>
                        <button onClick={() => setEditingId(null)} style={{ marginLeft: 4 }}>Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.name}</td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.student_id}</td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.email}</td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.github_username}</td>
                      <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right", whiteSpace: "nowrap" }}>
                        <button onClick={() => startEdit(s)}>Edit</button>
                        <button onClick={() => handleDelete(s.id)} style={{ marginLeft: 4 }}>Delete</button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
