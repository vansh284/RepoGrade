import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  Assignment,
  AssignmentInput,
  GradingComponentInput,
  EnvVarInput,
} from "../api/client";

const emptyForm: AssignmentInput = {
  name: "",
  github_repo_name: "",
  checks_directory: "",
  evaluator_weight: 0.7,
  peer_weight: 0.3,
  grading_components: [],
  environment_variables: [],
};

export default function AssignmentsPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const cid = Number(courseId);

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<AssignmentInput>({ ...emptyForm });

  const load = () => {
    api.assignments.list(cid).then(setAssignments).catch((e) => setError(e.message));
  };

  useEffect(load, [cid]);

  const resetForm = () => {
    setForm({ ...emptyForm, grading_components: [], environment_variables: [] });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    try {
      if (editingId !== null) {
        await api.assignments.update(cid, editingId, form);
      } else {
        await api.assignments.create(cid, form);
      }
      resetForm();
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const startEdit = (a: Assignment) => {
    setForm({
      name: a.name,
      github_repo_name: a.github_repo_name,
      checks_directory: a.checks_directory,
      evaluator_weight: a.evaluator_weight,
      peer_weight: a.peer_weight,
      grading_components: a.grading_components.map(({ name, max_points, weight }) => ({
        name,
        max_points,
        weight,
      })),
      environment_variables: a.environment_variables.map(({ key, value }) => ({
        key,
        value,
      })),
    });
    setEditingId(a.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this assignment?")) return;
    try {
      await api.assignments.delete(cid, id);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const updateField = (field: keyof AssignmentInput, value: string | number) => {
    setForm((f) => ({ ...f, [field]: value }));
  };

  // Grading components helpers
  const addComponent = () => {
    setForm((f) => ({
      ...f,
      grading_components: [...f.grading_components, { name: "", max_points: 0, weight: 0 }],
    }));
  };

  const updateComponent = (idx: number, field: keyof GradingComponentInput, value: string | number) => {
    setForm((f) => ({
      ...f,
      grading_components: f.grading_components.map((gc, i) =>
        i === idx ? { ...gc, [field]: value } : gc
      ),
    }));
  };

  const removeComponent = (idx: number) => {
    setForm((f) => ({
      ...f,
      grading_components: f.grading_components.filter((_, i) => i !== idx),
    }));
  };

  // Env var helpers
  const addEnvVar = () => {
    setForm((f) => ({
      ...f,
      environment_variables: [...f.environment_variables, { key: "", value: "" }],
    }));
  };

  const updateEnvVar = (idx: number, field: keyof EnvVarInput, value: string) => {
    setForm((f) => ({
      ...f,
      environment_variables: f.environment_variables.map((ev, i) =>
        i === idx ? { ...ev, [field]: value } : ev
      ),
    }));
  };

  const removeEnvVar = (idx: number) => {
    setForm((f) => ({
      ...f,
      environment_variables: f.environment_variables.filter((_, i) => i !== idx),
    }));
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/">&larr; Courses</Link>
      </div>
      <h2>Assignments</h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>dismiss</button>
        </div>
      )}

      {!showForm && (
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          style={{ marginBottom: 24 }}
        >
          New Assignment
        </button>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginBottom: 24, border: "1px solid #ddd", padding: 16, borderRadius: 4 }}>
          <h3>{editingId !== null ? "Edit Assignment" : "New Assignment"}</h3>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            <label>
              Name
              <input
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="HW1"
                style={{ width: "100%", display: "block", marginTop: 4 }}
              />
            </label>
            <label>
              GitHub Repo Name
              <input
                value={form.github_repo_name}
                onChange={(e) => updateField("github_repo_name", e.target.value)}
                placeholder="cs201-hw1"
                style={{ width: "100%", display: "block", marginTop: 4 }}
              />
            </label>
            <label>
              Checks Directory
              <input
                value={form.checks_directory}
                onChange={(e) => updateField("checks_directory", e.target.value)}
                placeholder="/path/to/checks"
                style={{ width: "100%", display: "block", marginTop: 4 }}
              />
            </label>
            <div style={{ display: "flex", gap: 12 }}>
              <label style={{ flex: 1 }}>
                Evaluator Weight
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={form.evaluator_weight}
                  onChange={(e) => updateField("evaluator_weight", parseFloat(e.target.value) || 0)}
                  style={{ width: "100%", display: "block", marginTop: 4 }}
                />
              </label>
              <label style={{ flex: 1 }}>
                Peer Weight
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={form.peer_weight}
                  onChange={(e) => updateField("peer_weight", parseFloat(e.target.value) || 0)}
                  style={{ width: "100%", display: "block", marginTop: 4 }}
                />
              </label>
            </div>
          </div>

          {/* Grading Components */}
          <div style={{ marginBottom: 16 }}>
            <h4>Grading Components</h4>
            {form.grading_components.map((gc, idx) => (
              <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "end" }}>
                <label style={{ flex: 2 }}>
                  {idx === 0 && "Name"}
                  <input
                    value={gc.name}
                    onChange={(e) => updateComponent(idx, "name", e.target.value)}
                    placeholder="Component name"
                    style={{ width: "100%", display: "block", marginTop: idx === 0 ? 4 : 0 }}
                  />
                </label>
                <label style={{ flex: 1 }}>
                  {idx === 0 && "Max Points"}
                  <input
                    type="number"
                    value={gc.max_points}
                    onChange={(e) => updateComponent(idx, "max_points", parseInt(e.target.value) || 0)}
                    style={{ width: "100%", display: "block", marginTop: idx === 0 ? 4 : 0 }}
                  />
                </label>
                <label style={{ flex: 1 }}>
                  {idx === 0 && "Weight"}
                  <input
                    type="number"
                    step="0.01"
                    value={gc.weight}
                    onChange={(e) => updateComponent(idx, "weight", parseFloat(e.target.value) || 0)}
                    style={{ width: "100%", display: "block", marginTop: idx === 0 ? 4 : 0 }}
                  />
                </label>
                <button type="button" onClick={() => removeComponent(idx)} style={{ marginTop: idx === 0 ? 18 : 0 }}>
                  Remove
                </button>
              </div>
            ))}
            <button type="button" onClick={addComponent}>Add Component</button>
          </div>

          {/* Environment Variables */}
          <div style={{ marginBottom: 16 }}>
            <h4>Environment Variables</h4>
            {form.environment_variables.map((ev, idx) => (
              <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "end" }}>
                <label style={{ flex: 1 }}>
                  {idx === 0 && "Key"}
                  <input
                    value={ev.key}
                    onChange={(e) => updateEnvVar(idx, "key", e.target.value)}
                    placeholder="KEY"
                    style={{ width: "100%", display: "block", marginTop: idx === 0 ? 4 : 0 }}
                  />
                </label>
                <label style={{ flex: 1 }}>
                  {idx === 0 && "Value"}
                  <input
                    value={ev.value}
                    onChange={(e) => updateEnvVar(idx, "value", e.target.value)}
                    placeholder="value"
                    style={{ width: "100%", display: "block", marginTop: idx === 0 ? 4 : 0 }}
                  />
                </label>
                <button type="button" onClick={() => removeEnvVar(idx)} style={{ marginTop: idx === 0 ? 18 : 0 }}>
                  Remove
                </button>
              </div>
            ))}
            <button type="button" onClick={addEnvVar}>Add Variable</button>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit">{editingId !== null ? "Save" : "Create"}</button>
            <button type="button" onClick={resetForm}>Cancel</button>
          </div>
        </form>
      )}

      {assignments.length === 0 && !showForm ? (
        <p>No assignments yet.</p>
      ) : (
        !showForm && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Name</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Repo</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Components</th>
                <th style={{ textAlign: "right", borderBottom: "1px solid #ccc", padding: 8 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((a) => (
                <tr key={a.id}>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{a.name}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{a.github_repo_name}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                    {a.grading_components.length}
                  </td>
                  <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right" }}>
                    <Link to={`/courses/${cid}/assignments/${a.id}/dashboard`}>
                      <button type="button">Dashboard</button>
                    </Link>
                    <button onClick={() => startEdit(a)} style={{ marginLeft: 4 }}>Edit</button>
                    <button onClick={() => handleDelete(a.id)} style={{ marginLeft: 4 }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  );
}
