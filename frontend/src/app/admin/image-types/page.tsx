"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/shell";
import { api } from "@/lib/api";
import type { ImageTypeOut } from "@/lib/types";

export default function ImageTypesPage() {
  const [items, setItems] = useState<ImageTypeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ code: "", label: "", category: "extraoral", is_required: true });

  const load = async () => {
    const data = await api.get<ImageTypeOut[]>("/api/image-types");
    setItems(data);
  };

  useEffect(() => {
    load()
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const addType = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/api/image-types", { ...form, sort_order: items.length + 1 });
    setForm({ code: "", label: "", category: "extraoral", is_required: true });
    await load();
  };

  const toggleRequired = async (item: ImageTypeOut) => {
    await api.patch(`/api/image-types/${item.id}`, { is_required: !item.is_required });
    await load();
  };

  return (
    <Shell>
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold">Rasm turlari</h1>
          <p className="text-sm text-gray-500">Har bir bemor uchun talab qilinadigan diagnostik rasm turlari</p>
        </div>

        <form onSubmit={addType} className="rounded-lg border border-gray-200 bg-white p-4 flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Kod</label>
            <input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="face_frontal" className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Nomi</label>
            <input required value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Kategoriya</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="extraoral">extraoral</option>
              <option value="intraoral">intraoral</option>
              <option value="radiology">radiology</option>
            </select>
          </div>
          <label className="flex items-center gap-1.5 text-sm pb-2">
            <input type="checkbox" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
            Majburiy
          </label>
          <button type="submit" className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Qo&apos;shish
          </button>
        </form>

        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Kod</th>
                <th className="px-3 py-2">Nomi</th>
                <th className="px-3 py-2">Kategoriya</th>
                <th className="px-3 py-2">Majburiy</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={4} className="px-3 py-8 text-center text-gray-400">Yuklanmoqda...</td></tr>
              )}
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100">
                  <td className="px-3 py-2 font-mono text-xs">{item.code}</td>
                  <td className="px-3 py-2">{item.label}</td>
                  <td className="px-3 py-2 text-gray-500">{item.category}</td>
                  <td className="px-3 py-2">
                    <button onClick={() => toggleRequired(item)} className={`rounded px-2 py-0.5 text-xs ${item.is_required ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
                      {item.is_required ? "Majburiy" : "Ixtiyoriy"}
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
