"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import type { AssignmentConfigOut, SyncLogOut } from "@/lib/types";

export default function SettingsPage() {
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
      </div>
    </Shell>
  );
}
