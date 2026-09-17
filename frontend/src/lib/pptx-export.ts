import { API_URL, getToken } from "./api";

export interface FetchedImage {
  dataUrl: string;
  width: number;
  height: number;
}

/** Fetches one clinical image (through our authenticated backend, same as
 * AuthenticatedImage) and decodes it to a data: URI plus its natural pixel
 * size, both of which pptxgenjs's addImage/addShape need. */
export async function fetchImageForExport(externalUrl: string): Promise<FetchedImage> {
  const isOwnBackend = externalUrl.startsWith("/api/");
  const url = isOwnBackend ? `${API_URL}${externalUrl}` : externalUrl;
  const res = await fetch(url, isOwnBackend ? { headers: { Authorization: `Bearer ${getToken() ?? ""}` } } : undefined);
  if (!res.ok) throw new Error("Rasmni yuklab bo'lmadi");
  const blob = await res.blob();
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Rasmni o'qib bo'lmadi"));
    reader.readAsDataURL(blob);
  });
  const { width, height } = await new Promise<{ width: number; height: number }>((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => reject(new Error("Rasm o'lchamini aniqlab bo'lmadi"));
    img.src = dataUrl;
  });
  return { dataUrl, width, height };
}

/** Same math as CSS `object-fit: contain` — the sub-rect of `box` that an
 * image of size (iw,ih) actually renders into. Used both by the on-screen
 * slide viewer and by the PPTX export, so a mark drawn at (x%, y%) of the
 * *image* lands on the same spot in both. */
export function containBox(
  iw: number,
  ih: number,
  box: { x: number; y: number; w: number; h: number },
): { x: number; y: number; w: number; h: number } {
  if (!iw || !ih) return box;
  const scale = Math.min(box.w / iw, box.h / ih);
  const w = iw * scale;
  const h = ih * scale;
  return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h };
}

export function hexNoHash(hex: string): string {
  return hex.replace("#", "");
}
