import { useState, type FormEvent } from "react";
import { login, type User } from "../api";

interface LoginPageProps {
  onLogin: (user: User) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      onLogin(await login(username, password));
    } catch {
      setError("Usuario o contraseña incorrectos.");
      setSubmitting(false);
    }
  }

  return (
    <main className="page page-center">
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <h1>docvault</h1>
        <p className="mono muted">ACCESO INTERNO</p>

        <label className="field">
          <span className="field-label mono">USUARIO</span>
          <input
            type="text"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoFocus
          />
        </label>

        <label className="field">
          <span className="field-label mono">CONTRASEÑA</span>
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="button-primary" disabled={submitting || !username || !password}>
          {submitting ? "Entrando" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
