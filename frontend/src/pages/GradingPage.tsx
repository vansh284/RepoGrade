import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  Assignment,
  DashboardRow,
  EvaluatorGradeOut,
  GradingComponent,
} from "../api/client";

export default function GradingPage() {
  const { courseId, assignmentId, studentId } = useParams<{
    courseId: string;
    assignmentId: string;
    studentId: string;
  }>();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const sid = Number(studentId);
  const navigate = useNavigate();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [rows, setRows] = useState<DashboardRow[]>([]);
  const [grades, setGrades] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const currentIndex = rows.findIndex((r) => r.student_db_id === sid);
  const currentRow = currentIndex >= 0 ? rows[currentIndex] : null;

  useEffect(() => {
    api.assignments.get(cid, aid).then(setAssignment).catch(() => {});
    api.submissions
      .dashboard(cid, aid, { sort: "student_name", order: "asc" })
      .then(setRows)
      .catch(() => {});
  }, [cid, aid]);

  useEffect(() => {
    api.grades
      .get(cid, aid, sid)
      .then((existing: EvaluatorGradeOut[]) => {
        const map: Record<number, string> = {};
        for (const g of existing) {
          map[g.grading_component_id] = String(g.score);
        }
        setGrades(map);
      })
      .catch(() => setGrades({}));
    setSaved(false);
  }, [cid, aid, sid]);

  const handleSave = async () => {
    if (!assignment) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const gradeInputs = assignment.grading_components
        .filter((gc: GradingComponent) => grades[gc.id] !== undefined && grades[gc.id] !== "")
        .map((gc: GradingComponent) => ({
          grading_component_id: gc.id,
          score: parseFloat(grades[gc.id]),
        }));
      await api.grades.submit(cid, aid, sid, gradeInputs);
      setSaved(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const goTo = (index: number) => {
    if (index >= 0 && index < rows.length) {
      navigate(
        `/courses/${cid}/assignments/${aid}/grade/${rows[index].student_db_id}`,
      );
    }
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
        Grade: {currentRow?.student_name ?? "Student"}
      </h2>

      {error && (
        <div style={{ color: "red", marginBottom: 12 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      {currentRow && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ margin: "4px 0" }}>
            <strong>GitHub:</strong>{" "}
            <a
              href={currentRow.repo_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {currentRow.repo_url}
            </a>
          </p>
          <p style={{ margin: "4px 0" }}>
            <strong>Clone Status:</strong>{" "}
            <span
              style={{
                color:
                  currentRow.clone_status === "cloned"
                    ? "#2e7d32"
                    : currentRow.clone_status === "missing"
                      ? "#c62828"
                      : "#757575",
                fontWeight: 500,
              }}
            >
              {currentRow.clone_status}
            </span>
          </p>
        </div>
      )}

      {assignment && assignment.grading_components.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Scores</h3>
          <table style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: 8,
                    borderBottom: "1px solid #ccc",
                  }}
                >
                  Component
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: 8,
                    borderBottom: "1px solid #ccc",
                  }}
                >
                  Max Points
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: 8,
                    borderBottom: "1px solid #ccc",
                  }}
                >
                  Score
                </th>
              </tr>
            </thead>
            <tbody>
              {assignment.grading_components.map((gc: GradingComponent) => (
                <tr key={gc.id}>
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    {gc.name}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    {gc.max_points}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max={gc.max_points}
                      value={grades[gc.id] ?? ""}
                      onChange={(e) =>
                        setGrades((prev) => ({
                          ...prev,
                          [gc.id]: e.target.value,
                        }))
                      }
                      style={{ width: 80 }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Grades"}
        </button>
        {saved && (
          <span style={{ color: "#2e7d32", fontWeight: 500 }}>Saved</span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          marginTop: 24,
          alignItems: "center",
        }}
      >
        <button
          onClick={() => goTo(currentIndex - 1)}
          disabled={currentIndex <= 0}
        >
          Previous Student
        </button>
        <span style={{ fontSize: 13, color: "#666" }}>
          {currentIndex >= 0
            ? `${currentIndex + 1} of ${rows.length}`
            : ""}
        </span>
        <button
          onClick={() => goTo(currentIndex + 1)}
          disabled={currentIndex < 0 || currentIndex >= rows.length - 1}
        >
          Next Student
        </button>
      </div>
    </div>
  );
}
