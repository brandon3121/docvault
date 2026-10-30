import { ApiError } from "./api";

export function documentErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = typeof error.detail === "string" ? error.detail : "";
    if (error.status === 400) {
      if (detail.includes("future")) {
        return "La fecha del documento no puede ser futura.";
      }
      if (detail.includes("owner_full_name")) {
        return "Escribe el nombre completo del propietario: nombre y al menos un apellido.";
      }
      if (detail.includes("not a PDF")) {
        return "El archivo no es un PDF válido.";
      }
      return "Revisa los datos del formulario.";
    }
    if (error.status === 413) {
      return "El archivo supera el tamaño máximo permitido.";
    }
    if (error.status === 403) {
      return "Solo quien subió el documento o un administrador puede editarlo.";
    }
  }
  return fallback;
}
