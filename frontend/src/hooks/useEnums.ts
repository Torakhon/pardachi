import { useEffect, useState } from 'react'

import { getCached } from '../lib/api'
import type { EnumsResponse } from '../types'

const FALLBACK: EnumsResponse = {
  room_types: [
    { value: 'living_room', label: 'Mehmonxona' },
    { value: 'bedroom', label: 'Yotoqxona' },
    { value: 'kitchen', label: 'Oshxona' },
    { value: 'kids_room', label: 'Bolalar xonasi' },
    { value: 'hall', label: 'Zal' },
    { value: 'corridor', label: 'Koridor' },
    { value: 'bathroom', label: 'Hammom' },
    { value: 'office', label: 'Ish xonasi' },
    { value: 'other', label: 'Boshqa' },
  ],
  item_types: [
    { value: 'window', label: 'Oyna' },
    { value: 'door', label: 'Eshik' },
  ],
  project_statuses: [
    { value: 'draft', label: 'Yangi' },
    { value: 'in_progress', label: 'Jarayonda' },
    { value: 'completed', label: 'Yakunlangan' },
    { value: 'cancelled', label: 'Bekor qilingan' },
  ],
  user_roles: [
    { value: 'admin', label: 'Administrator' },
    { value: 'measurer', label: "O'lchovchi" },
  ],
  location_sources: [
    { value: 'telegram', label: 'Telegram' },
    { value: 'browser', label: 'Brauzer' },
    { value: 'manual', label: "Qo'lda kiritilgan" },
  ],
  fabric_types: ['Tyul', 'Blackout', 'Baxmal', 'Jakkard', "Zig'ir (len)", 'Atlas', 'Organza', 'Shifon'],
  curtain_models: ['Klassik', 'Rim pardasi', 'Rulon parda', 'Jalyuzi', 'Yapon pardasi', 'Lambrekenli'],
}

let cached: EnumsResponse | null = null

/** Ma'lumotnoma ro'yxatlari (xona turlari, matolar va h.k.). */
export function useEnums(): EnumsResponse {
  const [enums, setEnums] = useState<EnumsResponse>(cached ?? FALLBACK)

  useEffect(() => {
    if (cached) return
    let active = true
    void getCached<EnumsResponse>('/meta/enums')
      .then((result) => {
        cached = result.data
        if (active) setEnums(result.data)
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  return enums
}
