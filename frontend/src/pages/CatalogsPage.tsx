import { useEffect, useState, type FormEvent } from "react";
import {
  ApiError,
  createDestination,
  createDocumentType,
  createOwner,
  deleteDestination,
  deleteDocumentType,
  deleteOwner,
  searchOwners,
  updateDestination,
  updateDocumentType,
  updateOwner,
  type Destination,
  type DocumentType,
  type Owner,
} from "../api";
import DestinationSelect from "../components/DestinationSelect";
import { useCatalogs } from "../hooks/useCatalogs";

function catalogErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      const detail = typeof error.detail === "string" ? error.detail : "";
      if (detail.includes("already exists")) {
        return "Ya existe un registro con ese nombre.";
      }
      if (detail.includes("child")) {
        return "No se puede borrar: tiene subdestinos.";
      }
      return "No se puede borrar: tiene documentos asociados.";
    }
    if (error.status === 400) {
      return "Destino padre no válido.";
    }
    if (error.status === 422) {
      return "Revisa los datos: el nombre es obligatorio.";
    }
  }
  return "No se pudo completar la operación.";
}

function useAction(onDone: () => Promise<void> | void) {
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
      setError(catalogErrorMessage(caught));
      return false;
    } finally {
      setBusy(false);
    }
  }

  return { error, busy, run };
}

function confirmDelete(name: string): boolean {
  return window.confirm(`¿Borrar "${name}"?`);
}

