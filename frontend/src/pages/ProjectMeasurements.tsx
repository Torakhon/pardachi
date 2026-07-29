import { useParams } from 'react-router-dom'

import { CardSkeleton, Chip, EmptyState, ErrorState } from '../components/Feedback'
import { PageHeader, Screen } from '../components/Layout'
import { useResource } from '../hooks/useResource'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { formatCm } from '../lib/format'
import type { MeasurementItem } from '../types'

/** Tikuv bo'limi uchun obyektdagi barcha o'lchovlar jadvali. */
export function ProjectMeasurementsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  useTelegramBack(`/projects/${projectId}`)

  const { data, loading, error, reload } = useResource<MeasurementItem[]>(
    projectId ? `/projects/${projectId}/measurements` : null,
  )

  return (
    <Screen>
      <PageHeader
        title={t.project.measurementsAll}
        subtitle={data ? `${data.length} ta o‘lchov` : undefined}
        back={`/projects/${projectId}`}
      />

      {loading && !data ? (
        <CardSkeleton count={4} />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : !data || data.length === 0 ? (
        <EmptyState icon="📏" title={t.room.emptyItems} />
      ) : (
        <div className="space-y-2.5">
          {data.map((item) => (
            <div key={item.id} className="card space-y-2 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold">
                    {item.item_type === 'window' ? '🪟' : '🚪'} {item.name}
                  </h3>
                  <p className="text-sm text-hint tabular-nums">
                    {formatCm(item.width_cm)} × {formatCm(item.height_cm)} {t.app.cm} · {item.area_m2} m²
                  </p>
                </div>
                {item.quantity > 1 && <Chip>×{item.quantity}</Chip>}
              </div>

              <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-sm">
                <Row label={t.measurement.curtain} value={pair(item.curtain_width_cm, item.curtain_height_cm)} />
                <Row label={t.measurement.cornice} value={pair(item.cornice_width_cm, item.cornice_height_cm)} />
                <Row label={t.measurement.fabricType} value={item.fabric_type} />
                <Row label={t.measurement.curtainModel} value={item.curtain_model} />
                <Row label={t.measurement.fabricColor} value={item.fabric_color} />
              </dl>

              {item.notes && <p className="text-sm text-hint">📝 {item.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </Screen>
  )
}

function pair(width: string | null, height: string | null): string | null {
  if (!width && !height) return null
  return `${width ? formatCm(width) : '—'} × ${height ? formatCm(height) : '—'}`
}

function Row({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-hint">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  )
}
