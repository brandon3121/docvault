import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getMe, type User } from "./api";
import Layout from "./components/Layout";
import DocumentDetailPage from "./pages/DocumentDetailPage";
import DocumentsPage from "./pages/DocumentsPage";
import LoginPage from "./pages/LoginPage";
import OriginsPage from "./pages/OriginsPage";
import UploadPage from "./pages/UploadPage";

type AuthState = { status: "loading" } | { status: "anonymous" } | { status: "authenticated"; user: User };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    getMe()
      .then((user) => setAuth({ status: "authenticated", user }))
      .catch(() => setAuth({ status: "anonymous" }));
  }, []);

  if (auth.status === "loading") {
    return <main className="page page-center mono muted">CARGANDO</main>;
  }

  if (auth.status === "anonymous") {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={(user) => setAuth({ status: "authenticated", user })} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  const { user } = auth;

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route element={<Layout user={user} onLogout={() => setAuth({ status: "anonymous" })} />}>
        <Route path="/" element={<Navigate to="/documents" replace />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage user={user} />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route
          path="/origins"
          element={user.role === "admin" ? <OriginsPage /> : <Navigate to="/documents" replace />}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
