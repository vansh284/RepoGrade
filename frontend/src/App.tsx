import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import AssignmentsPage from "./pages/AssignmentsPage";
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
