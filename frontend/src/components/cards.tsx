import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { t } from '../i18n/uz'
import { cn } from '../lib/cn'
import { formatCm, formatPhone, formatRelative } from '../lib/format'
import type { MeasurementItem, ProjectSummary, Room } from '../types'
import { IconButton } from './Button'
import { Chip, StatusBadge } from './Feedback'

export function StatCard({
  icon,
  label,
  value,
  to,
  tone = 'default',
}: {
  icon: string
  label: string
  value: ReactNode
  to?: string
  tone?: 'default' | 'brand'
}) {
  const content = (
    <div
      className={cn(
        'card tap-scale flex h-full flex-col justify-between gap-2 p-4',
        tone === 'brand' && 'border-brand-500/40',
      )}
    >
      <span className="text-2xl" aria-hidden>
        {icon}
      </span>
      <div>
        <div className="text-2xl font-bold leading-tight tabular-nums">{value}</div>
        <div className="text-xs text-hint">{label}</div>
      </div>
    </div>
  )
  return to ? (
    <Link to={to} className="block h-full">
      {content}
    </Link>
  ) : (
    content
  )
}

export function ProjectCard({ project }: { project: ProjectSummary }) {
  return (
    <Link to={`/projects/${project.id}`} className="card tap-scale block p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-[15px] font-semibold leading-tight">{project.name}</h3>
          <p className="mt-0.5 truncate text-sm text-hint">{project.customer_name}</p>
        </div>
        <StatusBadge status={project.status} label={project.status_label} />
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <Chip tone="brand">№ {project.order_number}</Chip>
        <Chip>🚪 {project.rooms_count}</Chip>
        <Chip>📏 {project.items_count}</Chip>
        {project.photos_count > 0 && <Chip>📷 {project.photos_count}</Chip>}
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-2 text-xs text-hint">
        <span className="truncate">{formatPhone(project.customer_phone)}</span>
        <span className="shrink-0">{formatRelative(project.updated_at)}</span>
      </div>
    </Link>
  )
}

export function RoomCard({
  room,
  onEdit,
  onDelete,
}: {
  room: Room
  onEdit?: () => void
  onDelete?: () => void
}) {
  return (
    <div className="card overflow-hidden">
      <Link to={`/rooms/${room.id}`} className="block">
        <div className="flex gap-3 p-3">
          {room.image ? (
            <img
              src={room.image.url}
              alt={room.name}
              loading="lazy"
              className="h-20 w-20 shrink-0 rounded-xl object-cover"
            />
          ) : (
            <div
              className="flex h-20 w-20 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border border-dashed text-[10px] text-hint"
              style={{ borderColor: 'var(--app-border)' }}
            >
              <span className="text-xl" aria-hidden>
                📷
              </span>
              {t.room.noPhoto}
            </div>
          )}

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate font-semibold leading-tight">{room.name}</h3>
                <p className="text-xs text-hint">{room.room_type_label}</p>
              </div>
              <div className="flex shrink-0 -mr-1 -mt-1">
                {onEdit && (
                  <IconButton
                    label={t.app.edit}
                    onClick={(event) => {
                      event.preventDefault()
                      onEdit()
                    }}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 20h4l10-10-4-4L4 16v4Z" strokeLinejoin="round" />
                    </svg>
                  </IconButton>
                )}
                {onDelete && (
                  <IconButton
                    label={t.app.delete}
                    tone="danger"
                    onClick={(event) => {
                      event.preventDefault()
                      onDelete()
                    }}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </IconButton>
                )}
              </div>
            </div>

            <div className="mt-2 flex flex-wrap gap-1.5">
              <Chip>🪟 {room.windows_count}</Chip>
              <Chip>🚪 {room.doors_count}</Chip>
              {!room.has_image && <Chip tone="brand">{t.room.photoRequired}</Chip>}
            </div>
          </div>
        </div>
      </Link>
    </div>
  )
}

export function MeasurementRow({
  item,
  onClick,
  onDelete,
}: {
  item: MeasurementItem
  onClick?: () => void
  onDelete?: () => void
}) {
  return (
    <div className="card flex items-center gap-3 p-3">
      <button type="button" onClick={onClick} className="flex min-w-0 flex-1 items-center gap-3 text-left">
        <span
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-lg"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
          aria-hidden
        >
          {item.item_type === 'window' ? '🪟' : '🚪'}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="truncate font-semibold">{item.name}</span>
            {item.quantity > 1 && <Chip>×{item.quantity}</Chip>}
          </span>
          <span className="mt-0.5 block truncate text-sm text-hint tabular-nums">
            {formatCm(item.width_cm)} × {formatCm(item.height_cm)} {t.app.cm}
            {item.fabric_type ? ` · ${item.fabric_type}` : ''}
            {item.fabric_color ? ` · ${item.fabric_color}` : ''}
          </span>
        </span>
      </button>
      {onDelete && (
        <IconButton label={t.app.delete} tone="danger" onClick={onDelete}>
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </IconButton>
      )}
    </div>
  )
}

export function InfoRow({ label, value, action }: { label: string; value: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5">
      <span className="shrink-0 text-sm text-hint">{label}</span>
      <span className="min-w-0 text-right text-sm font-medium">{value}</span>
      {action}
    </div>
  )
}
