import { useState } from "react";
import { logout, type User } from "../api";

interface HomePageProps {
  user: User;
  onLogout: () => void;
}

export default function HomePage({ user, onLogout }: HomePageProps) {
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
        <div className="topbar-actions">
          <span className="mono muted">{user.role.toUpperCase()}</span>
          <button type="button" className="button-secondary" onClick={handleLogout} disabled={busy}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <main className="content">
        <h1>Bienvenido, {user.full_name}</h1>
      </main>
    </div>
  );
}
