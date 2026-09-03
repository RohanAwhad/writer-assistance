import { useState } from "react";
import ProjectsScreen from "./screens/ProjectsScreen";
import WorkspaceScreen from "./screens/WorkspaceScreen";

type View =
  | { name: "projects" }
  | { name: "workspace"; projectId: number; projectName: string };

export default function App() {
  const [view, setView] = useState<View>({ name: "projects" });

  if (view.name === "projects") {
    return <ProjectsScreen onOpenProject={(projectId, projectName) => setView({ name: "workspace", projectId, projectName })} />;
  }
  return (
    <WorkspaceScreen
      projectId={view.projectId}
      projectName={view.projectName}
      onBack={() => setView({ name: "projects" })}
    />
  );
}
