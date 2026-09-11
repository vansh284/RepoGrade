import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import AssignmentDashboardPage from "./pages/AssignmentDashboardPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import CoursesPage from "./pages/CoursesPage";
import GradingPage from "./pages/GradingPage";
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
