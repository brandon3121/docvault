import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { duplicateDocumentId, uploadDocument, type DocumentRecord } from "../api";
import DocumentForm, { type DocumentFormValues } from "../components/DocumentForm";
import { useDestinations } from "../hooks/useDestinations";
import { documentErrorMessage } from "../messages";

type Result =
  | { kind: "success"; document: DocumentRecord }
  | { kind: "duplicate"; documentId: number }
  | { kind: "error"; message: string };

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export default function UploadPage() {
  const { destinations, error: destinationsError } = useDestinations();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [formKey, setFormKey] = useState(0);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setResult(null);
    if (selected && !isPdf(selected)) {
      setFile(null);
      setFileError("Selecciona un archivo PDF.");
      event.target.value = "";
      return;
    }
    setFileError(null);
    setFile(selected);
  }

  async function handleSubmit(values: DocumentFormValues) {
    if (!file) {
      setFileError("Selecciona un archivo PDF.");
      return;
    }
    const form = new FormData();
    form.set("file", file);
    form.set("destination_id", values.destinationId);
    form.set("owner_full_name", values.ownerFullName);
    if (values.documentDate) {
      form.set("document_date", values.documentDate);
    }

    setSubmitting(true);
    setResult(null);
    try {
      const document = await uploadDocument(form);
      setResult({ kind: "success", document });
      setFile(null);
      setFormKey((key) => key + 1);
    } catch (error) {
      const existingId = duplicateDocumentId(error);
      setResult(
        existingId !== null
          ? { kind: "duplicate", documentId: existingId }
          : { kind: "error", message: documentErrorMessage(error, "No se pudo subir el documento.") },
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-sections narrow">
      <h1>Subir carta responsiva</h1>

      {destinationsError && <p className="form-error">No se pudieron cargar los orígenes.</p>}
      {!destinationsError && destinations.length === 0 && (
        <p className="muted">Se necesita al menos un origen. Un administrador puede crearlo en Orígenes.</p>
      )}

      {result?.kind === "success" && (
        <p className="notice" role="status">
          Carta guardada: <Link to={`/documents/${result.document.id}`}>{result.document.original_filename}</Link>
        </p>
      )}
      {result?.kind === "duplicate" && (
        <p className="form-error" role="alert">
          Este PDF ya está registrado. <Link to={`/documents/${result.documentId}`}>Ver el documento existente</Link>
        </p>
      )}
      {result?.kind === "error" && (
        <p className="form-error" role="alert">
          {result.message}
        </p>
      )}

      <DocumentForm
        key={formKey}
        destinations={destinations}
        submitLabel={submitting ? "Subiendo" : "Subir"}
        submitting={submitting}
        onSubmit={handleSubmit}
        fileField={
          <div className="field">
            <label className="field-label mono" htmlFor="document-file">
              ARCHIVO PDF
            </label>
            <input id="document-file" type="file" accept="application/pdf,.pdf" onChange={handleFileChange} required />
            {fileError && (
              <p className="form-error" role="alert">
                {fileError}
              </p>
            )}
          </div>
        }
      />
    </div>
  );
}
