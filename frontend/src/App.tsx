import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import CoursesPage from "./pages/CoursesPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<CoursesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
