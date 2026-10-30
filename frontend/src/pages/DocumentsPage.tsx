import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { listDocuments, searchOwners, type DocumentFilters, type DocumentPage, type Owner } from "../api";
import DestinationSelect from "../components/DestinationSelect";
import { formatDate, formatDateTime } from "../format";
import { useDestinations } from "../hooks/useDestinations";

const PAGE_SIZE = 50;
const OWNER_SUGGESTION_DELAY_MS = 200;
const FILTER_KEYS = ["q", "owner", "destination_id", "date_from", "date_to"] as const;

type FilterKey = (typeof FILTER_KEYS)[number];
type FilterValues = Record<FilterKey, string>;

function filtersFromParams(params: URLSearchParams): FilterValues {
  return Object.fromEntries(FILTER_KEYS.map((key) => [key, params.get(key) ?? ""])) as FilterValues;
}

function useOwnerSuggestions(query: string): Owner[] {
  const [owners, setOwners] = useState<Owner[]>([]);

  useEffect(() => {
    if (!query.trim()) {
      setOwners([]);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchOwners(query, controller.signal)
        .then(setOwners)
        .catch(() => undefined);
    }, OWNER_SUGGESTION_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  return owners;
}

export default function DocumentsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { destinations } = useDestinations();
  const [draft, setDraft] = useState<FilterValues>(() => filtersFromParams(params));
  const [page, setPage] = useState<DocumentPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const ownerSuggestions = useOwnerSuggestions(draft.owner);

  const offset = Number(params.get("offset") ?? 0) || 0;
  const paramsKey = params.toString();

  useEffect(() => {
    const filters: DocumentFilters = { ...filtersFromParams(params), limit: PAGE_SIZE, offset };
    let cancelled = false;
    setLoading(true);
    listDocuments(filters)
      .then((result) => {
        if (!cancelled) {
          setPage(result);
          setError(false);
        }
      })
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [paramsKey]);

  function applyFilters(values: FilterValues, nextOffset = 0) {
    const next = new URLSearchParams();
    for (const key of FILTER_KEYS) {
      if (values[key].trim()) {
        next.set(key, values[key].trim());
      }
    }
    if (nextOffset > 0) {
      next.set("offset", String(nextOffset));
    }
    setParams(next);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(draft);
  }

  function handleClear() {
    const empty = filtersFromParams(new URLSearchParams());
    setDraft(empty);
    applyFilters(empty);
  }

  function updateDraft(key: FilterKey, value: string) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  const applied = filtersFromParams(params);
  const total = page?.total ?? 0;

  return (
    <div className="page-sections">
      <h1>Documentos</h1>

      <section className="section">
        <h2>Filtros</h2>
        <form className="filters" onSubmit={handleSubmit} role="search">
          <div className="field">
            <label className="field-label mono" htmlFor="filter-owner">
              PROPIETARIO
            </label>
            <input
              id="filter-owner"
              type="search"
              list="owner-suggestions"
              autoComplete="off"
              value={draft.owner}
              onChange={(event) => updateDraft("owner", event.target.value)}
            />
            <datalist id="owner-suggestions">
              {ownerSuggestions.map((owner) => (
                <option key={owner.id} value={owner.full_name} />
              ))}
            </datalist>
          </div>
          <div className="field">
            <label className="field-label mono" htmlFor="filter-destination">
              ORIGEN
            </label>
            <DestinationSelect
              id="filter-destination"
              destinations={destinations}
              value={draft.destination_id}
              onChange={(value) => updateDraft("destination_id", value)}
              emptyLabel="Todos"
            />
          </div>
          <div className="field">
            <label className="field-label mono" htmlFor="filter-q">
              ARCHIVO
            </label>
            <input id="filter-q" type="search" value={draft.q} onChange={(event) => updateDraft("q", event.target.value)} />
          </div>
          <div className="field">
            <label className="field-label mono" htmlFor="filter-date-from">
              DESDE
            </label>
            <input
              id="filter-date-from"
              type="date"
              value={draft.date_from}
              onChange={(event) => updateDraft("date_from", event.target.value)}
            />
          </div>
          <div className="field">
            <label className="field-label mono" htmlFor="filter-date-to">
              HASTA
            </label>
            <input
              id="filter-date-to"
              type="date"
              value={draft.date_to}
              onChange={(event) => updateDraft("date_to", event.target.value)}
            />
          </div>
          <div className="filters-actions">
            <button type="submit" className="button-primary">
              Buscar
            </button>
            <button type="button" className="button-secondary" onClick={handleClear}>
              Limpiar
            </button>
          </div>
        </form>
      </section>

      <section className="section">
        <h2>Resultados</h2>
        {error && <p className="form-error">No se pudieron cargar los documentos.</p>}

        <p className="mono muted" aria-live="polite">
          {loading ? "CARGANDO" : `${total} DOCUMENTO${total === 1 ? "" : "S"}`}
        </p>

        {page && page.items.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Origen</th>
                  <th scope="col">Propietario</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Carga</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((document) => (
                  <tr
                    key={document.id}
                    className="table-row-link"
                    onClick={() => navigate(`/documents/${document.id}`)}
                  >
                    <td>
                      <Link to={`/documents/${document.id}`} onClick={(event) => event.stopPropagation()}>
                        {document.destination_path}
                      </Link>
                    </td>
                    <td>{document.owner_name ?? "—"}</td>
                    <td className="mono nowrap">{formatDate(document.document_date)}</td>
                    <td className="mono nowrap">{formatDateTime(document.uploaded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {page && total > PAGE_SIZE && (
          <div className="pagination">
            <button
              type="button"
              className="button-secondary"
              disabled={offset === 0}
              onClick={() => applyFilters(applied, Math.max(offset - PAGE_SIZE, 0))}
            >
              Anterior
            </button>
            <span className="mono muted">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} DE {total}
            </span>
            <button
              type="button"
              className="button-secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => applyFilters(applied, offset + PAGE_SIZE)}
            >
              Siguiente
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
