import { Route, Routes } from "react-router-dom";

import { GuestRoute, ProtectedRoute } from "./auth/RouteGuards";
import AppShell from "./components/layout/AppShell";
import ActivityPage from "./pages/ActivityPage";
import AnalysesPage from "./pages/AnalysesPage";
import AnalysisReportPage from "./pages/AnalysisReportPage";
import DashboardPage from "./pages/DashboardPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import IssuesPage from "./pages/IssuesPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import RegisterPage from "./pages/RegisterPage";
import RepositoriesPage from "./pages/RepositoriesPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import SettingsPage from "./pages/SettingsPage";
import TeamPage from "./pages/TeamPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/repositories" element={<RepositoriesPage />} />
          <Route path="/analyses" element={<AnalysesPage />} />
          <Route path="/analyses/:analysisId" element={<AnalysisReportPage />} />
          <Route path="/issues" element={<IssuesPage />} />
          <Route path="/team" element={<TeamPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
