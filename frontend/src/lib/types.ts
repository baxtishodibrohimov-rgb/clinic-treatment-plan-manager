export type Role = "super_admin" | "admin" | "planner" | "doctor" | "consultant";

export type CaseStatus =
  | "NEW"
  | "WAITING_ASSIGNMENT"
  | "ASSIGNED"
  | "IMAGES_READY"
  | "ANALYSIS_IN_PROGRESS"
  | "PLAN_IN_PROGRESS"
  | "REVIEW_REQUIRED"
  | "READY"
  | "CONSULTATION_COMPLETED"
  | "OVERDUE";

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  telegram_id: number | null;
  is_active: boolean;
  max_workload: number | null;
  roles: Role[];
}

export interface CaseListItem {
  id: string;
  status: CaseStatus;
  priority: string;
  consultation_datetime: string | null;
  deadline: string | null;
  images_progress_percent: number;
  patient_name: string;
  doctor_name: string | null;
  planner_name: string | null;
}

export interface DashboardStats {
  today_consultations: number;
  new_cases: number;
  in_progress: number;
  review_pending: number;
  ready: number;
  overdue: number;
}

export interface ImageTypeOut {
  id: string;
  code: string;
  label: string;
  category: string;
  is_required: boolean;
}

export interface ClinicalImageOut {
  id: string;
  image_type_id: string | null;
  external_url: string | null;
  source: string;
}

export interface FindingOut {
  id: string;
  category: string;
  description: string;
  severity: string | null;
  is_confirmed: boolean;
}

export interface AuditLogOut {
  action: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseDetail {
  id: string;
  status: CaseStatus;
  priority: string;
  consultation_datetime: string | null;
  deadline: string | null;
  images_progress_percent: number;
  patient: { cliniccards_patient_id: string; full_name: string; birth_date: string | null; phone: string | null } | null;
  doctor_name: string | null;
  planner_id: string | null;
  planner_name: string | null;
  image_types: ImageTypeOut[];
  images: ClinicalImageOut[];
  findings: FindingOut[];
  audit_log: AuditLogOut[];
}

export interface ReminderRuleOut {
  id: string;
  name: string;
  trigger_type: string;
  offset_minutes: number | null;
  notify_roles: string[];
  is_active: boolean;
  sort_order: number;
}

export interface AssignmentConfigOut {
  mode: "manual" | "auto";
  strategy: "least_workload" | "round_robin";
}

export interface SyncLogOut {
  id: string;
  sync_type: string;
  status: string;
  records_seen: number;
  cases_created: number;
  error: string | null;
}
