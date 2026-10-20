import { Navigate, Route, Routes } from "react-router-dom";

import { Shell } from "./components/Shell";
import { DashboardPage } from "./pages/DashboardPage";
import { GraphExplorerPage } from "./pages/GraphExplorerPage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { MySkillsPage } from "./pages/MySkillsPage";
import { PathBuilderPage } from "./pages/PathBuilderPage";
import { RoleExplorerPage } from "./pages/RoleExplorerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<DashboardPage />} />
        <Route path="skills" element={<MySkillsPage />} />
        <Route path="graph" element={<GraphExplorerPage />} />
        <Route path="roles" element={<RoleExplorerPage />} />
        <Route path="path" element={<PathBuilderPage />} />
        <Route path="methodology" element={<MethodologyPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
