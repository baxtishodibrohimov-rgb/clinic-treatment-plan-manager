import type { AnnotationColor, AnyMark, Arrow, Mark } from "./types";

// Shared between the analysis wizard's fullscreen drawing toolbar and the
// presentation slide renderer, so a mark drawn once looks identical in both
// places (and in the exported PPTX).
export const COLOR_HEX: Record<AnnotationColor, string> = {
  red: "#DC2626",
  green: "#16A34A",
  blue: "#2563EB",
  yellow: "#CA8A04",
  black: "#4B5563",
};
export const COLOR_KEYS = Object.keys(COLOR_HEX) as AnnotationColor[];

export const WIDTH_PRESETS = [2, 3.5, 5.5] as const;
export const WIDTH_LABELS = ["Ingichka", "O'rta", "Qalin"];

export function nextWidth(current: number): number {
  const idx = WIDTH_PRESETS.indexOf(current as (typeof WIDTH_PRESETS)[number]);
  return WIDTH_PRESETS[(idx + 1) % WIDTH_PRESETS.length] ?? WIDTH_PRESETS[0];
}

export function splitMarks(items: AnyMark[]): { mark: Mark | null; arrows: Arrow[] } {
  const mark = (items.find((i) => i.kind === "mark") as Mark | undefined) ?? null;
  const arrows = items.filter((i) => i.kind === "arrow") as Arrow[];
  return { mark, arrows };
}
