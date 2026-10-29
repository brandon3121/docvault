import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getMe, type User } from "./api";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";

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

  return (
    <Routes>
      <Route
        path="/login"
        element={
          auth.status === "authenticated" ? (
            <Navigate to="/" replace />
          ) : (
            <LoginPage onLogin={(user) => setAuth({ status: "authenticated", user })} />
          )
        }
      />
      <Route
        path="/"
        element={
          auth.status === "authenticated" ? (
            <HomePage user={auth.user} onLogout={() => setAuth({ status: "anonymous" })} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
