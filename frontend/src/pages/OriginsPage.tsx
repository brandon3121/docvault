import { useState, type FormEvent } from "react";
import { ApiError, createDestination, deleteDestination, renameDestination, type Destination } from "../api";
import { useDestinations } from "../hooks/useDestinations";

function originErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      const detail = typeof error.detail === "string" ? error.detail : "";
      return detail.includes("child")
        ? "No se puede borrar: este origen tiene sucursales."
        : "No se puede borrar: hay documentos asociados a este origen.";
    }
    if (error.status === 422) {
      return "El nombre es obligatorio.";
    }
  }
  return "No se pudo completar la operación.";
}

function useAction(onDone: () => Promise<void>) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      await action();
      await onDone();
      return true;
    } catch (caught) {
      setError(originErrorMessage(caught));
      return false;
    } finally {
      setBusy(false);
    }
  }

  return { error, busy, run };
}

function OriginRow({ origin, onChanged }: { origin: Destination; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(origin.name);
  const { error, busy, run } = useAction(onChanged);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (await run(() => renameDestination(origin.id, name))) {
      setEditing(false);
    }
  }

  function cancel() {
    setName(origin.name);
    setEditing(false);
  }

  function remove() {
    if (window.confirm(`¿Borrar el origen "${origin.path}"?`)) {
      void run(() => deleteDestination(origin.id));
    }
  }

  return (
    <li className="origin-row">
      {editing ? (
        <form className="origin-edit" onSubmit={save}>
          <input
            aria-label={`Nuevo nombre para ${origin.path}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoFocus
          />
          <div className="row-actions">
            <button type="submit" className="button-primary button-small" disabled={busy || !name.trim()}>
              Guardar
            </button>
            <button type="button" className="button-secondary button-small" onClick={cancel}>
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <div className="origin-view">
          <span>{origin.path}</span>
          <div className="row-actions">
            <button type="button" className="button-secondary button-small" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button type="button" className="button-secondary button-small" disabled={busy} onClick={remove}>
              Borrar
            </button>
          </div>
        </div>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}

export default function OriginsPage() {
  const { destinations, error: loadError, reload } = useDestinations();
  const [name, setName] = useState("");
  const { error, busy, run } = useAction(reload);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (await run(() => createDestination(name.trim(), null))) {
      setName("");
    }
  }

  return (
    <div className="page-sections origins">
      <h1>Orígenes</h1>

      <section className="section">
        <h2>Agregar origen</h2>
        <form className="origin-add" onSubmit={add}>
          <div className="field">
            <label className="field-label mono" htmlFor="origin-name">
              NOMBRE
            </label>
            <input id="origin-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={255} />
          </div>
          <div>
            <button type="submit" className="button-primary" disabled={busy || !name.trim()}>
              Agregar origen
            </button>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </form>
      </section>

      <section className="section">
        <h2>Orígenes registrados</h2>
        {loadError && <p className="form-error">No se pudieron cargar los orígenes.</p>}
        {destinations.length > 0 ? (
          <ul className="origin-list">
            {destinations.map((origin) => (
              <OriginRow key={`${origin.id}-${origin.path}`} origin={origin} onChanged={reload} />
            ))}
          </ul>
        ) : (
          !loadError && <p className="muted">Todavía no hay orígenes.</p>
        )}
      </section>
    </div>
  );
}
