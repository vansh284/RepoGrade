import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import AssignmentDashboardPage from "./pages/AssignmentDashboardPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import EmailTemplatesPage from "./pages/EmailTemplatesPage";
import CoursesPage from "./pages/CoursesPage";
import StudentsPage from "./pages/StudentsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<CoursesPage />} />
          <Route path="/courses/:courseId/students" element={<StudentsPage />} />
          <Route path="/courses/:courseId/assignments" element={<AssignmentsPage />} />
          <Route path="/courses/:courseId/assignments/:assignmentId/dashboard" element={<AssignmentDashboardPage />} />
          <Route path="/courses/:courseId/assignments/:assignmentId/emails" element={<EmailTemplatesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
