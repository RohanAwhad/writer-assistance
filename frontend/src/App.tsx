import { Routes, Route, Link } from "react-router";
import ProjectsPage from "@/pages/ProjectsPage";
import ProjectWorkspace from "@/pages/ProjectWorkspace";
import ReportEditor from "@/pages/ReportEditor";

export default function App() {
  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex h-12 shrink-0 items-center border-b px-4">
        <Link to="/" className="text-base font-semibold tracking-tight">
          Writer's Desk
        </Link>
      </header>
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectWorkspace />} />
          <Route
            path="/projects/:projectId/report/:reportId"
            element={<ReportEditor />}
          />
        </Routes>
      </main>
    </div>
  );
}
