import { useCallback, useEffect, useState } from "react";
import { listDestinations, listDocumentTypes, type Destination, type DocumentType } from "../api";

export function useCatalogs() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([]);
  const [error, setError] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [nextDestinations, nextTypes] = await Promise.all([listDestinations(), listDocumentTypes()]);
      setDestinations(nextDestinations);
      setDocumentTypes(nextTypes);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { destinations, documentTypes, error, reload };
}
