import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { DashboardRow, CloneProgress, CheckProgress } from "../api/client";

type SortField = "student_name" | "github_username" | "clone_status";

export default function AssignmentDashboardPage() {
  const { courseId, assignmentId } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const navigate = useNavigate();

  const [rows, setRows] = useState<DashboardRow[]>([]);
  const [error, setError] = useState("");
  const [cloning, setCloning] = useState(false);
  const [cloneProgress, setCloneProgress] = useState<CloneProgress | null>(null);
  const [runningChecks, setRunningChecks] = useState(false);
  const [checkProgress, setCheckProgress] = useState<CheckProgress | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("student_name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [assignmentName, setAssignmentName] = useState("");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

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
    setCloneProgress(null);
    try {
      const result = await api.submissions.clone(cid, aid);
      setCloneProgress(result);
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCloning(false);
    }
  };

  const handleRunChecks = async () => {
    setRunningChecks(true);
    setCheckProgress(null);
    try {
      const result = await api.checks.run(cid, aid);
      setCheckProgress(result);
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRunningChecks(false);
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

  const checkNames = new Set<string>();
  for (const row of rows) {
    for (const cr of row.check_results) {
      checkNames.add(cr.check_name);
    }
  }
  const sortedCheckNames = Array.from(checkNames).sort();

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

        <button onClick={handleRunChecks} disabled={runningChecks}>
          {runningChecks ? "Running Checks..." : "Run Checks"}
        </button>

        <a href={api.checks.exportUrl(cid, aid)} download>
          <button type="button">Export CSV</button>
        </a>

        <Link to={`/courses/${cid}/assignments/${aid}/emails`}>
          <button type="button">Email Templates</button>
        </Link>

        <Link to={`/courses/${cid}/assignments/${aid}/peer-evaluations`}>
          <button type="button">Peer Evaluations</button>
        </Link>

        <a href={api.grades.canvasExportUrl(cid, aid)} download>
          <button type="button">Canvas Export</button>
        </a>

        {cloneProgress && (
          <span style={{ fontSize: 13 }}>
            {cloneProgress.completed}/{cloneProgress.total} cloned
            {cloneProgress.failed > 0 && (
              <span style={{ color: "#c62828" }}>
                , {cloneProgress.failed} failed
              </span>
            )}
          </span>
        )}

        {checkProgress && (
          <span style={{ fontSize: 13 }}>
            Checks: {checkProgress.completed}/{checkProgress.total} completed
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
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
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
                  GitHub{sortIndicator("github_username")}
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
                {sortedCheckNames.map((cn) => (
                  <th
                    key={cn}
                    style={{
                      textAlign: "center",
                      borderBottom: "1px solid #ccc",
                      padding: 8,
                    }}
                  >
                    {cn}
                  </th>
                ))}
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                  }}
                >
                  Evaluator Grade
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                  }}
                >
                  Peer Grade
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                  }}
                >
                  Penalties
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                  }}
                >
                  Final Grade
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ccc",
                    padding: 8,
                  }}
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const checksByName = new Map(
                  row.check_results.map((cr) => [cr.check_name, cr])
                );
                const isExpanded = expandedRow === row.student_db_id;

                return (
                  <tr key={row.student_db_id}>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      {row.student_name}
                    </td>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
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
                    {sortedCheckNames.map((cn) => {
                      const cr = checksByName.get(cn);
                      if (!cr) {
                        return (
                          <td
                            key={cn}
                            style={{
                              padding: 8,
                              borderBottom: "1px solid #eee",
                              textAlign: "center",
                              color: "#999",
                            }}
                          >
                            —
                          </td>
                        );
                      }
                      return (
                        <td
                          key={cn}
                          style={{
                            padding: 8,
                            borderBottom: "1px solid #eee",
                            textAlign: "center",
                            cursor: "pointer",
                          }}
                          onClick={() =>
                            setExpandedRow(isExpanded ? null : row.student_db_id)
                          }
                          title={cr.message}
                        >
                          <span
                            style={{
                              color: cr.passed ? "#2e7d32" : "#c62828",
                              fontWeight: 600,
                            }}
                          >
                            {cr.passed ? "✓" : "✗"}
                          </span>
                          {isExpanded && (
                            <div
                              style={{
                                textAlign: "left",
                                fontSize: 12,
                                marginTop: 4,
                                padding: 8,
                                background: "#f5f5f5",
                                borderRadius: 4,
                                whiteSpace: "pre-wrap",
                              }}
                            >
                              <div>
                                <strong>Message:</strong> {cr.message}
                              </div>
                              {cr.details && (
                                <div>
                                  <strong>Details:</strong> {cr.details}
                                </div>
                              )}
                              {cr.stderr && (
                                <div style={{ color: "#c62828" }}>
                                  <strong>Stderr:</strong> {cr.stderr}
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                      );
                    })}
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      {row.evaluator_grade_total != null
                        ? row.evaluator_grade_total
                        : "--"}
                    </td>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      {row.peer_grade_average != null
                        ? row.peer_grade_average.toFixed(1)
                        : "--"}
                    </td>
                    <td
                      style={{
                        padding: 8,
                        borderBottom: "1px solid #eee",
                        color: row.penalty_total > 0 ? "#c62828" : undefined,
                      }}
                    >
                      {row.penalty_count > 0
                        ? `${row.penalty_count} (-${row.penalty_total})`
                        : "--"}
                    </td>
                    <td
                      style={{
                        padding: 8,
                        borderBottom: "1px solid #eee",
                        fontWeight: 600,
                      }}
                    >
                      {row.final_grade != null
                        ? row.final_grade.toFixed(2)
                        : "--"}
                      {row.incomplete_pools && row.incomplete_pools.length > 0 && (
                        <span
                          title={`Missing grades: ${row.incomplete_pools.join(", ")} pool(s) have no submissions`}
                          style={{
                            marginLeft: 6,
                            background: "#f59e0b",
                            color: "#fff",
                            borderRadius: 4,
                            padding: "1px 6px",
                            fontSize: 11,
                            fontWeight: 500,
                          }}
                        >
                          incomplete
                        </span>
                      )}
                    </td>
                    <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                      <button
                        onClick={() =>
                          navigate(
                            `/courses/${cid}/assignments/${aid}/grade/${row.student_db_id}`,
                          )
                        }
                        style={{ fontSize: 12 }}
                      >
                        Grade
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
