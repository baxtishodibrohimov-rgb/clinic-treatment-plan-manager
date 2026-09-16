"use client";

import { useEffect, useState } from "react";
import { API_URL, getToken } from "@/lib/api";

/**
 * Manually-uploaded images are served from our own backend behind auth
 * (a plain <img src> can't attach an Authorization header), so this
 * fetches the bytes with the token and renders them as a blob URL.
 * Cliniccards-sourced images are already public URLs and don't need this.
 */
export function AuthenticatedImage({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setFailed(false);

    const isOwnBackend = src.startsWith("/api/");
    if (!isOwnBackend) {
      setBlobUrl(src);
      return;
    }

    fetch(`${API_URL}${src}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } })
      .then((res) => {
        if (!res.ok) throw new Error("not ok");
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  if (failed || !blobUrl) {
    return <span className="text-xs text-gray-400">{failed ? "Xato" : "..."}</span>;
  }

  // eslint-disable-next-line @next/next/no-img-element
  return <img src={blobUrl} alt={alt} className={className} />;
}
