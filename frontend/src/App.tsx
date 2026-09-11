import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import AssignmentDashboardPage from "./pages/AssignmentDashboardPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import EmailTemplatesPage from "./pages/EmailTemplatesPage";
import CoursesPage from "./pages/CoursesPage";
import GradingPage from "./pages/GradingPage";
import PeerEvaluationsPage from "./pages/PeerEvaluationsPage";
import SettingsPage from "./pages/SettingsPage";
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
          <Route path="/courses/:courseId/assignments/:assignmentId/grade/:studentId" element={<GradingPage />} />
          <Route path="/courses/:courseId/assignments/:assignmentId/emails" element={<EmailTemplatesPage />} />
          <Route path="/courses/:courseId/assignments/:assignmentId/peer-evaluations" element={<PeerEvaluationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
