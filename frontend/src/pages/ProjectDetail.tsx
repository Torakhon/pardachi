import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button, IconButton } from '../components/Button'
import { CardSkeleton, Chip, ErrorState, StatusBadge } from '../components/Feedback'
import { OfflineBanner, PageHeader, Screen, Section } from '../components/Layout'
import { ConfirmDialog } from '../components/Sheet'
import { InfoRow, RoomCard } from '../components/cards'
import { EmptyState } from '../components/Feedback'
import { useResource } from '../hooks/useResource'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { ApiError, QueuedError, api } from '../lib/api'
import { formatDateTime, formatPhone } from '../lib/format'
import { getCurrentLocation, openExternal } from '../lib/telegram'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'
import type { Project } from '../types'

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { isAdmin, canWrite, user: currentUser } = useAuth()
  useTelegramBack('/projects')

  const { data: project, loading, error, fromCache, reload } = useResource<Project>(
    projectId ? `/projects/${projectId}` : null,
  )

  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmFinish, setConfirmFinish] = useState(false)
  const [roomToDelete, setRoomToDelete] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [locating, setLocating] = useState(false)

  if (loading && !project) {
    return (
      <Screen>
        <PageHeader title={t.app.loading} back="/projects" />
        <CardSkeleton count={3} />
      </Screen>
    )
  }

  if (error && !project) {
    return (
      <Screen>
        <PageHeader title={t.project.summary} back="/projects" />
        <ErrorState message={error} onRetry={() => void reload()} />
      </Screen>
    )
  }

  if (!project) return null

  const changeStatus = async (status: 'completed' | 'in_progress') => {
    setBusy(true)
    try {
      await api.patch(`/projects/${project.id}/status`, { status }, { label: `${project.name}: ${status}` })
      toast.success(status === 'completed' ? t.project.finished : t.project.reopened)
      await reload()
    } catch (caught) {
      if (caught instanceof QueuedError) toast.warning(t.offline.savedLocally)
      else if (caught instanceof ApiError) toast.error(caught.message)
      else toast.error(t.app.somethingWrong)
    } finally {
      setBusy(false)
      setConfirmFinish(false)
    }
  }

  const removeProject = async () => {
    setBusy(true)
    try {
      await api.delete(`/projects/${project.id}`, { label: `${t.app.delete}: ${project.name}` })
      toast.success(t.project.deleted)
      navigate('/projects', { replace: true })
    } catch (caught) {
      if (caught instanceof QueuedError) {
        toast.warning(t.offline.savedLocally)
        navigate('/projects', { replace: true })
      } else {
        toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
      }
    } finally {
      setBusy(false)
      setConfirmDelete(false)
    }
  }

  const removeRoom = async (roomId: string) => {
    setBusy(true)
    try {
      await api.delete(`/rooms/${roomId}`, { label: `${t.app.delete}: ${t.room.newTitle}` })
      toast.success(t.room.deleted)
      await reload()
    } catch (caught) {
      if (caught instanceof QueuedError) toast.warning(t.offline.savedLocally)
      else toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
      setRoomToDelete(null)
    }
  }

  const captureLocation = async () => {
    setLocating(true)
    try {
      const result = await getCurrentLocation()
      await api.post(
        `/projects/${project.id}/location`,
        {
          latitude: result.latitude.toFixed(6),
          longitude: result.longitude.toFixed(6),
          accuracy_m: result.accuracy ? result.accuracy.toFixed(2) : null,
          source: result.source,
        },
        { label: `${t.project.location}: ${project.name}` },
      )
      toast.success(t.project.locationSaved)
      await reload()
    } catch (caught) {
      if (caught instanceof QueuedError) toast.warning(t.offline.savedLocally)
      else toast.error(t.project.locationError)
    } finally {
      setLocating(false)
    }
  }

  const completed = project.status === 'completed'
  // Administrator hamma obyektni, o'lchovchi faqat o'zi yaratganini tahrirlaydi.
  const canEdit = isAdmin || (canWrite && project.creator?.id === currentUser?.id)

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={project.name}
        subtitle={`№ ${project.order_number}`}
        back="/projects"
        action={
          canEdit ? (
          <div className="flex">
            <IconButton label={t.app.edit} onClick={() => navigate(`/projects/${project.id}/edit`)}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" strokeLinejoin="round" />
              </svg>
            </IconButton>
            <IconButton label={t.app.delete} tone="danger" onClick={() => setConfirmDelete(true)}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </IconButton>
          </div>
          ) : undefined
        }
      />

      {fromCache && <p className="mb-3 text-xs text-hint">{t.offline.cachedView}</p>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <StatusBadge status={project.status} label={project.status_label} />
        <Chip>🚪 {project.rooms_count}</Chip>
        <Chip>📏 {project.items_count}</Chip>
        <Chip>📷 {project.photos_count}</Chip>
      </div>

      <Section title={t.project.summary}>
        <div className="card divide-y px-4" style={{ borderColor: 'var(--app-border)' }}>
          <InfoRow label={t.project.customerName} value={project.customer_name} />
          <InfoRow
            label={t.project.phone}
            value={
              <a href={`tel:${project.customer_phone}`} className="text-brand-600">
                {formatPhone(project.customer_phone)}
              </a>
            }
          />
          {project.address && <InfoRow label={t.project.address} value={project.address} />}
          {project.note && <InfoRow label={t.project.note} value={project.note} />}
          <InfoRow label={t.project.createdBy} value={project.creator?.full_name ?? '—'} />
          <InfoRow label={t.project.createdAt} value={formatDateTime(project.created_at)} />
          {project.completed_at && (
            <InfoRow label={t.project.completedAt} value={formatDateTime(project.completed_at)} />
          )}
          <InfoRow
            label={t.project.location}
            value={
              project.location ? (
                <button type="button" className="text-brand-600" onClick={() => openExternal(project.location!.maps_url)}>
                  {t.project.openMap} ↗
                </button>
              ) : (
                <Button size="sm" variant="ghost" loading={locating} onClick={() => void captureLocation()}>
                  {t.project.captureLocation}
                </Button>
              )
            }
          />
        </div>
      </Section>

      <Section
        title={`${t.project.rooms} (${project.rooms.length})`}
        action={
          canEdit ? (
            <Button size="sm" variant="ghost" onClick={() => navigate(`/projects/${project.id}/rooms/new`)}>
              ➕ {t.project.addRoom}
            </Button>
          ) : undefined
        }
      >
        {project.rooms.length === 0 ? (
          <div className="card">
            <EmptyState
              icon="🚪"
              title={t.project.emptyRooms}
              description={t.room.photoHint}
              action={
                canEdit ? (
                  <Button size="sm" onClick={() => navigate(`/projects/${project.id}/rooms/new`)}>
                    {t.project.addRoom}
                  </Button>
                ) : undefined
              }
            />
          </div>
        ) : (
          <div className="space-y-3">
            {project.rooms.map((room) => (
              <RoomCard
                key={room.id}
                room={room}
                onEdit={canEdit ? () => navigate(`/rooms/${room.id}/edit`) : undefined}
                onDelete={canEdit ? () => setRoomToDelete(room.id) : undefined}
              />
            ))}
          </div>
        )}
      </Section>

      <div className="space-y-3">
        {canEdit && (
          <Button fullWidth size="lg" onClick={() => navigate(`/projects/${project.id}/rooms/new`)}>
            ➕ {t.project.addRoom}
          </Button>
        )}

        {completed ? (
          <Button
            fullWidth
            size="lg"
            variant="secondary"
            loading={busy}
            onClick={() => void changeStatus('in_progress')}
          >
            {t.project.reopen}
          </Button>
        ) : (
          <Button
            fullWidth
            size="lg"
            variant="success"
            disabled={project.rooms.length === 0}
            onClick={() => setConfirmFinish(true)}
          >
            ✓ {t.project.finish}
          </Button>
        )}

        {isAdmin && project.items_count > 0 && (
          <Button
            fullWidth
            variant="ghost"
            onClick={() => navigate(`/projects/${project.id}/measurements`)}
          >
            {t.project.measurementsAll}
          </Button>
        )}
      </div>

      <ConfirmDialog
        open={confirmDelete}
        message={t.project.deleteConfirm}
        loading={busy}
        onConfirm={() => void removeProject()}
        onCancel={() => setConfirmDelete(false)}
      />

      <ConfirmDialog
        open={confirmFinish}
        title={t.project.finish}
        message={t.project.finishConfirm}
        confirmLabel={t.project.finish}
        tone="primary"
        loading={busy}
        onConfirm={() => void changeStatus('completed')}
        onCancel={() => setConfirmFinish(false)}
      />

      <ConfirmDialog
        open={roomToDelete !== null}
        message={t.room.deleteConfirm}
        loading={busy}
        onConfirm={() => roomToDelete && void removeRoom(roomToDelete)}
        onCancel={() => setRoomToDelete(null)}
      />
    </Screen>
  )
}
