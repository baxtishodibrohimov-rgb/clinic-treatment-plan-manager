"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ClinicOut } from "@/lib/types";

interface ClinicForm {
  name: string;
  cliniccards_branch_code: string;
  is_active: boolean;
  is_default: boolean;
}

function emptyForm(): ClinicForm {
  return { name: "", cliniccards_branch_code: "", is_active: true, is_default: false };
}

function ClinicRow({ clinic, onSaved }: { clinic: ClinicOut; onSaved: () => void }) {
  const [form, setForm] = useState<ClinicForm>({
    name: clinic.name,
    cliniccards_branch_code: clinic.cliniccards_branch_code ?? "",
    is_active: clinic.is_active,
    is_default: clinic.is_default,
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/api/clinics/${clinic.id}`, {
        name: form.name,
        is_active: form.is_active,
        is_default: form.is_default,
        cliniccards_branch_code: form.cliniccards_branch_code || null,
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-b border-gray-100">
      <td className="px-3 py-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm" />
      </td>
      <td className="px-3 py-2">
        <input
          value={form.cliniccards_branch_code}
          onChange={(e) => setForm({ ...form, cliniccards_branch_code: e.target.value })}
          placeholder="—"
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
        />
      </td>
      <td className="px-3 py-2 text-center">
        <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
      </td>
      <td className="px-3 py-2 text-center">
        <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
      </td>
      <td className="px-3 py-2 text-right">
        <button onClick={save} disabled={saving} className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          Saqlash
        </button>
      </td>
    </tr>
  );
}

export default function ClinicsPage() {
  const { isSuperAdmin } = useAuth();
  const [clinics, setClinics] = useState<ClinicOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<ClinicForm>(emptyForm());
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const data = await api.get<ClinicOut[]>("/api/clinics");
    setClinics(data);
  };

  useEffect(() => {
    load()
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const createClinic = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/clinics", {
        name: form.name,
        cliniccards_branch_code: form.cliniccards_branch_code || null,
        is_default: form.is_default,
      });
      setShowCreate(false);
      setForm(emptyForm());
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    }
  };

  if (!isSuperAdmin) {
    return (
      <Shell>
        <p className="text-sm text-gray-500">Bu sahifa faqat bosh administrator uchun.</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-4">
        <Link href="/admin/settings-hub" className="text-sm text-accent hover:underline">← Sozlamalar</Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Filiallar</h1>
            <p className="text-sm text-gray-500">
              Klinika filiallarini boshqaring. Barcha filiallar bitta Cliniccards hisobidan foydalanadi — kelgan
              bemor qaysi filialga tegishli ekanini aniqlash uchun &quot;Cliniccards filial kodi&quot;ni to&apos;ldiring
              (agar noaniq bo&apos;lsa, &quot;standart&quot; qilib belgilangan filialga tushadi).
            </p>
          </div>
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 shrink-0"
          >
            + Yangi filial
          </button>
        </div>

        {showCreate && (
          <form onSubmit={createClinic} className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <div className="grid grid-cols-2 gap-3">
              <input
                required
                placeholder="Filial nomi (masalan: Chilonzor filiali)"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <input
                placeholder="Cliniccards filial kodi (ixtiyoriy)"
                value={form.cliniccards_branch_code}
                onChange={(e) => setForm({ ...form, cliniccards_branch_code: e.target.value })}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
              Standart filial (kodi mos kelmagan bemorlar shu yerga tushadi)
            </label>
            <button type="submit" className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Yaratish
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Nomi</th>
                <th className="px-3 py-2">Cliniccards filial kodi</th>
                <th className="px-3 py-2 text-center">Standart</th>
                <th className="px-3 py-2 text-center">Faol</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-gray-400">
                    Yuklanmoqda...
                  </td>
                </tr>
              )}
              {!loading && clinics.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-gray-400">
                    Filial yo&apos;q
                  </td>
                </tr>
              )}
              {clinics.map((c) => (
                <ClinicRow key={c.id} clinic={c} onSaved={load} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
