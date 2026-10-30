import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, duplicateDocumentId, uploadDocument, type DocumentRecord } from "../api";
import DocumentForm, { type DocumentFormValues } from "../components/DocumentForm";
import { useCatalogs } from "../hooks/useCatalogs";

type Result =
  | { kind: "success"; document: DocumentRecord }
  | { kind: "duplicate"; documentId: number }
  | { kind: "error"; message: string };

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function uploadErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 400) {
      return typeof error.detail === "string" && error.detail.includes("future")
        ? "La fecha del documento no puede ser futura."
        : "El archivo no es un PDF válido o faltan datos obligatorios.";
    }
    if (error.status === 413) {
      return "El archivo supera el tamaño máximo permitido.";
    }
  }
  return "No se pudo subir el documento.";
}

export default function UploadPage() {
  const { destinations, documentTypes, error: catalogError } = useCatalogs();
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
    form.set("title", values.title.trim());
    form.set("destination_id", values.destinationId);
    form.set("document_type_id", values.documentTypeId);
    if (values.owner.id !== null) {
      form.set("owner_id", String(values.owner.id));
    } else if (values.owner.name.trim()) {
      form.set("owner_name", values.owner.name.trim());
    }
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
          : { kind: "error", message: uploadErrorMessage(error) },
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="stack">
      <h1>Subir documento</h1>

      {catalogError && <p className="form-error">No se pudieron cargar los catálogos.</p>}
      {!catalogError && (destinations.length === 0 || documentTypes.length === 0) && (
        <p className="muted">Se necesita al menos un destino y un tipo de documento. Un administrador puede crearlos en Catálogos.</p>
      )}

      {result?.kind === "success" && (
        <p className="notice" role="status">
          Documento guardado: <Link to={`/documents/${result.document.id}`}>{result.document.title}</Link>
        </p>
      )}
      {result?.kind === "duplicate" && (
        <p className="form-error" role="alert">
          Este PDF ya existe. <Link to={`/documents/${result.documentId}`}>Ver el documento existente</Link>
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
        documentTypes={documentTypes}
        submitLabel={submitting ? "Subiendo" : "Subir"}
        submitting={submitting}
        onSubmit={handleSubmit}
        fileField={
          <div className="field">
            <label className="field-label mono" htmlFor="document-file">
              ARCHIVO PDF
            </label>
            <input
              id="document-file"
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
              required
            />
            {fileError && (
              <p className="form-error" role="alert">
                {fileError}
              </p>
            )}
          </div>
        }
      />
    </section>
  );
}
