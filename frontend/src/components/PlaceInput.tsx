import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { geocode } from "../api/client";
import type { PlaceRef } from "../api/types";
import { useDebounced } from "../hooks/useDebounced";

interface Props {
  label: string;
  placeholder: string;
  text: string;
  selected: PlaceRef | null;
  onTextChange: (text: string) => void;
  onSelect: (place: PlaceRef) => void;
}

/** Text box with debounced, cached geocoding suggestions and keyboard navigation. */
export default function PlaceInput({ label, placeholder, text, selected, onTextChange, onSelect }: Props) {
  const id = useId();
  const listId = `${id}-list`;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const query = useDebounced(text.trim(), 300);
  const enabled = open && !selected && query.length >= 2;
  const { data: results = [], isFetching, isError } = useQuery({
    queryKey: ["geocode", query.toLowerCase()],
    queryFn: ({ signal }) => geocode(query, signal),
    enabled,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const showList = enabled && results.length > 0;

  function choose(place: PlaceRef) {
    onSelect(place);
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && showList) {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === "ArrowUp" && showList) {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && showList && active >= 0) {
      event.preventDefault();
      choose(results[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="combo">
        <input
          id={id}
          type="text"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${id}-opt-${active}` : undefined}
          autoComplete="off"
          placeholder={placeholder}
          value={text}
          className={selected ? "resolved" : undefined}
          onChange={(e) => {
            onTextChange(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {showList && (
          <ul id={listId} role="listbox" className="suggestions">
            {results.map((place, i) => (
              <li
                key={`${place.lat},${place.lon},${place.label}`}
                id={`${id}-opt-${i}`}
                role="option"
                aria-selected={i === active}
                className={i === active ? "active" : undefined}
                // mousedown (not click) so it fires before the input's blur closes the list
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(place);
                }}
              >
                {place.label}
              </li>
            ))}
          </ul>
        )}
      </div>
      {enabled && !isFetching && !isError && results.length === 0 && (
        <p className="field-note">No matches found</p>
      )}
      {isError && <p className="field-note error">Couldn't search places right now</p>}
    </div>
  );
}
