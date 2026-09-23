"use client";

import { useEffect, useRef, useState } from "react";
import { COLOR_HEX, COLOR_KEYS, WIDTH_LABELS, WIDTH_PRESETS, nextWidth, splitMarks } from "@/lib/annotations";
import type { AnnotationColor, AnyMark, Arrow, Mark } from "@/lib/types";

type Tool = "oval" | "arrow" | "line" | null;
type DragPreview = { tool: Exclude<Tool, null>; color: AnnotationColor; x1: number; y1: number; x2: number; y2: number };

const MARKER_PREFIX = "ac-arrow";

function pct(clientX: number, clientY: number, rect: DOMRect) {
  return { x: ((clientX - rect.left) / rect.width) * 100, y: ((clientY - rect.top) / rect.height) * 100 };
}

/**
 * SVG drawing layer over a photo — line / arrow / oval / rect marks, in the
 * exact % coordinate shape the backend's ImageAnnotation model stores.
 * Read-only when `editable` is false (case detail thumbnail, presentation
 * slide); interactive (draw / move / resize / color / width) otherwise.
 */
export function AnnotationCanvas({
  marks,
  onChange,
  editable = false,
  idSalt,
}: {
  marks: AnyMark[];
  onChange?: (next: AnyMark[]) => void;
  editable?: boolean;
  idSalt: string;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [tool, setTool] = useState<Tool>(null);
  const [color, setColor] = useState<AnnotationColor>("red");
  const [width, setWidth] = useState<number>(WIDTH_PRESETS[1]);
  const [ovalVariant, setOvalVariant] = useState<"oval" | "rect">("oval");
  const [colorPickerOpen, setColorPickerOpen] = useState(false);
  const [widthPickerOpen, setWidthPickerOpen] = useState(false);
  const [drag, setDrag] = useState<DragPreview | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const [resizing, setResizing] = useState(false);
  const [moving, setMoving] = useState<{ startPt: { x: number; y: number }; orig: Mark } | null>(null);
  const [selectedMarkIndex, setSelectedMarkIndex] = useState<number | null>(null);
  const [selectedArrowIndex, setSelectedArrowIndex] = useState<number | null>(null);
  const [arrowDrag, setArrowDrag] = useState<{
    index: number;
    mode: "move" | "start" | "end";
    startPt: { x: number; y: number };
    orig: Arrow;
  } | null>(null);

  const { marks: committedMarks, arrows } = splitMarks(marks);
  // During resize/move we redraw every mousemove but only tell the parent
  // (which PUTs a new versioned DB row per call) once, on mouseup — else a
  // single drag would write dozens of rows.
  const [liveMark, setLiveMark] = useState<Mark | null>(null);
  const [liveArrows, setLiveArrows] = useState<Arrow[] | null>(null);
  const committedMark = selectedMarkIndex === null ? null : committedMarks[selectedMarkIndex] ?? null;
  const mark = liveMark ?? committedMark;
  const displayedMarks = committedMarks.map((item, index) => (index === selectedMarkIndex && liveMark ? liveMark : item));
  const displayedArrows = liveArrows ?? arrows;

  useEffect(() => {
    if (!resizing && !moving) return;
    const onMove = (e: MouseEvent) => {
      const rect = wrapRef.current?.getBoundingClientRect();
      if (!rect || !rect.width || !rect.height) return;
      const p = pct(e.clientX, e.clientY, rect);
      if (resizing && committedMark) {
        setLiveMark({ ...committedMark, x2: p.x, y2: p.y });
      } else if (moving && moving.orig) {
        const dx = p.x - moving.startPt.x;
        const dy = p.y - moving.startPt.y;
        setLiveMark({ ...moving.orig, x1: moving.orig.x1 + dx, y1: moving.orig.y1 + dy, x2: moving.orig.x2 + dx, y2: moving.orig.y2 + dy });
      }
    };
    const onUp = () => {
      setResizing(false);
      setMoving(null);
      setLiveMark((m) => {
        if (m && selectedMarkIndex !== null) {
          const nextMarks = committedMarks.map((item, index) => (index === selectedMarkIndex ? m : item));
          onChange?.([...nextMarks, ...arrows]);
        }
        return null;
      });
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resizing, moving, selectedMarkIndex]);

  useEffect(() => {
    if (!arrowDrag) return;
    const onMove = (e: MouseEvent) => {
      const rect = wrapRef.current?.getBoundingClientRect();
      if (!rect || !rect.width || !rect.height) return;
      const point = pct(e.clientX, e.clientY, rect);
      const next = arrows.map((arrow, index) => {
        if (index !== arrowDrag.index) return arrow;
        if (arrowDrag.mode === "start") return { ...arrowDrag.orig, x1: point.x, y1: point.y };
        if (arrowDrag.mode === "end") return { ...arrowDrag.orig, x2: point.x, y2: point.y };
        const dx = point.x - arrowDrag.startPt.x;
        const dy = point.y - arrowDrag.startPt.y;
        return {
          ...arrowDrag.orig,
          x1: arrowDrag.orig.x1 + dx,
          y1: arrowDrag.orig.y1 + dy,
          x2: arrowDrag.orig.x2 + dx,
          y2: arrowDrag.orig.y2 + dy,
        };
      });
      setLiveArrows(next);
    };
    const onUp = () => {
      setArrowDrag(null);
      setLiveArrows((next) => {
        if (next) onChange?.([...displayedMarks, ...next]);
        return null;
      });
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arrowDrag]);

  const handleDragStart = (e: React.MouseEvent) => {
    if (!editable || !tool || resizing || moving) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const p = pct(e.clientX, e.clientY, rect);
    dragStart.current = p;
    setDrag({ tool, color, x1: p.x, y1: p.y, x2: p.x, y2: p.y });
  };
  const handleDragMove = (e: React.MouseEvent) => {
    if (!dragStart.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const p = pct(e.clientX, e.clientY, rect);
    setDrag((d) => (d ? { ...d, x2: p.x, y2: p.y } : d));
  };
  const handleDragEnd = (e: React.MouseEvent) => {
    const start = dragStart.current;
    dragStart.current = null;
    setDrag(null);
    if (!start || !tool) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const end = pct(e.clientX, e.clientY, rect);
    const dist = Math.hypot(end.x - start.x, end.y - start.y);
    if (tool === "oval") {
      const rawX1 = dist < 3 ? start.x - 10 : start.x;
      const rawY1 = dist < 3 ? start.y - 8 : start.y;
      const rawX2 = dist < 3 ? start.x + 10 : end.x;
      const rawY2 = dist < 3 ? start.y + 8 : end.y;
      const next: Mark = {
        kind: "mark",
        x1: Math.min(rawX1, rawX2),
        y1: Math.min(rawY1, rawY2),
        x2: Math.max(rawX1, rawX2),
        y2: Math.max(rawY1, rawY2),
        color,
        width,
        shape: ovalVariant,
      };
      onChange?.([...committedMarks, next, ...arrows]);
      setSelectedMarkIndex(committedMarks.length);
      setSelectedArrowIndex(null);
    } else if (dist >= 1) {
      const next: Arrow = { kind: "arrow", x1: start.x, y1: start.y, x2: end.x, y2: end.y, color, width, shape: tool };
      onChange?.([...committedMarks, ...arrows, next]);
      setSelectedArrowIndex(arrows.length);
      setSelectedMarkIndex(null);
    }
    setTool(null);
  };

  const cycleMarkWidth = (idx: number) => {
    const nextMarks = committedMarks.map((item, index) => (index === idx ? { ...item, width: nextWidth(item.width) } : item));
    onChange?.([...nextMarks, ...arrows]);
  };
  const cycleArrowWidth = (idx: number) => {
    const next = arrows.map((a, i) => (i === idx ? { ...a, width: nextWidth(a.width) } : a));
    onChange?.([...committedMarks, ...next]);
  };
  const startResize = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setResizing(true);
  };
  const startMove = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (!mark) return;
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMoving({ startPt: pct(e.clientX, e.clientY, rect), orig: mark });
  };
  const startArrowEdit = (e: React.MouseEvent, index: number, mode: "move" | "start" | "end") => {
    e.stopPropagation();
    e.preventDefault();
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTool(null);
    setSelectedMarkIndex(null);
    setSelectedArrowIndex(index);
    setArrowDrag({ index, mode, startPt: pct(e.clientX, e.clientY, rect), orig: arrows[index] });
  };
  const clearAll = () => {
    setSelectedMarkIndex(null);
    setSelectedArrowIndex(null);
    setTool(null);
    onChange?.([]);
  };
  const deleteSelected = () => {
    if (selectedMarkIndex !== null) {
      onChange?.([...committedMarks.filter((_, index) => index !== selectedMarkIndex), ...arrows]);
      setSelectedMarkIndex(null);
      return;
    }
    if (selectedArrowIndex !== null) {
      onChange?.([...committedMarks, ...arrows.filter((_, index) => index !== selectedArrowIndex)]);
      setSelectedArrowIndex(null);
    }
  };

  const markX = mark ? Math.min(mark.x1, mark.x2) : 0;
  const markY = mark ? Math.min(mark.y1, mark.y2) : 0;
  const markW = mark ? Math.abs(mark.x2 - mark.x1) : 0;
  const markH = mark ? Math.abs(mark.y2 - mark.y1) : 0;

  const dragIsOval = drag?.tool === "oval" && ovalVariant !== "rect";
  const dragIsRect = drag?.tool === "oval" && ovalVariant === "rect";
  const dragIsLine = drag && drag.tool !== "oval";

  return (
    <div
      ref={wrapRef}
      style={{ position: "relative", width: "100%", height: "100%" }}
      onMouseDown={editable ? handleDragStart : undefined}
      onMouseMove={editable ? handleDragMove : undefined}
      onMouseUp={editable ? handleDragEnd : undefined}
    >
      {editable && tool && (
        <div style={{ position: "absolute", inset: 0, zIndex: 5, cursor: "crosshair" }} />
      )}
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
        <defs>
          {COLOR_KEYS.map((key) => (
            <marker
              key={key}
              id={`${MARKER_PREFIX}-${idSalt}-${key}`}
              markerWidth={8}
              markerHeight={8}
              refX={4}
              refY={4}
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 Z" fill={COLOR_HEX[key]} />
            </marker>
          ))}
        </defs>

        {displayedMarks.map((drawnMark, index) => {
          const cx = (drawnMark.x1 + drawnMark.x2) / 2;
          const cy = (drawnMark.y1 + drawnMark.y2) / 2;
          const rx = Math.max(3, Math.abs(drawnMark.x2 - drawnMark.x1) / 2);
          const ry = Math.max(3, Math.abs(drawnMark.y2 - drawnMark.y1) / 2);
          const x = Math.min(drawnMark.x1, drawnMark.x2);
          const y = Math.min(drawnMark.y1, drawnMark.y2);
          const w = Math.abs(drawnMark.x2 - drawnMark.x1);
          const h = Math.abs(drawnMark.y2 - drawnMark.y1);
          return (
          <g key={`mark-${index}`}>
            {drawnMark.shape === "rect" ? (
              <rect
                x={`${x}%`}
                y={`${y}%`}
                width={`${w}%`}
                height={`${h}%`}
                fill="none"
                stroke={COLOR_HEX[drawnMark.color]}
                strokeWidth={drawnMark.width}
                onClick={editable ? () => { setTool(null); setSelectedArrowIndex(null); setSelectedMarkIndex(index); } : undefined}
                onDoubleClick={editable ? () => cycleMarkWidth(index) : undefined}
                style={editable ? { pointerEvents: "auto", cursor: "pointer" } : undefined}
              />
            ) : (
              <ellipse
                cx={`${cx}%`}
                cy={`${cy}%`}
                rx={`${rx}%`}
                ry={`${ry}%`}
                fill="none"
                stroke={COLOR_HEX[drawnMark.color]}
                strokeWidth={drawnMark.width}
                onClick={editable ? () => { setTool(null); setSelectedArrowIndex(null); setSelectedMarkIndex(index); } : undefined}
                onDoubleClick={editable ? () => cycleMarkWidth(index) : undefined}
                style={editable ? { pointerEvents: "auto", cursor: "pointer" } : undefined}
              />
            )}
          </g>
          );
        })}

        {displayedArrows.map((a, i) => (
          <g key={i}>
            <line
              x1={`${a.x1}%`}
              y1={`${a.y1}%`}
              x2={`${a.x2}%`}
              y2={`${a.y2}%`}
              stroke={COLOR_HEX[a.color]}
              strokeWidth={a.width}
              markerEnd={a.shape === "arrow" ? `url(#${MARKER_PREFIX}-${idSalt}-${a.color})` : undefined}
              onDoubleClick={editable ? () => cycleArrowWidth(i) : undefined}
              onClick={editable ? () => { setTool(null); setSelectedMarkIndex(null); setSelectedArrowIndex(i); } : undefined}
              style={editable ? { pointerEvents: "auto", cursor: "move" } : undefined}
            />
            {editable && (
              <line
                x1={`${a.x1}%`}
                y1={`${a.y1}%`}
                x2={`${a.x2}%`}
                y2={`${a.y2}%`}
                stroke="transparent"
                strokeWidth={Math.max(14, a.width + 10)}
                onMouseDown={(event) => startArrowEdit(event, i, "move")}
                onClick={() => { setSelectedMarkIndex(null); setSelectedArrowIndex(i); }}
                onDoubleClick={() => cycleArrowWidth(i)}
                style={{ pointerEvents: "stroke", cursor: "move" }}
              />
            )}
            {a.shape === "line" && (
              <>
                <circle cx={`${a.x1}%`} cy={`${a.y1}%`} r={4} fill={COLOR_HEX[a.color]} />
                <circle cx={`${a.x2}%`} cy={`${a.y2}%`} r={4} fill={COLOR_HEX[a.color]} />
              </>
            )}
          </g>
        ))}

        {drag && dragIsOval && (
          <ellipse
            cx={`${(drag.x1 + drag.x2) / 2}%`}
            cy={`${(drag.y1 + drag.y2) / 2}%`}
            rx={`${Math.max(1, Math.abs(drag.x2 - drag.x1) / 2)}%`}
            ry={`${Math.max(1, Math.abs(drag.y2 - drag.y1) / 2)}%`}
            fill="none"
            stroke={COLOR_HEX[drag.color]}
            strokeWidth={width}
            strokeDasharray="4 3"
          />
        )}
        {drag && dragIsRect && (
          <rect
            x={`${Math.min(drag.x1, drag.x2)}%`}
            y={`${Math.min(drag.y1, drag.y2)}%`}
            width={`${Math.abs(drag.x2 - drag.x1)}%`}
            height={`${Math.abs(drag.y2 - drag.y1)}%`}
            fill="none"
            stroke={COLOR_HEX[drag.color]}
            strokeWidth={width}
            strokeDasharray="4 3"
          />
        )}
        {drag && dragIsLine && (
          <line
            x1={`${drag.x1}%`}
            y1={`${drag.y1}%`}
            x2={`${drag.x2}%`}
            y2={`${drag.y2}%`}
            stroke={COLOR_HEX[drag.color]}
            strokeWidth={width}
            strokeDasharray="4 3"
          />
        )}
      </svg>

      {editable && selectedArrowIndex !== null && displayedArrows[selectedArrowIndex] && (
        <>
          {(["start", "end"] as const).map((handle) => {
            const arrow = displayedArrows[selectedArrowIndex];
            const x = handle === "start" ? arrow.x1 : arrow.x2;
            const y = handle === "start" ? arrow.y1 : arrow.y2;
            return (
              <div
                key={handle}
                title={handle === "start" ? "Boshlanish nuqtasini o‘zgartirish" : "Uzunligini o‘zgartirish"}
                onMouseDown={(event) => startArrowEdit(event, selectedArrowIndex, handle)}
                style={{
                  position: "absolute",
                  left: `${x}%`,
                  top: `${y}%`,
                  width: 16,
                  height: 16,
                  transform: "translate(-50%,-50%)",
                  borderRadius: "50%",
                  background: "#ffffff",
                  border: `3px solid ${COLOR_HEX[arrow.color]}`,
                  cursor: "move",
                  zIndex: 8,
                }}
              />
            );
          })}
        </>
      )}

      {editable && mark && (
        <>
          <div
            onMouseDown={startMove}
            title="Ko'chirish"
            style={{ position: "absolute", left: `${markX}%`, top: `${markY}%`, width: `${markW}%`, height: `${markH}%`, cursor: "move", zIndex: 6 }}
          />
          <div
            onMouseDown={startResize}
            title="O'lchamini o'zgartirish"
            style={{
              position: "absolute",
              left: `${mark.x2}%`,
              top: `${mark.y2}%`,
              width: 14,
              height: 14,
              transform: "translate(-50%,-50%)",
              borderRadius: "50%",
              background: COLOR_HEX[mark.color],
              border: "2px solid #ffffff",
              cursor: "nwse-resize",
              zIndex: 7,
            }}
          />
        </>
      )}

      {editable && (
        <div
          style={{
            position: "absolute",
            left: 12,
            bottom: 12,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "8px 16px",
            background: "#1c1c1c",
            borderRadius: 10,
            flexWrap: "wrap",
            zIndex: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, position: "relative" }}>
            <button
              type="button"
              onClick={() => {
                setColorPickerOpen((v) => !v);
                setWidthPickerOpen(false);
              }}
              style={{ width: 22, height: 22, borderRadius: "50%", background: COLOR_HEX[color], border: "2px solid #ffffff", cursor: "pointer" }}
            />
            {colorPickerOpen && (
              <div style={{ position: "absolute", bottom: "100%", left: 0, marginBottom: 4, display: "flex", gap: 4, padding: 4, background: "#2a2a2a", borderRadius: 8 }}>
                {COLOR_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    title={key}
                    onClick={() => {
                      setColor(key);
                      setColorPickerOpen(false);
                    }}
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: "50%",
                      background: COLOR_HEX[key],
                      border: `2px solid ${color === key ? "#ffffff" : "transparent"}`,
                      cursor: "pointer",
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          <div style={{ width: 1, height: 20, background: "#3a3a3a" }} />

          <div style={{ display: "flex", alignItems: "center", gap: 6, position: "relative" }}>
            <button
              type="button"
              title="Qalinlik"
              onClick={() => {
                setWidthPickerOpen((v) => !v);
                setColorPickerOpen(false);
              }}
              style={{ width: 22, height: 22, borderRadius: 6, background: "transparent", border: "1px solid #3a3a3a", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              <svg width={14} height={14} viewBox="0 0 24 24">
                <line x1={4} y1={20} x2={20} y2={4} stroke="#ffffff" strokeWidth={width} strokeLinecap="round" />
              </svg>
            </button>
            {widthPickerOpen && (
              <div style={{ position: "absolute", bottom: "100%", left: 0, marginBottom: 4, display: "flex", flexDirection: "column", gap: 4, padding: 6, background: "#2a2a2a", borderRadius: 8, zIndex: 20 }}>
                {WIDTH_PRESETS.map((w, i) => (
                  <button
                    key={w}
                    type="button"
                    title={WIDTH_LABELS[i]}
                    onClick={() => {
                      setWidth(w);
                      setWidthPickerOpen(false);
                    }}
                    style={{ width: 60, height: 22, display: "flex", alignItems: "center", justifyContent: "center", background: width === w ? "#3a3a3a" : "transparent", border: "none", borderRadius: 5, cursor: "pointer" }}
                  >
                    <svg width={36} height={10} viewBox="0 0 36 10">
                      <line x1={2} y1={5} x2={34} y2={5} stroke="#ffffff" strokeWidth={w} strokeLinecap="round" />
                    </svg>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div style={{ width: 1, height: 20, background: "#3a3a3a" }} />

          <button
            type="button"
            title="Chiziq"
            onClick={() => setTool((t) => (t === "line" ? null : "line"))}
            style={{ display: "flex", alignItems: "center", gap: 4, background: tool === "line" ? "#3a3a3a" : "transparent", border: "none", cursor: "pointer", padding: "4px 6px", borderRadius: 6 }}
          >
            <svg width={16} height={16} viewBox="0 0 24 24">
              <line x1={4} y1={20} x2={20} y2={4} stroke={tool === "line" ? "#ffffff" : "#9a9a9a"} strokeWidth={2.5} />
              <circle cx={4} cy={20} r={2.5} fill={tool === "line" ? "#ffffff" : "#9a9a9a"} />
              <circle cx={20} cy={4} r={2.5} fill={tool === "line" ? "#ffffff" : "#9a9a9a"} />
            </svg>
          </button>
          <button
            type="button"
            title="Strelka"
            onClick={() => setTool((t) => (t === "arrow" ? null : "arrow"))}
            style={{ display: "flex", alignItems: "center", gap: 4, background: tool === "arrow" ? "#3a3a3a" : "transparent", border: "none", cursor: "pointer", padding: "4px 6px", borderRadius: 6 }}
          >
            <svg width={16} height={16} viewBox="0 0 24 24">
              <line x1={4} y1={20} x2={20} y2={4} stroke={tool === "arrow" ? "#ffffff" : "#9a9a9a"} strokeWidth={2.5} />
              <path d="M20,4 L20,10 M20,4 L14,4" stroke={tool === "arrow" ? "#ffffff" : "#9a9a9a"} strokeWidth={2.5} fill="none" />
            </svg>
          </button>
          <button
            type="button"
            title="Ikki marta bosing: to'rtburchak/oval"
            onClick={() => { setSelectedMarkIndex(null); setSelectedArrowIndex(null); setTool((t) => (t === "oval" ? null : "oval")); }}
            onDoubleClick={() => setOvalVariant((v) => (v === "rect" ? "oval" : "rect"))}
            style={{ display: "flex", alignItems: "center", gap: 4, background: tool === "oval" ? "#3a3a3a" : "transparent", border: "none", cursor: "pointer", padding: "4px 6px", borderRadius: 6 }}
          >
            {ovalVariant === "rect" ? (
              <svg width={16} height={16} viewBox="0 0 24 24">
                <rect x={4} y={6} width={16} height={12} fill="none" stroke={tool === "oval" ? "#ffffff" : "#9a9a9a"} strokeWidth={2.5} />
              </svg>
            ) : (
              <svg width={16} height={16} viewBox="0 0 24 24">
                <ellipse cx={12} cy={12} rx={9} ry={6} fill="none" stroke={tool === "oval" ? "#ffffff" : "#9a9a9a"} strokeWidth={2.5} />
              </svg>
            )}
          </button>
          <button
            type="button"
            title="Tanlangan shaklni o‘chirish"
            disabled={selectedMarkIndex === null && selectedArrowIndex === null}
            onClick={deleteSelected}
            style={{ display: "flex", alignItems: "center", background: "transparent", border: "none", cursor: selectedMarkIndex === null && selectedArrowIndex === null ? "not-allowed" : "pointer", opacity: selectedMarkIndex === null && selectedArrowIndex === null ? 0.35 : 1, padding: "4px 6px" }}
          >
            <svg width={16} height={16} viewBox="0 0 24 24">
              <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 10v7m4-7v7" stroke="#ffffff" strokeWidth={1.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button type="button" title="Hammasini tozalash" onClick={clearAll} style={{ display: "flex", alignItems: "center", background: "transparent", border: "none", cursor: "pointer", padding: "4px 6px" }}>
            <svg width={16} height={16} viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" stroke="#9a9a9a" strokeWidth={2.2} strokeLinecap="round" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
