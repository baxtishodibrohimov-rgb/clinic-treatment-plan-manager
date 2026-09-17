"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AssignmentConfigOut, SyncLogOut } from "@/lib/types";

const RESET_CONFIRM_PHRASE = "HAMMASINI TOZALA";

function DangerZone() {
  const [confirmText, setConfirmText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const reset = async () => {
    if (confirmText !== RESET_CONFIRM_PHRASE) return;
    if (!window.confirm("Haqiqatan ham BARCHA bemor/case ma'lumotlarini butunlay o'chirmoqchimisiz? Bu amalni ORQAGA QAYTARIB BO'LMAYDI.")) {
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      await api.post("/api/settings/reset-patient-data", { confirm_phrase: confirmText });
      setResult("Barcha bemor/case ma'lumotlari o'chirildi. Cliniccardsdan qaytadan sync qiling.");
      setConfirmText("");
    } catch (e) {
      setResult(e instanceof ApiError ? e.message : "Xatolik");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border-2 border-status-other bg-status-other-bg p-4 space-y-3">
      <h2 className="font-semibold text-status-other">Xavfli zona</h2>
      <p className="text-sm text-status-other">
        Barcha case&apos;lar, bemorlar, rasmlar, tahlil javoblari, muammolar ro&apos;yxati va tarix butunlay
        o&apos;chiriladi. Xodimlar, klinikalar, rasm turlari va savolnoma saqlanib qoladi. Bu amalni ORQAGA
        QAYTARIB BO&apos;LMAYDI.
      </p>
      {result && <div className="rounded-md bg-white px-3 py-2 text-sm text-status-other">{result}</div>}
      <div className="space-y-1">
        <label className="text-xs font-medium text-status-other">
          Davom etish uchun aniq shu matnni yozing: <span className="font-mono">{RESET_CONFIRM_PHRASE}</span>
        </label>
        <input
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          className="w-full max-w-sm rounded-md border border-status-other px-3 py-2 text-sm"
        />
      </div>
      <button
        onClick={reset}
        disabled={busy || confirmText !== RESET_CONFIRM_PHRASE}
        className="rounded-md bg-status-other px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        {busy ? "..." : "Barcha bemor ma'lumotlarini o'chirish"}
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { isSuperAdmin } = useAuth();
  const [config, setConfig] = useState<AssignmentConfigOut | null>(null);
  const [log, setLog] = useState<SyncLogOut[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const [c, l] = await Promise.all([
      api.get<AssignmentConfigOut>("/api/settings/assignment-config"),
      api.get<SyncLogOut[]>("/api/settings/sync-log"),
    ]);
    setConfig(c);
    setLog(l);
  };

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const updateConfig = async (patch: Partial<AssignmentConfigOut>) => {
    if (!config) return;
    const next = { ...config, ...patch };
    await api.put("/api/settings/assignment-config", next);
    await load();
  };

  const syncNow = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await api.post<{ cases_created: number; records_seen: number }>("/api/settings/sync-now");
      setMessage(`Sync tugadi: ${res.cases_created} yangi case, ${res.records_seen} appointment ko'rildi`);
      await load();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Xatolik");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <Shell>
      <div className="space-y-6">
        <Link href="/admin/settings-hub" className="text-sm text-accent hover:underline">← Sozlamalar</Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Tizim sozlamalari</h1>
            <p className="text-sm text-gray-500">
              Cliniccards API kaliti va Telegram token bu yerda emas — ular faqat backend environment
              o&apos;zgaruvchisi sifatida saqlanadi.
            </p>
          </div>
          <button
            onClick={syncNow}
            disabled={syncing}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "..." : "Cliniccards sync"}
          </button>
        </div>

        {message && <div className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}

        {config && (
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="font-semibold">Biriktirish algoritmi</h2>
            <div className="flex flex-wrap gap-4">
              <div className="space-y-1">
                <label className="text-xs text-gray-500">Rejim</label>
                <select
                  value={config.mode}
                  onChange={(e) => updateConfig({ mode: e.target.value as AssignmentConfigOut["mode"] })}
                  className="block rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="manual">Manual (qo&apos;lda)</option>
                  <option value="auto">Auto (avtomatik)</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-500">Strategiya</label>
                <select
                  value={config.strategy}
                  onChange={(e) => updateConfig({ strategy: e.target.value as AssignmentConfigOut["strategy"] })}
                  className="block rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="least_workload">Eng kam workload&apos;li planner</option>
                  <option value="round_robin">Round-robin</option>
                </select>
              </div>
            </div>
          </div>
        )}

        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-semibold mb-3">Sync log</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-1">Turi</th>
                <th className="py-1">Status</th>
                <th className="py-1">Ko&apos;rilgan</th>
                <th className="py-1">Yaratilgan</th>
                <th className="py-1">Xato</th>
              </tr>
            </thead>
            <tbody>
              {log.length === 0 && (
                <tr><td colSpan={5} className="py-4 text-center text-gray-400">Hali sync bo&apos;lmagan</td></tr>
              )}
              {log.map((l) => (
                <tr key={l.id} className="border-t border-gray-100">
                  <td className="py-1.5">{l.sync_type}</td>
                  <td className="py-1.5">
                    <span className={`rounded px-1.5 py-0.5 text-xs ${l.status === "success" ? "bg-green-100 text-green-700" : l.status === "error" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {l.status}
                    </span>
                  </td>
                  <td className="py-1.5">{l.records_seen}</td>
                  <td className="py-1.5">{l.cases_created}</td>
                  <td className="py-1.5 text-red-600 text-xs truncate max-w-xs">{l.error ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {isSuperAdmin && <DangerZone />}
      </div>
    </Shell>
  );
}
