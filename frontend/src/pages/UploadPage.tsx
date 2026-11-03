import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router";
import { duplicateDocumentId, extractDocumentFields, uploadDocument, type DocumentRecord } from "../api";
import DocumentForm, { type DocumentFormSuggestion, type DocumentFormValues } from "../components/DocumentForm";
import ErrorNotice from "../components/ErrorNotice";
import { useDestinations } from "../hooks/useDestinations";
import { documentErrorMessage } from "../messages";

type Result =
  | { kind: "success"; document: DocumentRecord }
  | { kind: "duplicate"; documentId: number }
  | { kind: "error"; message: string };

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function canPreviewPdf(): boolean {
  return navigator.pdfViewerEnabled !== false;
}

function usePreviewUrl(file: File | null): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return url;
}

export default function UploadPage() {
  const { destinations, error: destinationsError } = useDestinations();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [formKey, setFormKey] = useState(0);
  const [extracting, setExtracting] = useState(false);
  const [suggestion, setSuggestion] = useState<DocumentFormSuggestion | null>(null);
  const extraction = useRef<AbortController | null>(null);
  const previewUrl = usePreviewUrl(file);

  function readSuggestion(selected: File | null) {
    extraction.current?.abort();
    extraction.current = null;
    setSuggestion(null);
    setExtracting(false);
    if (!selected) {
      return;
    }
    const controller = new AbortController();
    extraction.current = controller;
    setExtracting(true);
    extractDocumentFields(selected, controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) {
          setSuggestion({ ownerFullName: found.owner_full_name, documentDate: found.document_date });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setSuggestion({ ownerFullName: null, documentDate: null });
        }
      })
      .finally(() => {
        if (extraction.current === controller) {
          extraction.current = null;
          setExtracting(false);
        }
      });
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setResult(null);
    if (selected && !isPdf(selected)) {
      setFile(null);
      setFileError("Selecciona un archivo PDF.");
      readSuggestion(null);
      event.target.value = "";
      return;
    }
    setFileError(null);
    setFile(selected);
    readSuggestion(selected);
  }

  function validateFile(): boolean {
    if (!file) {
      setFileError("Selecciona un archivo PDF.");
      return false;
    }
    return true;
  }

  async function handleSubmit(values: DocumentFormValues) {
    if (!file) {
      return;
    }
    const form = new FormData();
    form.set("file", file);
    form.set("destination_id", values.destinationId);
    form.set("owner_full_name", values.ownerFullName);
    if (values.documentDate) {
      form.set("document_date", values.documentDate);
    }
    if (suggestion?.ownerFullName) {
      form.set("owner_name_extracted", suggestion.ownerFullName);
    }
    if (suggestion?.documentDate) {
      form.set("document_date_extracted", suggestion.documentDate);
    }

    setSubmitting(true);
    setResult(null);
    try {
      const document = await uploadDocument(form);
      setResult({ kind: "success", document });
      setFile(null);
      setFileError(null);
      setSuggestion(null);
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
    <div className={previewUrl ? "page-sections" : "page-sections narrow"}>
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
        <ErrorNotice>
          Este PDF ya está registrado. <Link to={`/documents/${result.documentId}`}>Ver el documento existente</Link>
        </ErrorNotice>
      )}
      {result?.kind === "error" && (
        <ErrorNotice>{result.message}</ErrorNotice>
      )}

      <div className={previewUrl ? "upload-layout" : undefined}>
        {previewUrl && (
          <div className="upload-preview">
            {canPreviewPdf() ? (
              <iframe className="upload-preview-frame" src={previewUrl} title="Vista previa del documento" />
            ) : (
              <p className="muted">No se puede mostrar la vista previa</p>
            )}
          </div>
        )}
        <div className="upload-form">
          <DocumentForm
            key={formKey}
            destinations={destinations}
            submitLabel={submitting ? "Subiendo" : "Subir"}
            submitting={submitting}
            submitDisabled={extracting}
            suggestion={suggestion}
            validateExtra={validateFile}
            onSubmit={handleSubmit}
            fileField={
              <div className="field">
                <label className="field-label mono" htmlFor="document-file">
                  ARCHIVO PDF
                </label>
                <input id="document-file" type="file" accept="application/pdf,.pdf" onChange={handleFileChange} required />
                {extracting && (
                  <p className="mono muted" role="status">
                    Leyendo el documento...
                  </p>
                )}
                {!extracting && (suggestion?.ownerFullName || suggestion?.documentDate) && (
                  <p className="muted" role="status">
                    Sugerido automáticamente. Revisa antes de guardar.
                  </p>
                )}
                {fileError && (
                  <p className="form-error" role="alert">
                    {fileError}
                  </p>
                )}
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
