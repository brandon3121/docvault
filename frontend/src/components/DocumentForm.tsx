import { useState, type FormEvent, type ReactNode, type SyntheticEvent } from "react";
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
  validateExtra?: () => boolean;
  onSubmit: (values: DocumentFormValues) => void;
}

export const MIN_DOCUMENT_DATE = "2000-01-01";
export const OWNER_NAME_MESSAGE = "Escribe nombre y al menos un apellido";
export const DOCUMENT_DATE_MESSAGE = "La fecha debe estar entre 2000 y hoy";

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

function isDocumentDateInRange(value: string): boolean {
  return !value || (value >= MIN_DOCUMENT_DATE && value <= todayIso());
}

function openDatePicker(event: SyntheticEvent<HTMLInputElement>) {
  const input = event.currentTarget;
  if (typeof input.showPicker !== "function") {
    return;
  }
  try {
    input.showPicker();
  } catch {
    return;
  }
}

export default function DocumentForm({
  destinations,
  initialValues = EMPTY_DOCUMENT_FORM,
  submitLabel,
  submitting,
  readOnly = false,
  fileField,
  validateExtra,
  onSubmit,
}: DocumentFormProps) {
  const [values, setValues] = useState<DocumentFormValues>(initialValues);
  const [ownerTouched, setOwnerTouched] = useState(false);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [dateTouched, setDateTouched] = useState(false);

  function update<K extends keyof DocumentFormValues>(key: K, value: DocumentFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOwnerTouched(true);
    setSubmitAttempted(true);
    setDateTouched(true);
    const extraValid = validateExtra ? validateExtra() : true;
    if (
      !extraValid ||
      !values.destinationId ||
      !hasFirstAndLastName(values.ownerFullName) ||
      !isDocumentDateInRange(values.documentDate)
    ) {
      return;
    }
    onSubmit({ ...values, ownerFullName: collapseSpaces(values.ownerFullName) });
  }

  const ownerInvalid = ownerTouched && !hasFirstAndLastName(values.ownerFullName);
  const destinationMissing = submitAttempted && !values.destinationId;
  const dateInvalid = dateTouched && !isDocumentDateInRange(values.documentDate);

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
          {destinationMissing && (
            <p className="form-error" role="alert">
              Selecciona un origen.
            </p>
          )}
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
              {OWNER_NAME_MESSAGE}
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
            className="date-input"
            min={MIN_DOCUMENT_DATE}
            max={todayIso()}
            value={values.documentDate}
            onChange={(event) => update("documentDate", event.target.value)}
            onFocus={openDatePicker}
            onClick={openDatePicker}
            onBlur={() => values.documentDate && setDateTouched(true)}
            aria-invalid={dateInvalid}
            aria-describedby={dateInvalid ? "document-date-error" : undefined}
          />
          {dateInvalid && (
            <p id="document-date-error" className="form-error" role="alert">
              {DOCUMENT_DATE_MESSAGE}
            </p>
          )}
        </div>

        {!readOnly && (
          <div>
            <button type="submit" className="button-primary" disabled={submitting}>
              {submitLabel}
            </button>
          </div>
        )}
      </fieldset>
    </form>
  );
}
