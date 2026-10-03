import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import VerifyAnyFile from "./pages/VerifyAnyFile";
import Receipt from "./pages/Receipt";
import StudentDashboard from "./pages/StudentDashboard";
import EvidenceDetail from "./pages/EvidenceDetail";
import SkillGraphPage from "./pages/SkillGraph";
import CareerGapPage from "./pages/CareerGap";
import ProfilePage from "./pages/ProfilePage";
import PublicProfilePage from "./pages/PublicProfile";
import IssuerDashboard from "./pages/IssuerDashboard";
import RecruiterPage from "./pages/RecruiterPage";
import AuditPage from "./pages/AuditPage";
import type { Role } from "./lib/types";

function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) return <p className="text-sm">Loading</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/verify" element={<VerifyAnyFile />} />
            <Route path="/receipt/:credentialId" element={<Receipt />} />
            <Route path="/profiles/:userId" element={<PublicProfilePage />} />
            <Route
              path="/dashboard"
              element={
                <RequireRole roles={["student"]}>
                  <StudentDashboard />
                </RequireRole>
              }
            />
            <Route
              path="/evidence/:evidenceId"
              element={
                <RequireRole roles={["student", "issuer", "recruiter"]}>
                  <EvidenceDetail />
                </RequireRole>
              }
            />
            <Route
              path="/graph"
              element={
                <RequireRole roles={["student"]}>
                  <SkillGraphPage />
                </RequireRole>
              }
            />
            <Route
              path="/career"
              element={
                <RequireRole roles={["student"]}>
                  <CareerGapPage />
                </RequireRole>
              }
            />
            <Route
              path="/profile"
              element={
                <RequireRole roles={["student"]}>
                  <ProfilePage />
                </RequireRole>
              }
            />
            <Route
              path="/issuer"
              element={
                <RequireRole roles={["issuer"]}>
                  <IssuerDashboard />
                </RequireRole>
              }
            />
            <Route
              path="/recruiter"
              element={
                <RequireRole roles={["recruiter"]}>
                  <RecruiterPage />
                </RequireRole>
              }
            />
            <Route
              path="/audit"
              element={
                <RequireRole roles={["student", "issuer", "recruiter"]}>
                  <AuditPage />
                </RequireRole>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}
