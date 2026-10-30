import type { Destination } from "../api";

interface DestinationSelectProps {
  id: string;
  destinations: Destination[];
  value: string;
  onChange: (value: string) => void;
  emptyLabel: string;
  required?: boolean;
  excludeId?: number;
}

const INDENT = "    ";

export default function DestinationSelect({
  id,
  destinations,
  value,
  onChange,
  emptyLabel,
  required,
  excludeId,
}: DestinationSelectProps) {
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)} required={required}>
      <option value="">{emptyLabel}</option>
      {destinations
        .filter((destination) => destination.id !== excludeId)
        .map((destination) => (
          <option key={destination.id} value={destination.id}>
            {INDENT.repeat(destination.depth)}
            {destination.name}
          </option>
        ))}
    </select>
  );
}
