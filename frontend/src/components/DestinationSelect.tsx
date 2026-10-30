import type { Destination } from "../api";

interface DestinationSelectProps {
  id: string;
  destinations: Destination[];
  value: string;
  onChange: (value: string) => void;
  emptyLabel: string;
  required?: boolean;
}

export default function DestinationSelect({
  id,
  destinations,
  value,
  onChange,
  emptyLabel,
  required,
}: DestinationSelectProps) {
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)} required={required}>
      <option value="">{emptyLabel}</option>
      {destinations.map((destination) => (
        <option key={destination.id} value={destination.id}>
          {destination.path}
        </option>
      ))}
    </select>
  );
}
