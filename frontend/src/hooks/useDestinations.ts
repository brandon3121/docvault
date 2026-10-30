import { useCallback, useEffect, useState } from "react";
import { listDestinations, type Destination } from "../api";

export function useDestinations() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [error, setError] = useState(false);

  const reload = useCallback(async () => {
    try {
      setDestinations(await listDestinations());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { destinations, error, reload };
}
