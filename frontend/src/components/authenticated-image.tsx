"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL, getToken } from "@/lib/api";

/**
 * All clinical images are served from our own backend behind auth.
 * Cliniccards images are fetched server-side with the secret API Token, so
 * the browser only ever receives our protected /api/images/... URL.
 */
export function AuthenticatedImage({
  src,
  alt,
  className,
  thumbnail = false,
}: {
  src: string;
  alt: string;
  className?: string;
  thumbnail?: boolean;
}) {
  const containerRef = useRef<HTMLSpanElement>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [visible, setVisible] = useState(!thumbnail);

  useEffect(() => {
    if (!thumbnail || visible || !containerRef.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [thumbnail, visible]);

  useEffect(() => {
    if (!visible) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    const controller = new AbortController();
    setFailed(false);

    const isOwnBackend = src.startsWith("/api/");
    if (!isOwnBackend) {
      setBlobUrl(src);
      return;
    }

    const queryIndex = src.indexOf("?");
    const path = queryIndex >= 0 ? src.slice(0, queryIndex) : src;
    const query = queryIndex >= 0 ? src.slice(queryIndex) : "";
    const requestSrc = thumbnail && path.endsWith("/file") ? `${path.slice(0, -5)}/thumbnail${query}` : src;
    fetch(`${API_URL}${requestSrc}`, {
      headers: { Authorization: `Bearer ${getToken() ?? ""}` },
      signal: controller.signal,
    })
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
        if (!cancelled && !controller.signal.aborted) setFailed(true);
      });

    return () => {
      cancelled = true;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, thumbnail, visible]);

  if (failed || !blobUrl) {
    return <span ref={containerRef} className="flex h-full w-full items-center justify-center text-xs text-gray-400">{failed ? "Xato" : "..."}</span>;
  }

  // eslint-disable-next-line @next/next/no-img-element
  return <img src={blobUrl} alt={alt} className={className} loading={thumbnail ? "lazy" : "eager"} decoding="async" />;
}
