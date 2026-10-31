import type { Checkpoint } from "../api/types";
import { RISK_COLORS, RISK_LABELS } from "./risk";
import { formatDateTime } from "./format";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** DOM for a checkpoint popup. Built with textContent (never innerHTML). */
export function buildCheckpointPopup(cp: Checkpoint, routeLabel: string): HTMLElement {
  const root = el("div", "popup");

  const head = el("div", "popup-head");
  const chip = el("span", "chip", RISK_LABELS[cp.risk]);
  chip.style.background = RISK_COLORS[cp.risk];
  head.append(chip, el("strong", undefined, `Mile ${Math.round(cp.mile)}`));
  root.append(head, el("div", "popup-sub", routeLabel));

  root.append(el("div", "popup-eta", `ETA ${formatDateTime(cp.eta)}`));

  const grid = el("dl", "popup-grid");
  const rows: [string, string][] = [
    ["Wind", `${cp.wind_mph.toFixed(0)} mph`],
    ["Rain", `${cp.rain_in_hr.toFixed(2)} in/hr`],
    ["Snow", `${cp.snow_in_hr.toFixed(2)} in/hr`],
  ];
  for (const [label, value] of rows) {
    grid.append(el("dt", undefined, label), el("dd", undefined, value));
  }
  root.append(grid, el("p", "popup-reason", cp.reason));
  return root;
}
