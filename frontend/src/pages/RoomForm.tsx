import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button, StickyAction } from '../components/Button'
import { FullScreenLoader } from '../components/Feedback'
import { Input, Select, TextArea } from '../components/Input'
import { PageHeader, Screen, Section } from '../components/Layout'
import { useEnums } from '../hooks/useEnums'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { ApiError, QueuedError, api } from '../lib/api'
import { cn } from '../lib/cn'
import { buildOptimisticRoom, cacheRoom, newId } from '../lib/optimistic'
import { haptic } from '../lib/telegram'
import { useToast } from '../store/toast'
import type { Room, RoomType } from '../types'

const PRESETS: { name: string; type: RoomType; icon: string }[] = [
  { name: 'Mehmonxona', type: 'living_room', icon: '🛋️' },
  { name: 'Yotoqxona', type: 'bedroom', icon: '🛏️' },
  { name: 'Oshxona', type: 'kitchen', icon: '🍳' },
  { name: 'Bolalar xonasi', type: 'kids_room', icon: '🧸' },
  { name: 'Zal', type: 'hall', icon: '🏛️' },
  { name: 'Koridor', type: 'corridor', icon: '🚪' },
  { name: 'Hammom', type: 'bathroom', icon: '🚿' },
  { name: 'Ish xonasi', type: 'office', icon: '💼' },
]

export function RoomFormPage({ mode }: { mode: 'create' | 'edit' }) {
  const { projectId, roomId } = useParams<{ projectId: string; roomId: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const enums = useEnums()

  const [name, setName] = useState('')
  const [roomType, setRoomType] = useState<RoomType>('other')
  const [note, setNote] = useState('')
  const [ownerProjectId, setOwnerProjectId] = useState<string | null>(projectId ?? null)
  const [loading, setLoading] = useState(mode === 'edit')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useTelegramBack(mode === 'edit' ? `/rooms/${roomId}` : `/projects/${projectId}`)

  useEffect(() => {
    if (mode !== 'edit' || !roomId) return
    let active = true
    void api
      .get<Room>(`/rooms/${roomId}`)
      .then((room) => {
        if (!active) return
        setName(room.name)
        setRoomType(room.room_type)
        setNote(room.note ?? '')
        setOwnerProjectId(room.project_id)
      })
      .catch((caught: unknown) => toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [mode, roomId, toast])

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    haptic.select()
    setName(preset.name)
    setRoomType(preset.type)
    setError('')
  }

  const submit = async () => {
    if (!name.trim()) {
      setError(t.validation.required)
      haptic.error()
      return
    }
    setSaving(true)

    const payload = { name: name.trim(), room_type: roomType, note: note.trim() || null }

    try {
      if (mode === 'edit' && roomId) {
        await api.patch<Room>(`/rooms/${roomId}`, payload, { label: `${t.room.editTitle}: ${payload.name}` })
        toast.success(t.room.updated)
        navigate(`/rooms/${roomId}`, { replace: true })
        return
      }

      if (!projectId) return
      const id = newId()
      try {
        const room = await api.post<Room>(`/projects/${projectId}/rooms`, { ...payload, id }, {
          label: `${t.room.newTitle}: ${payload.name}`,
        })
        toast.success(t.room.created)
        navigate(`/rooms/${room.id}`, { replace: true })
      } catch (caught) {
        if (caught instanceof QueuedError) {
          await cacheRoom(
            buildOptimisticRoom({
              id,
              project_id: projectId,
              name: payload.name,
              room_type: roomType,
              room_type_label: enums.room_types.find((option) => option.value === roomType)?.label ?? '',
              note: payload.note,
              sort_order: 0,
            }),
          )
          toast.warning(t.offline.savedLocally)
          navigate(`/rooms/${id}`, { replace: true })
          return
        }
        throw caught
      }
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.fields.name ?? '')
        toast.error(caught.message)
      } else {
        toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <FullScreenLoader />

  return (
    <Screen>
      <PageHeader
        title={mode === 'create' ? t.room.newTitle : t.room.editTitle}
        back={mode === 'edit' ? `/rooms/${roomId}` : `/projects/${ownerProjectId ?? ''}`}
      />

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        {mode === 'create' && (
          <Section title={t.room.quickAdd}>
            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  className={cn(
                    'card tap-scale flex items-center gap-2 px-3 py-3 text-left text-sm font-medium',
                    name === preset.name && 'border-brand-500 text-brand-600',
                  )}
                >
                  <span className="text-xl" aria-hidden>
                    {preset.icon}
                  </span>
                  {preset.name}
                </button>
              ))}
            </div>
          </Section>
        )}

        <Input
          label={t.room.name}
          required
          value={name}
          error={error}
          placeholder={t.room.namePlaceholder}
          onChange={(event) => {
            setName(event.target.value)
            setError('')
          }}
        />

        <Select
          label={t.room.type}
          value={roomType}
          options={enums.room_types}
          onChange={(event) => setRoomType(event.target.value as RoomType)}
        />

        <TextArea label={t.room.note} value={note} onChange={(event) => setNote(event.target.value)} />

        <StickyAction>
          <Button type="submit" fullWidth size="lg" loading={saving}>
            {mode === 'create' ? t.app.add : t.app.save}
          </Button>
        </StickyAction>
      </form>
    </Screen>
  )
}
