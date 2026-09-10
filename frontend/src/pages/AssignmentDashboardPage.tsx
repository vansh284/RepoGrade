import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { DashboardRow, CloneProgress } from "../api/client";

type SortField = "student_name" | "github_username" | "clone_status";

export default function AssignmentDashboardPage() {
  const { courseId, assignmentId } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [rows, setRows] = useState<DashboardRow[]>([]);
  const [error, setError] = useState("");
  const [cloning, setCloning] = useState(false);
  const [progress, setProgress] = useState<CloneProgress | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("student_name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [assignmentName, setAssignmentName] = useState("");

  const load = () => {
    api.submissions
      .dashboard(cid, aid, {
        status: statusFilter || undefined,
        search: search || undefined,
        sort: sortField,
        order: sortOrder,
      })
      .then(setRows)
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    api.assignments
      .get(cid, aid)
      .then((a) => setAssignmentName(a.name))
      .catch(() => {});
    load();
  }, [cid, aid, statusFilter, sortField, sortOrder]);

  const handleClone = async () => {
    setCloning(true);
    setProgress(null);
    try {
      const result = await api.submissions.clone(cid, aid);
      setProgress(result);
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCloning(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const sortIndicator = (field: SortField) => {
    if (sortField !== field) return "";
    return sortOrder === "asc" ? " ▲" : " ▼";
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "cloned":
        return "#2e7d32";
      case "missing":
        return "#c62828";
      case "error":
        return "#e65100";
      default:
        return "#757575";
    }
  };

  return (
    <div>
      <Link
        to={`/courses/${cid}/assignments`}
        style={{ textDecoration: "none", color: "#666", fontSize: 13 }}
      >
        &larr; Assignments
      </Link>
      <h2 style={{ marginTop: 8 }}>
        {assignmentName || "Assignment"} — Dashboard
      </h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 16,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <button onClick={handleClone} disabled={cloning}>
          {cloning ? "Cloning..." : "Clone All Repos"}
        </button>

        {progress && (
          <span style={{ fontSize: 13 }}>
            {progress.completed}/{progress.total} cloned
            {progress.failed > 0 && (
              <span style={{ color: "#c62828" }}>
                , {progress.failed} failed
              </span>
            )}
          </span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 16,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <form
          onSubmit={handleSearch}
          style={{ display: "flex", gap: 8 }}
        >
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or GitHub..."
            style={{ width: 220 }}
          />
          <button type="submit">Search</button>
        </form>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="cloned">Cloned</option>
          <option value="missing">Missing</option>
          <option value="error">Error</option>
        </select>
      </div>

      {rows.length === 0 ? (
        <p>No students to display.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th
                  onClick={() => toggleSort("student_name")}
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  Student Name{sortIndicator("student_name")}
                </th>
                <th
                  onClick={() => toggleSort("github_username")}
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  GitHub Username{sortIndicator("github_username")}
                </th>
                <th
                  onClick={() => toggleSort("clone_status")}
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  Repo Status{sortIndicator("clone_status")}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.student_db_id}
                  style={{ cursor: "pointer" }}
                  title="Click for student detail (coming soon)"
                >
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    {row.student_name}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    {row.github_username}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      borderBottom: "1px solid #eee",
                      color: statusColor(row.clone_status),
                      fontWeight: 500,
                    }}
                  >
                    {row.clone_status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
