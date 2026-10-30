import { useEffect, useId, useState, type KeyboardEvent } from "react";
import { searchOwners, type Owner } from "../api";

export interface OwnerValue {
  id: number | null;
  name: string;
}

interface OwnerInputProps {
  id: string;
  value: OwnerValue;
  onChange: (value: OwnerValue) => void;
  disabled?: boolean;
}

const SEARCH_DELAY_MS = 200;

export default function OwnerInput({ id, value, onChange, disabled }: OwnerInputProps) {
  const listId = useId();
  const [suggestions, setSuggestions] = useState<Owner[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    if (!open) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchOwners(value.name, controller.signal)
        .then((owners) => {
          setSuggestions(owners);
          setActiveIndex(-1);
        })
        .catch(() => undefined);
    }, SEARCH_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, value.name]);

  function select(owner: Owner) {
    onChange({ id: owner.id, name: owner.full_name });
    setOpen(false);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => Math.min(index + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter" && open && activeIndex >= 0 && suggestions[activeIndex]) {
      event.preventDefault();
      select(suggestions[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const showList = open && suggestions.length > 0;

  return (
    <div className="combobox">
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        value={value.name}
        disabled={disabled}
        onChange={(event) => {
          onChange({ id: null, name: event.target.value });
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={handleKeyDown}
      />
      {showList && (
        <ul id={listId} role="listbox" className="combobox-list">
          {suggestions.map((owner, index) => (
            <li
              key={owner.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className="combobox-option"
              onMouseDown={(event) => {
                event.preventDefault();
                select(owner);
              }}
            >
              {owner.full_name}
              {owner.department && <span className="mono muted"> {owner.department}</span>}
            </li>
          ))}
        </ul>
      )}
      {value.name.trim() && value.id === null && (
        <p className="field-hint mono muted">NUEVO PROPIETARIO SI NO EXISTE</p>
      )}
    </div>
  );
}
