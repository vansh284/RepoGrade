import { useEffect, useState } from "react";
import { api, Course } from "../api/client";

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    api.courses.list().then(setCourses).catch((e) => setError(e.message));
  };

  useEffect(load, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.courses.create(name.trim());
      setName("");
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdate = async (id: number) => {
    if (!editName.trim()) return;
    try {
      await api.courses.update(id, editName.trim());
      setEditingId(null);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this course?")) return;
    try {
      await api.courses.delete(id);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h2>Courses</h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      <form onSubmit={handleCreate} style={{ marginBottom: 24 }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Course name (e.g. CS201 Fall 2026)"
          style={{ width: 300, marginRight: 8 }}
        />
        <button type="submit">Create Course</button>
      </form>

      {courses.length === 0 ? (
        <p>No courses yet. Create one above.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Name</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ccc", padding: 8 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {courses.map((c) => (
              <tr key={c.id}>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                  {editingId === c.id ? (
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleUpdate(c.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      autoFocus
                    />
                  ) : (
                    c.name
                  )}
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right" }}>
                  {editingId === c.id ? (
                    <>
                      <button onClick={() => handleUpdate(c.id)}>Save</button>
                      <button onClick={() => setEditingId(null)} style={{ marginLeft: 4 }}>
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditingId(c.id);
                          setEditName(c.name);
                        }}
                      >
                        Edit
                      </button>
                      <button onClick={() => handleDelete(c.id)} style={{ marginLeft: 4 }}>
                        Delete
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
