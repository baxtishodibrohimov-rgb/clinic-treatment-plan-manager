"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/shell";
import { api } from "@/lib/api";
import type { ReminderRuleOut } from "@/lib/types";

export default function RemindersPage() {
  const [rules, setRules] = useState<ReminderRuleOut[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const data = await api.get<ReminderRuleOut[]>("/api/reminder-rules");
    setRules(data);
  };

  useEffect(() => {
    load()
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const updateOffset = async (rule: ReminderRuleOut, minutes: number) => {
    await api.patch(`/api/reminder-rules/${rule.id}`, { offset_minutes: minutes });
    await load();
  };

  const toggleActive = async (rule: ReminderRuleOut) => {
    await api.patch(`/api/reminder-rules/${rule.id}`, { is_active: !rule.is_active });
    await load();
  };

  return (
    <Shell>
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold">Eslatma qoidalari</h1>
          <p className="text-sm text-gray-500">Qachon va kimga Telegram eslatma yuborilishini boshqaring</p>
        </div>

        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Nomi</th>
                <th className="px-3 py-2">Trigger</th>
                <th className="px-3 py-2">Necha daqiqa oldin</th>
                <th className="px-3 py-2">Kimga</th>
                <th className="px-3 py-2">Faol</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={5} className="px-3 py-8 text-center text-gray-400">Yuklanmoqda...</td></tr>
              )}
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-gray-100">
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2 text-gray-500">{r.trigger_type}</td>
                  <td className="px-3 py-2">
                    {r.trigger_type === "before_consultation" ? (
                      <input
                        type="number"
                        defaultValue={r.offset_minutes ?? 0}
                        onBlur={(e) => updateOffset(r, Number(e.target.value))}
                        className="w-24 rounded border border-gray-300 px-2 py-1 text-sm"
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-500">{r.notify_roles.join(", ")}</td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => toggleActive(r)}
                      className={`rounded px-2 py-0.5 text-xs ${r.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                    >
                      {r.is_active ? "Faol" : "O'chiq"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
