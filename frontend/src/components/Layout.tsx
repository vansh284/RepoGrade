import { Outlet, NavLink } from "react-router-dom";

export default function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav
        style={{
          width: 200,
          padding: 16,
          borderRight: "1px solid #ddd",
          background: "#f8f9fa",
        }}
      >
        <h1 style={{ fontSize: 20, marginBottom: 24 }}>RepoGrade</h1>
        <NavLink
          to="/"
          style={({ isActive }) => ({
            display: "block",
            padding: "8px 0",
            textDecoration: "none",
            fontWeight: isActive ? "bold" : "normal",
            color: isActive ? "#1a73e8" : "#333",
          })}
        >
          Courses
        </NavLink>
        <NavLink
          to="/settings"
          style={({ isActive }) => ({
            display: "block",
            padding: "8px 0",
            textDecoration: "none",
            fontWeight: isActive ? "bold" : "normal",
            color: isActive ? "#1a73e8" : "#333",
          })}
        >
          Settings
        </NavLink>
      </nav>
      <main style={{ flex: 1, padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