function DestinationRow({ destination, destinations, onChanged }: {
  destination: Destination;
  destinations: Destination[];
  onChanged: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(destination.name);
  const [parentId, setParentId] = useState(destination.parent_id ? String(destination.parent_id) : "");
  const { error, busy, run } = useAction(onChanged);

  async function save(event: FormEvent) {
    event.preventDefault();
    const ok = await run(() => updateDestination(destination.id, name, parentId ? Number(parentId) : null));
    if (ok) {
      setEditing(false);
    }
  }

  return (
    <li className="catalog-row" style={{ paddingLeft: `${destination.depth * 1.5}rem` }}>
      {editing ? (
        <form className="catalog-edit" onSubmit={save}>
          <input aria-label="Nombre" value={name} onChange={(event) => setName(event.target.value)} required />
          <DestinationSelect
            id={`destination-parent-${destination.id}`}
            destinations={destinations}
            value={parentId}
            onChange={setParentId}
            emptyLabel="Sin destino padre"
            excludeId={destination.id}
          />
          <div className="catalog-actions">
            <button type="submit" className="button-primary" disabled={busy || !name.trim()}>
              Guardar
            </button>
            <button type="button" className="button-secondary" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <div className="catalog-view">
          <span>{destination.name}</span>
          <div className="catalog-actions">
            <button type="button" className="button-secondary" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button
              type="button"
              className="button-secondary"
              disabled={busy}
              onClick={() => confirmDelete(destination.name) && run(() => deleteDestination(destination.id))}
            >
              Borrar
            </button>
          </div>
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </li>
  );
}

function DestinationsSection({ destinations, onChanged }: { destinations: Destination[]; onChanged: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("");
  const { error, busy, run } = useAction(onChanged);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (await run(() => createDestination(name, parentId ? Number(parentId) : null))) {
      setName("");
    }
  }

  return (
    <section className="catalog">
      <h2>Destinos</h2>
      <form className="catalog-add" onSubmit={add}>
        <input aria-label="Nuevo destino" placeholder="Nuevo destino" value={name} onChange={(event) => setName(event.target.value)} />
        <DestinationSelect
          id="new-destination-parent"
          destinations={destinations}
          value={parentId}
          onChange={setParentId}
          emptyLabel="Sin destino padre"
        />
        <button type="submit" className="button-primary" disabled={busy || !name.trim()}>
          Agregar
        </button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      <ul className="catalog-list">
        {destinations.map((destination) => (
          <DestinationRow
            key={`${destination.id}-${destination.name}-${destination.parent_id}`}
            destination={destination}
            destinations={destinations}
            onChanged={onChanged}
          />
        ))}
      </ul>
      {destinations.length === 0 && <p className="muted">Sin destinos.</p>}
    </section>
  );
}

function DocumentTypeRow({ documentType, onChanged }: { documentType: DocumentType; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(documentType.name);
  const { error, busy, run } = useAction(onChanged);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (await run(() => updateDocumentType(documentType.id, name))) {
      setEditing(false);
    }
  }

  return (
    <li className="catalog-row">
      {editing ? (
        <form className="catalog-edit" onSubmit={save}>
          <input aria-label="Nombre" value={name} onChange={(event) => setName(event.target.value)} required />
          <div className="catalog-actions">
            <button type="submit" className="button-primary" disabled={busy || !name.trim()}>
              Guardar
            </button>
            <button type="button" className="button-secondary" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <div className="catalog-view">
          <span>{documentType.name}</span>
          <div className="catalog-actions">
            <button type="button" className="button-secondary" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button
              type="button"
              className="button-secondary"
              disabled={busy}
              onClick={() => confirmDelete(documentType.name) && run(() => deleteDocumentType(documentType.id))}
            >
              Borrar
            </button>
          </div>
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </li>
  );
}

function DocumentTypesSection({ documentTypes, onChanged }: { documentTypes: DocumentType[]; onChanged: () => Promise<void> }) {
  const [name, setName] = useState("");
  const { error, busy, run } = useAction(onChanged);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (await run(() => createDocumentType(name))) {
      setName("");
    }
  }

  return (
    <section className="catalog">
      <h2>Tipos de documento</h2>
      <form className="catalog-add" onSubmit={add}>
        <input aria-label="Nuevo tipo" placeholder="Nuevo tipo" value={name} onChange={(event) => setName(event.target.value)} />
        <button type="submit" className="button-primary" disabled={busy || !name.trim()}>
          Agregar
        </button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      <ul className="catalog-list">
        {documentTypes.map((documentType) => (
          <DocumentTypeRow key={`${documentType.id}-${documentType.name}`} documentType={documentType} onChanged={onChanged} />
        ))}
      </ul>
      {documentTypes.length === 0 && <p className="muted">Sin tipos.</p>}
    </section>
  );
}

function OwnerRow({ owner, onChanged }: { owner: Owner; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState(owner.full_name);
  const [department, setDepartment] = useState(owner.department ?? "");
  const { error, busy, run } = useAction(onChanged);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (await run(() => updateOwner(owner.id, fullName, department.trim() || null))) {
      setEditing(false);
    }
  }

  return (
    <li className="catalog-row">
      {editing ? (
        <form className="catalog-edit" onSubmit={save}>
          <input aria-label="Nombre completo" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
          <input
            aria-label="Departamento"
            placeholder="Departamento"
            value={department}
            onChange={(event) => setDepartment(event.target.value)}
          />
          <div className="catalog-actions">
            <button type="submit" className="button-primary" disabled={busy || !fullName.trim()}>
              Guardar
            </button>
            <button type="button" className="button-secondary" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <div className="catalog-view">
          <span>
            {owner.full_name}
            {owner.department && <span className="mono muted"> {owner.department}</span>}
          </span>
          <div className="catalog-actions">
            <button type="button" className="button-secondary" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button
              type="button"
              className="button-secondary"
              disabled={busy}
              onClick={() => confirmDelete(owner.full_name) && run(() => deleteOwner(owner.id))}
            >
              Borrar
            </button>
          </div>
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </li>
  );
}

function OwnersSection() {
  const [query, setQuery] = useState("");
  const [owners, setOwners] = useState<Owner[]>([]);
  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("");

  async function reload() {
    setOwners(await searchOwners(query));
  }

  const { error, busy, run } = useAction(reload);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchOwners(query, controller.signal)
        .then(setOwners)
        .catch(() => undefined);
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (await run(() => createOwner(fullName, department.trim() || null))) {
      setFullName("");
      setDepartment("");
    }
  }

  return (
    <section className="catalog">
      <h2>Propietarios</h2>
      <form className="catalog-add" onSubmit={add}>
        <input
          aria-label="Nombre completo"
          placeholder="Nombre completo"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
        <input
          aria-label="Departamento"
          placeholder="Departamento"
          value={department}
          onChange={(event) => setDepartment(event.target.value)}
        />
        <button type="submit" className="button-primary" disabled={busy || !fullName.trim()}>
          Agregar
        </button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="field">
        <label className="field-label mono" htmlFor="owner-search">
          BUSCAR (MÁXIMO 20 RESULTADOS)
        </label>
        <input id="owner-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      <ul className="catalog-list">
        {owners.map((owner) => (
          <OwnerRow key={`${owner.id}-${owner.full_name}-${owner.department}`} owner={owner} onChanged={reload} />
        ))}
      </ul>
      {owners.length === 0 && <p className="muted">Sin resultados.</p>}
    </section>
  );
}

export default function CatalogsPage() {
  const { destinations, documentTypes, error, reload } = useCatalogs();

  return (
    <div className="stack">
      <h1>Catálogos</h1>
      {error && <p className="form-error">No se pudieron cargar los catálogos.</p>}
      <div className="catalogs">
        <DestinationsSection destinations={destinations} onChanged={reload} />
        <DocumentTypesSection documentTypes={documentTypes} onChanged={reload} />
        <OwnersSection />
      </div>
    </div>
  );
}
