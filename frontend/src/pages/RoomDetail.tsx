import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button, IconButton } from '../components/Button'
import { CardSkeleton, Chip, EmptyState, ErrorState } from '../components/Feedback'
import { OfflineBanner, PageHeader, Screen, Section } from '../components/Layout'
import { PhotoPicker } from '../components/PhotoPicker'
import { ConfirmDialog } from '../components/Sheet'
import { MeasurementRow } from '../components/cards'
import { useResource } from '../hooks/useResource'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { QueuedError, api } from '../lib/api'
import { useToast } from '../store/toast'
import type { Room, RoomImage } from '../types'

export function RoomDetailPage() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const { data: room, loading, error, fromCache, reload, setData } = useResource<Room>(
    roomId ? `/rooms/${roomId}` : null,
  )
  const [itemToDelete, setItemToDelete] = useState<string | null>(null)
  const [confirmRoomDelete, setConfirmRoomDelete] = useState(false)
  const [busy, setBusy] = useState(false)

  useTelegramBack(room ? `/projects/${room.project_id}` : '/projects')

  if (loading && !room) {
    return (
      <Screen>
        <PageHeader title={t.app.loading} back />
        <CardSkeleton count={2} />
      </Screen>
    )
  }

  if (error && !room) {
    return (
      <Screen>
        <PageHeader title={t.room.editTitle} back />
        <ErrorState message={error} onRetry={() => void reload()} />
      </Screen>
    )
  }

  if (!room || !roomId) return null

  const onImageChange = (image: RoomImage | null) => {
    setData((previous) => (previous ? { ...previous, image, has_image: image !== null } : previous))
  }

  const deleteItem = async (itemId: string) => {
    setBusy(true)
    try {
      await api.delete(`/measurements/${itemId}`, { label: `${t.app.delete}: ${t.measurement.newTitle}` })
      toast.success(t.measurement.deleted)
      await reload()
    } catch (caught) {
      if (caught instanceof QueuedError) toast.warning(t.offline.savedLocally)
      else toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
      setItemToDelete(null)
    }
  }

  const deleteRoom = async () => {
    setBusy(true)
    try {
      await api.delete(`/rooms/${roomId}`, { label: `${t.app.delete}: ${room.name}` })
      toast.success(t.room.deleted)
      navigate(`/projects/${room.project_id}`, { replace: true })
    } catch (caught) {
      if (caught instanceof QueuedError) {
        toast.warning(t.offline.savedLocally)
        navigate(`/projects/${room.project_id}`, { replace: true })
      } else {
        toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
      }
    } finally {
      setBusy(false)
      setConfirmRoomDelete(false)
    }
  }

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={room.name}
        subtitle={room.room_type_label}
        back={`/projects/${room.project_id}`}
        action={
          <div className="flex">
            <IconButton label={t.app.edit} onClick={() => navigate(`/rooms/${room.id}/edit`)}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" strokeLinejoin="round" />
              </svg>
            </IconButton>
            <IconButton label={t.app.delete} tone="danger" onClick={() => setConfirmRoomDelete(true)}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </IconButton>
          </div>
        }
      />

      {fromCache && <p className="mb-3 text-xs text-hint">{t.offline.cachedView}</p>}

      <Section title={t.room.photo}>
        <PhotoPicker roomId={room.id} image={room.image} onUploaded={onImageChange} />
      </Section>

      {room.note && (
        <Section title={t.room.note}>
          <p className="card p-4 text-sm leading-relaxed">{room.note}</p>
        </Section>
      )}

      <Section
        title={`${t.room.items} (${room.items.length})`}
        action={
          <span className="flex gap-1.5">
            <Chip>🪟 {room.windows_count}</Chip>
            <Chip>🚪 {room.doors_count}</Chip>
          </span>
        }
      >
        {room.items.length === 0 ? (
          <div className="card">
            <EmptyState icon="📏" title={t.room.emptyItems} description={t.measurement.hint} />
          </div>
        ) : (
          <div className="space-y-2.5">
            {room.items.map((item) => (
              <MeasurementRow
                key={item.id}
                item={item}
                onClick={() => navigate(`/measurements/${item.id}/edit`)}
                onDelete={() => setItemToDelete(item.id)}
              />
            ))}
          </div>
        )}
      </Section>

      <div className="grid grid-cols-2 gap-3">
        <Button size="lg" onClick={() => navigate(`/rooms/${room.id}/items/new?type=window`)}>
          🪟 {t.room.addWindow}
        </Button>
        <Button size="lg" variant="secondary" onClick={() => navigate(`/rooms/${room.id}/items/new?type=door`)}>
          🚪 {t.room.addDoor}
        </Button>
      </div>

      <ConfirmDialog
        open={itemToDelete !== null}
        message={t.measurement.deleteConfirm}
        loading={busy}
        onConfirm={() => itemToDelete && void deleteItem(itemToDelete)}
        onCancel={() => setItemToDelete(null)}
      />

      <ConfirmDialog
        open={confirmRoomDelete}
        message={t.room.deleteConfirm}
        loading={busy}
        onConfirm={() => void deleteRoom()}
        onCancel={() => setConfirmRoomDelete(false)}
      />
    </Screen>
  )
}
