/** Backend API bilan umumiy tiplar (app/schemas ga mos). */

export type UserRole = 'admin' | 'measurer'
export type ProjectStatus = 'draft' | 'in_progress' | 'completed' | 'cancelled'
export type ItemType = 'window' | 'door'
export type RoomType =
  | 'living_room'
  | 'bedroom'
  | 'kitchen'
  | 'kids_room'
  | 'hall'
  | 'corridor'
  | 'bathroom'
  | 'office'
  | 'other'
export type LocationSource = 'telegram' | 'browser' | 'manual'

export interface User {
  id: string
  telegram_id: number | null
  username: string | null
  first_name: string
  last_name: string | null
  phone: string | null
  photo_url: string | null
  role: UserRole
  role_label: string
  is_active: boolean
  language_code: string
  last_login_at: string | null
  created_at: string
  full_name: string
}

export interface UserShort {
  id: string
  first_name: string
  last_name: string | null
  username: string | null
  role: UserRole
  full_name: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RoomImage {
  id: string
  room_id: string
  url: string
  content_type: string
  size_bytes: number
  width: number | null
  height: number | null
  created_at: string
}

export interface MeasurementItem {
  id: string
  room_id: string
  name: string
  item_type: ItemType
  type_label: string
  quantity: number
  width_cm: string
  height_cm: string
  curtain_width_cm: string | null
  curtain_height_cm: string | null
  cornice_width_cm: string | null
  cornice_height_cm: string | null
  fabric_type: string | null
  curtain_model: string | null
  fabric_color: string | null
  notes: string | null
  sort_order: number
  size_label: string
  area_m2: number
  created_at: string
  updated_at: string
}

export interface Room {
  id: string
  project_id: string
  name: string
  room_type: RoomType
  room_type_label: string
  note: string | null
  sort_order: number
  image: RoomImage | null
  items: MeasurementItem[]
  windows_count: number
  doors_count: number
  has_image: boolean
  created_at: string
  updated_at: string
}

export interface ProjectLocation {
  id: string
  project_id: string
  latitude: string
  longitude: string
  accuracy_m: string | null
  source: LocationSource
  captured_at: string
  maps_url: string
}

export interface ProjectSummary {
  id: string
  name: string
  order_number: string
  customer_name: string
  customer_phone: string
  address: string
  status: ProjectStatus
  status_label: string
  created_at: string
  updated_at: string
  completed_at: string | null
  creator: UserShort | null
  rooms_count: number
  items_count: number
  photos_count: number
  location: ProjectLocation | null
}

export interface Project extends ProjectSummary {
  note: string | null
  rooms: Room[]
}

export interface PageMeta {
  total: number
  page: number
  size: number
  pages: number
}

export interface Paginated<T> {
  items: T[]
  meta: PageMeta
}

export interface DashboardStats {
  projects_total: number
  projects_draft: number
  projects_in_progress: number
  projects_completed: number
  rooms_total: number
  items_total: number
  windows_total: number
  doors_total: number
  photos_total: number
  users_total: number
  recent_projects: ProjectSummary[]
  per_measurer: { user_id: string; full_name: string; projects_count: number; completed_count: number }[]
}

export interface EnumOption {
  value: string
  label: string
}

export interface EnumsResponse {
  room_types: EnumOption[]
  item_types: EnumOption[]
  project_statuses: EnumOption[]
  user_roles: EnumOption[]
  location_sources: EnumOption[]
  fabric_types: string[]
  curtain_models: string[]
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: { fields?: Record<string, string> } & Record<string, unknown>
  }
}

export interface ProjectFormValues {
  name: string
  order_number: string
  customer_name: string
  customer_phone: string
  address: string
  note: string
}

export interface MeasurementFormValues {
  name: string
  item_type: ItemType
  width_cm: string
  height_cm: string
  curtain_width_cm: string
  curtain_height_cm: string
  cornice_width_cm: string
  cornice_height_cm: string
  fabric_type: string
  curtain_model: string
  fabric_color: string
  quantity: string
  notes: string
}
