export function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("es", { dateStyle: "short", timeStyle: "short" });
}
