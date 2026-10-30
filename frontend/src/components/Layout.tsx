import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { logout, type User } from "../api";

interface LayoutProps {
  user: User;
  onLogout: () => void;
}

export default function Layout({ user, onLogout }: LayoutProps) {
  const [busy, setBusy] = useState(false);

  async function handleLogout() {
    setBusy(true);
    try {
      await logout();
    } finally {
      onLogout();
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <span className="brand">docvault</span>
        <nav className="nav" aria-label="Principal">
          <NavLink to="/documents" end className="nav-link">
            Documentos
          </NavLink>
          <NavLink to="/upload" className="nav-link">
            Subir
          </NavLink>
          {user.role === "admin" && (
            <NavLink to="/origins" className="nav-link">
              Orígenes
            </NavLink>
          )}
        </nav>
        <div className="topbar-actions">
          <span className="mono muted topbar-user">{user.full_name.toUpperCase()}</span>
          <button type="button" className="button-secondary" onClick={handleLogout} disabled={busy}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
