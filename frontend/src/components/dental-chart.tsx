"use client";

import { useRef } from "react";
import type { DentalChartOut, ToothStatusOut } from "@/lib/types";

const DOUBLE_CLICK_MS = 300;

function ToothBox({ tooth, onToothClick, dark }: { tooth: ToothStatusOut; onToothClick: (clickType: "single" | "double") => void; dark: boolean }) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleClick = () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
      onToothClick("double");
    } else {
      timer.current = setTimeout(() => {
        timer.current = null;
        onToothClick("single");
      }, DOUBLE_CLICK_MS);
    }
  };

  const empty = !tooth.dentition;
  const primary = tooth.dentition === "primary";

  return (
    <button
      type="button"
      onClick={handleClick}
      title={empty ? "Bo'sh — 2 marta bosing (doimiy tish chiqadi)" : "1 marta: yo'q qilish. 2 marta: sut/doimiy almashtirish"}
      className={`flex h-11 w-9 shrink-0 select-none flex-col items-center justify-center rounded border text-xs font-semibold transition-colors ${
        empty
          ? dark
            ? "border-dashed border-white/25 bg-white/5 text-white/30 hover:border-white/50"
            : "border-dashed border-gray-300 bg-white text-gray-300 hover:border-gray-400"
          : primary
            ? dark
              ? "border-amber-400/70 bg-amber-400/15 text-amber-200 hover:bg-amber-400/25"
              : "border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100"
            : dark
              ? "border-emerald-400/60 bg-emerald-400/15 text-emerald-100 hover:bg-emerald-400/25"
              : "border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100"
      }`}
    >
      {empty ? "—" : tooth.tooth_code}
    </button>
  );
}

function Quadrant({ teeth, order, onClick, dark }: { teeth: ToothStatusOut[]; order: number[]; onClick: (position: number, clickType: "single" | "double") => void; dark: boolean }) {
  const byPosition = new Map(teeth.map((t) => [t.position, t]));
  return (
    <div className="flex gap-1">
      {order.map((pos) => {
        const tooth = byPosition.get(pos);
        if (!tooth) return null;
        return <ToothBox key={pos} tooth={tooth} dark={dark} onToothClick={(clickType) => onClick(pos, clickType)} />;
      })}
    </div>
  );
}

export function DentalChart({
  chart,
  onClick,
  onReset,
  jaw = "both",
  showReset = true,
  dark = false,
}: {
  chart: DentalChartOut;
  onClick: (quadrant: number, position: number, clickType: "single" | "double") => void;
  onReset: (dentition: "permanent" | "primary") => void;
  jaw?: "upper" | "lower" | "both";
  showReset?: boolean;
  dark?: boolean;
}) {
  const byQuadrant = (q: number) => chart.teeth.filter((t) => t.quadrant === q);
  const outward = [8, 7, 6, 5, 4, 3, 2, 1];
  const inward = [1, 2, 3, 4, 5, 6, 7, 8];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`text-xs ${dark ? "text-white/65" : "text-gray-500"}`}>
          1 marta bosish = tish yo&apos;q. 2 marta bosish = sut ↔ doimiy tish almashtirish (bo&apos;sh joyda — doimiy tish
          chiqadi).
        </p>
        {showReset && (
          <div className="flex gap-2">
            <button onClick={() => onReset("permanent")} className={`rounded-md border px-2 py-1 text-xs font-medium ${dark ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-100 hover:bg-emerald-400/20" : "border-gray-300 hover:bg-gray-50"}`}>
              Doimiy tish rejimi
            </button>
            <button onClick={() => onReset("primary")} className={`rounded-md border px-2 py-1 text-xs font-medium ${dark ? "border-amber-400/60 bg-amber-400/10 text-amber-200 hover:bg-amber-400/20" : "border-amber-300 text-amber-700 hover:bg-amber-50"}`}>
              Sut tish rejimi
            </button>
          </div>
        )}
      </div>

      <div className={`inline-flex flex-col gap-2 rounded-lg border p-3 ${dark ? "border-white/15 bg-black/15" : "border-gray-200 bg-white"}`}>
        {jaw !== "lower" && (
          <div className="flex justify-center gap-4">
            <Quadrant teeth={byQuadrant(1)} order={outward} dark={dark} onClick={(pos, ct) => onClick(1, pos, ct)} />
            <Quadrant teeth={byQuadrant(2)} order={inward} dark={dark} onClick={(pos, ct) => onClick(2, pos, ct)} />
          </div>
        )}
        {jaw === "both" && <div className={`h-px ${dark ? "bg-white/15" : "bg-gray-200"}`} />}
        {jaw !== "upper" && (
          <div className="flex justify-center gap-4">
            <Quadrant teeth={byQuadrant(4)} order={outward} dark={dark} onClick={(pos, ct) => onClick(4, pos, ct)} />
            <Quadrant teeth={byQuadrant(3)} order={inward} dark={dark} onClick={(pos, ct) => onClick(3, pos, ct)} />
          </div>
        )}
      </div>
    </div>
  );
}
