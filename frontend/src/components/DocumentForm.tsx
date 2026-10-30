import { useState, type FormEvent, type ReactNode } from "react";
import type { Destination, DocumentRecord, DocumentType } from "../api";
import DestinationSelect from "./DestinationSelect";
import OwnerInput, { type OwnerValue } from "./OwnerInput";

export interface DocumentFormValues {
  title: string;
  destinationId: string;
  documentTypeId: string;
  owner: OwnerValue;
  documentDate: string;
}

interface DocumentFormProps {
  destinations: Destination[];
  documentTypes: DocumentType[];
  initialValues?: DocumentFormValues;
  submitLabel: string;
  submitting: boolean;
  readOnly?: boolean;
  fileField?: ReactNode;
  onSubmit: (values: DocumentFormValues) => void;
}

export const EMPTY_DOCUMENT_FORM: DocumentFormValues = {
  title: "",
  destinationId: "",
  documentTypeId: "",
  owner: { id: null, name: "" },
  documentDate: "",
};

export function valuesFromDocument(document: DocumentRecord): DocumentFormValues {
  return {
    title: document.title,
    destinationId: String(document.destination_id),
    documentTypeId: String(document.document_type_id),
    owner: { id: document.owner_id, name: document.owner_name ?? "" },
    documentDate: document.document_date ?? "",
  };
}

export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export default function DocumentForm({
  destinations,
  documentTypes,
  initialValues = EMPTY_DOCUMENT_FORM,
  submitLabel,
  submitting,
  readOnly = false,
  fileField,
  onSubmit,
}: DocumentFormProps) {
  const [values, setValues] = useState<DocumentFormValues>(initialValues);

  function update<K extends keyof DocumentFormValues>(key: K, value: DocumentFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(values);
  }

  const incomplete = !values.title.trim() || !values.destinationId || !values.documentTypeId;

  return (
    <form className="form" onSubmit={handleSubmit}>
      <fieldset className="form-fieldset" disabled={readOnly || submitting}>
        {fileField}

        <div className="field">
          <label className="field-label mono" htmlFor="document-title">
            TÍTULO
          </label>
          <input
            id="document-title"
            type="text"
            maxLength={500}
            value={values.title}
            onChange={(event) => update("title", event.target.value)}
            required
          />
        </div>

        <div className="form-grid">
          <div className="field">
            <label className="field-label mono" htmlFor="document-destination">
              DESTINO
            </label>
            <DestinationSelect
              id="document-destination"
              destinations={destinations}
              value={values.destinationId}
              onChange={(value) => update("destinationId", value)}
              emptyLabel="Selecciona un destino"
              required
            />
          </div>

          <div className="field">
            <label className="field-label mono" htmlFor="document-type">
              TIPO
            </label>
            <select
              id="document-type"
              value={values.documentTypeId}
              onChange={(event) => update("documentTypeId", event.target.value)}
              required
            >
              <option value="">Selecciona un tipo</option>
              {documentTypes.map((documentType) => (
                <option key={documentType.id} value={documentType.id}>
                  {documentType.name}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field-label mono" htmlFor="document-owner">
              PROPIETARIO
            </label>
            <OwnerInput
              id="document-owner"
              value={values.owner}
              onChange={(value) => update("owner", value)}
              disabled={readOnly || submitting}
            />
          </div>

          <div className="field">
            <label className="field-label mono" htmlFor="document-date">
              FECHA DEL DOCUMENTO
            </label>
            <input
              id="document-date"
              type="date"
              max={todayIso()}
              value={values.documentDate}
              onChange={(event) => update("documentDate", event.target.value)}
            />
          </div>
        </div>

        {!readOnly && (
          <div>
            <button type="submit" className="button-primary" disabled={submitting || incomplete}>
              {submitLabel}
            </button>
          </div>
        )}
      </fieldset>
    </form>
  );
}
