"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { onScopeClinicChange, withClinicScope } from "@/lib/clinic-scope";
import type { ClinicOut, Role, UserOut } from "@/lib/types";

const TP_ROLES: Role[] = ["planner", "doctor", "consultant"];

function StaffRow({ user, showClinic, onSaved }: { user: UserOut; showClinic: boolean; onSaved: () => void }) {
  const [roles, setRoles] = useState<Set<Role>>(new Set(user.roles));
  const [maxWorkload, setMaxWorkload] = useState<string>(user.max_workload?.toString() ?? "");
  const [saving, setSaving] = useState(false);

  const toggle = (role: Role, checked: boolean) => {
    setRoles((prev) => {
      const next = new Set(prev);
      if (checked) next.add(role);
      else next.delete(role);
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.patch(`/api/users/${user.id}/roles`, {
        roles: Array.from(roles),
        max_workload: maxWorkload === "" ? null : Number(maxWorkload),
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-b border-gray-100">
      <td className="px-3 py-2 font-medium">{user.full_name}</td>
      <td className="px-3 py-2 text-gray-500">{user.email}</td>
      {showClinic && <td className="px-3 py-2 text-gray-500">{user.clinic?.name ?? "—"}</td>}
      {TP_ROLES.map((role) => (
        <td key={role} className="px-3 py-2 text-center">
          <input type="checkbox" checked={roles.has(role)} onChange={(e) => toggle(role, e.target.checked)} />
        </td>
      ))}
      <td className="px-3 py-2">
        <input
          type="number"
          placeholder="∞"
          value={maxWorkload}
          onChange={(e) => setMaxWorkload(e.target.value)}
          className="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
        />
      </td>
      <td className="px-3 py-2 text-right">
        <button
          onClick={save}
          disabled={saving}
          className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Saqlash
        </button>
      </td>
    </tr>
  );
}

export default function StaffPage() {
  const { isSuperAdmin } = useAuth();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [clinics, setClinics] = useState<ClinicOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", telegram_id: "", roles: [] as Role[], clinic_id: "" });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const data = await api.get<UserOut[]>(withClinicScope("/api/users"));
    setUsers(data);
  };

  useEffect(() => {
    load()
      .catch(() => {})
      .finally(() => setLoading(false));
    const unsubscribe = onScopeClinicChange(() => load().catch(() => {}));
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (isSuperAdmin) {
      api
        .get<ClinicOut[]>("/api/clinics")
        .then(setClinics)
        .catch(() => {});
    }
  }, [isSuperAdmin]);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/users", {
        ...form,
        telegram_id: form.telegram_id ? Number(form.telegram_id) : null,
        clinic_id: form.clinic_id || null,
      });
      setShowCreate(false);
      setForm({ email: "", password: "", full_name: "", telegram_id: "", roles: [], clinic_id: "" });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    }
  };

  return (
    <Shell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Xodimlar va rollar</h1>
            <p className="text-sm text-gray-500">Planner / Doctor / Consultant rolini va workload limitini belgilang</p>
          </div>
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Yangi xodim
          </button>
        </div>

        {showCreate && (
          <form onSubmit={createUser} className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <div className="grid grid-cols-2 gap-3">
              <input required placeholder="F.I.Sh" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
              <input required type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
              <input required type="password" placeholder="Parol" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
              <input placeholder="Telegram ID" value={form.telegram_id} onChange={(e) => setForm({ ...form, telegram_id: e.target.value })} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
              {isSuperAdmin && (
                <select
                  required
                  value={form.clinic_id}
                  onChange={(e) => setForm({ ...form, clinic_id: e.target.value })}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">Filialni tanlang</option>
                  {clinics.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="flex gap-4 text-sm">
              {TP_ROLES.map((role) => (
                <label key={role} className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={form.roles.includes(role)}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        roles: e.target.checked ? [...form.roles, role] : form.roles.filter((r) => r !== role),
                      })
                    }
                  />
                  {role}
                </label>
              ))}
            </div>
            <button type="submit" className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Yaratish
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">F.I.Sh</th>
                <th className="px-3 py-2">Email</th>
                {isSuperAdmin && <th className="px-3 py-2">Filial</th>}
                <th className="px-3 py-2 text-center">Planner</th>
                <th className="px-3 py-2 text-center">Doctor</th>
                <th className="px-3 py-2 text-center">Consultant</th>
                <th className="px-3 py-2">Max workload</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={isSuperAdmin ? 8 : 7} className="px-3 py-8 text-center text-gray-400">
                    Yuklanmoqda...
                  </td>
                </tr>
              )}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={isSuperAdmin ? 8 : 7} className="px-3 py-8 text-center text-gray-400">
                    Xodim yo&apos;q
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <StaffRow key={u.id} user={u} showClinic={isSuperAdmin} onSaved={load} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
