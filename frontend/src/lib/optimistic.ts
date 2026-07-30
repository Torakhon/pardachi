/**
 * Oflayn rejimda yaratilgan yozuvlarni lokal keshga qo'shish.
 *
 * Server javobi kelmasa ham foydalanuvchi o'z ma'lumotini ko'rishi kerak.
 * Keyinchalik navbat yuborilganda, keyingi GET so'rovi keshni yangilaydi.
 */

import { cacheGet, cacheSet } from './offline'
import type { MeasurementItem, Project, Room, RoomType } from '../types'

export function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  // Eski brauzerlar uchun zaxira variant
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0
    const value = char === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}

const nowIso = () => new Date().toISOString()

export function buildOptimisticProject(input: {
  id: string
  name: string
  order_number: string
  customer_name: string
  customer_phone: string
  address: string
  note: string | null
  /** Oflayn yaratilganda joriy foydalanuvchining jamoasi. */
  team_id?: string | null
  team_name?: string | null
}): Project {
  return {
    ...input,
    status: 'draft',
    status_label: 'Yangi',
    created_at: nowIso(),
    updated_at: nowIso(),
    completed_at: null,
    team_id: input.team_id ?? null,
    team: null,
    team_name: input.team_name ?? null,
    creator: null,
    rooms_count: 0,
    items_count: 0,
    photos_count: 0,
    location: null,
    rooms: [],
  }
}

export function buildOptimisticRoom(input: {
  id: string
  project_id: string
  name: string
  room_type: RoomType
  room_type_label: string
  note: string | null
  sort_order: number
}): Room {
  return {
    ...input,
    image: null,
    items: [],
    windows_count: 0,
    doors_count: 0,
    has_image: false,
    created_at: nowIso(),
    updated_at: nowIso(),
  }
}

export async function cacheProject(project: Project): Promise<void> {
  await cacheSet(`/projects/${project.id}`, project)
}

export async function cacheRoom(room: Room): Promise<void> {
  await cacheSet(`/rooms/${room.id}`, room)
  const project = await cacheGet<Project>(`/projects/${room.project_id}`)
  if (project) {
    const updated: Project = {
      ...project.data,
      rooms: [...project.data.rooms.filter((item) => item.id !== room.id), room],
      rooms_count: project.data.rooms.filter((item) => item.id !== room.id).length + 1,
    }
    await cacheSet(`/projects/${room.project_id}`, updated)
  }
}

export async function cacheItem(item: MeasurementItem): Promise<void> {
  const room = await cacheGet<Room>(`/rooms/${item.room_id}`)
  if (!room) return
  const items = [...room.data.items.filter((existing) => existing.id !== item.id), item]
  const updated: Room = {
    ...room.data,
    items,
    windows_count: items.filter((entry) => entry.item_type === 'window').length,
    doors_count: items.filter((entry) => entry.item_type === 'door').length,
  }
  await cacheSet(`/rooms/${item.room_id}`, updated)
}

export function buildOptimisticItem(input: {
  id: string
  room_id: string
  name: string
  item_type: 'window' | 'door'
  width_cm: string
  height_cm: string
  curtain_width_cm: string | null
  curtain_height_cm: string | null
  cornice_width_cm: string | null
  cornice_height_cm: string | null
  fabric_type: string | null
  curtain_model: string | null
  fabric_color: string | null
  quantity: number
  notes: string | null
  sort_order: number
}): MeasurementItem {
  const width = Number(input.width_cm) || 0
  const height = Number(input.height_cm) || 0
  return {
    ...input,
    type_label: input.item_type === 'window' ? 'Oyna' : 'Eshik',
    size_label: `${width} × ${height} sm`,
    area_m2: Number(((width * height) / 10000).toFixed(3)),
    created_at: nowIso(),
    updated_at: nowIso(),
  }
}
