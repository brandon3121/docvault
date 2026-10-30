import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, documentFileUrl, getDocument, updateDocument, type DocumentRecord, type User } from "../api";
import DocumentForm, { valuesFromDocument, type DocumentFormValues } from "../components/DocumentForm";
import { formatDate, formatDateTime } from "../format";
import { useDestinations } from "../hooks/useDestinations";
import { documentErrorMessage } from "../messages";

interface DocumentDetailPageProps {
  user: User;
}

export default function DocumentDetailPage({ user }: DocumentDetailPageProps) {
  const { id } = useParams();
  const documentId = Number(id);
  const { destinations } = useDestinations();
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [loadError, setLoadError] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    setDocument(null);
    setLoadError(null);
    getDocument(documentId)
      .then(setDocument)
      .catch((error) => setLoadError(error instanceof ApiError ? error.status : 0));
  }, [documentId]);

  async function handleSave(values: DocumentFormValues) {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateDocument(documentId, {
        destination_id: Number(values.destinationId),
        owner_full_name: values.ownerFullName,
        document_date: values.documentDate || null,
      });
      setDocument(updated);
      setFormKey((key) => key + 1);
      setMessage({ kind: "ok", text: "Cambios guardados." });
    } catch (error) {
      setMessage({ kind: "error", text: documentErrorMessage(error, "No se pudieron guardar los cambios.") });
    } finally {
      setSaving(false);
    }
  }

  if (loadError !== null) {
    return (
      <div className="page-sections">
        <p className="form-error">{loadError === 404 ? "El documento no existe." : "No se pudo cargar el documento."}</p>
        <Link to="/documents">Volver a documentos</Link>
      </div>
    );
  }

  if (!document) {
    return <p className="mono muted">CARGANDO</p>;
  }

  const canEdit = user.role === "admin" || document.uploaded_by === user.id;

  return (
    <div className="page-sections">
      <div>
        <Link to="/documents" className="mono muted back-link">
          ← DOCUMENTOS
        </Link>
        <h1>{document.owner_name ?? document.document_type_name}</h1>
        <p className="mono muted page-subtitle">
          {document.document_type_name.toUpperCase()} · {document.destination_path.toUpperCase()}
        </p>
      </div>

      <div className="detail">
        <div className="page-sections">
          <section className="section">
            <h2>Información</h2>
            <dl className="meta">
              <dt className="mono">ARCHIVO</dt>
              <dd>
                <a href={documentFileUrl(document.id)} target="_blank" rel="noreferrer">
                  {document.original_filename}
                </a>
              </dd>
              <dt className="mono">SUBIDO POR</dt>
              <dd>
                {document.uploaded_by_name}, {formatDateTime(document.uploaded_at)}
              </dd>
              <dt className="mono">FECHA</dt>
              <dd>
                {formatDate(document.document_date)}
                {document.document_date_edited && <span className="mono muted"> EDITADO</span>}
              </dd>
              <dt className="mono">PROPIETARIO</dt>
              <dd>
                {document.owner_name ?? "—"}
                {document.owner_name_edited && <span className="mono muted"> EDITADO</span>}
              </dd>
              <dt className="mono">SHA-256</dt>
              <dd className="mono hash">{document.sha256}</dd>
            </dl>
          </section>

          <section className="section">
            <h2>Editar</h2>
            {message && (
              <p
                className={message.kind === "ok" ? "notice" : "form-error"}
                role={message.kind === "ok" ? "status" : "alert"}
              >
                {message.text}
              </p>
            )}
            {!canEdit && <p className="muted">Solo quien subió el documento o un administrador puede editarlo.</p>}
            <DocumentForm
              key={`${document.id}-${formKey}`}
              destinations={destinations}
              initialValues={valuesFromDocument(document)}
              submitLabel={saving ? "Guardando" : "Guardar cambios"}
              submitting={saving}
              readOnly={!canEdit}
              onSubmit={handleSave}
            />
          </section>
        </div>

        <iframe className="pdf-frame" src={documentFileUrl(document.id)} title={`PDF: ${document.original_filename}`} />
      </div>
    </div>
  );
}
