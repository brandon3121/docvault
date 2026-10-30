import { useState, type FormEvent, type ReactNode } from "react";
import type { Destination, DocumentRecord } from "../api";
import DestinationSelect from "./DestinationSelect";

export interface DocumentFormValues {
  destinationId: string;
  ownerFullName: string;
  documentDate: string;
}

interface DocumentFormProps {
  destinations: Destination[];
  initialValues?: DocumentFormValues;
  submitLabel: string;
  submitting: boolean;
  readOnly?: boolean;
  fileField?: ReactNode;
  onSubmit: (values: DocumentFormValues) => void;
}

export const EMPTY_DOCUMENT_FORM: DocumentFormValues = {
  destinationId: "",
  ownerFullName: "",
  documentDate: "",
};

export function valuesFromDocument(document: DocumentRecord): DocumentFormValues {
  return {
    destinationId: String(document.destination_id),
    ownerFullName: document.owner_name ?? "",
    documentDate: document.document_date ?? "",
  };
}

export function collapseSpaces(value: string): string {
  return value.trim().split(/\s+/).filter(Boolean).join(" ");
}

export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function hasFirstAndLastName(value: string): boolean {
  return collapseSpaces(value).split(" ").length >= 2;
}

export default function DocumentForm({
  destinations,
  initialValues = EMPTY_DOCUMENT_FORM,
  submitLabel,
  submitting,
  readOnly = false,
  fileField,
  onSubmit,
}: DocumentFormProps) {
  const [values, setValues] = useState<DocumentFormValues>(initialValues);
  const [ownerTouched, setOwnerTouched] = useState(false);

  function update<K extends keyof DocumentFormValues>(key: K, value: DocumentFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOwnerTouched(true);
    if (!hasFirstAndLastName(values.ownerFullName)) {
      return;
    }
    onSubmit({ ...values, ownerFullName: collapseSpaces(values.ownerFullName) });
  }

  const ownerInvalid = ownerTouched && !hasFirstAndLastName(values.ownerFullName);

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <fieldset className="form-fieldset" disabled={readOnly || submitting}>
        {fileField}

        <div className="field">
          <label className="field-label mono" htmlFor="document-destination">
            ORIGEN
          </label>
          <DestinationSelect
            id="document-destination"
            destinations={destinations}
            value={values.destinationId}
            onChange={(value) => update("destinationId", value)}
            emptyLabel="Selecciona un origen"
            required
          />
        </div>

        <div className="field">
          <label className="field-label mono" htmlFor="document-owner">
            NOMBRE COMPLETO DEL PROPIETARIO
          </label>
          <input
            id="document-owner"
            type="text"
            autoComplete="off"
            maxLength={255}
            value={values.ownerFullName}
            onChange={(event) => update("ownerFullName", event.target.value)}
            onBlur={() => values.ownerFullName && setOwnerTouched(true)}
            aria-invalid={ownerInvalid}
            aria-describedby={ownerInvalid ? "document-owner-error" : undefined}
            required
          />
          {ownerInvalid && (
            <p id="document-owner-error" className="form-error" role="alert">
              Escribe nombre y al menos un apellido.
            </p>
          )}
        </div>

        <div className="field">
          <label className="field-label mono" htmlFor="document-date">
            FECHA DEL DOCUMENTO (OPCIONAL)
          </label>
          <input
            id="document-date"
            type="date"
            max={todayIso()}
            value={values.documentDate}
            onChange={(event) => update("documentDate", event.target.value)}
          />
        </div>

        {!readOnly && (
          <div>
            <button
              type="submit"
              className="button-primary"
              disabled={submitting || !values.destinationId || !values.ownerFullName.trim()}
            >
              {submitLabel}
            </button>
          </div>
        )}
      </fieldset>
    </form>
  );
}
