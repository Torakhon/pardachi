import { Link, useNavigate } from 'react-router-dom'

import { Button } from '../components/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/Feedback'
import { OfflineBanner, PageHeader, Screen, Section } from '../components/Layout'
import { ProjectCard, StatCard } from '../components/cards'
import { useResource } from '../hooks/useResource'
import { t } from '../i18n/uz'
import { useAuth } from '../store/auth'
import type { DashboardStats } from '../types'

export function DashboardPage() {
  const { user, isAdmin } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, fromCache, reload } = useResource<DashboardStats>('/stats/dashboard')

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={`${t.dashboard.greeting}${user ? `, ${user.first_name}` : ''}!`}
        subtitle={isAdmin ? 'Administrator' : t.app.tagline}
      />

      {fromCache && <p className="mb-3 text-xs text-hint">{t.offline.cachedView}</p>}

      <Button fullWidth size="lg" className="mb-5" onClick={() => navigate('/projects/new')}>
        ➕ {t.dashboard.newProject}
      </Button>

      {loading && !data ? (
        <CardSkeleton count={2} />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : data ? (
        <>
          <div className="mb-5 grid grid-cols-2 gap-3">
            <StatCard icon="📁" label={t.dashboard.projects} value={data.projects_total} to="/projects" tone="brand" />
            <StatCard icon="📏" label={t.dashboard.measurements} value={data.items_total} />
            <StatCard icon="🚪" label={t.dashboard.rooms} value={data.rooms_total} />
            <StatCard icon="📷" label={t.dashboard.photos} value={data.photos_total} />
          </div>

          <Section title={t.filters.status}>
            <div className="card divide-y" style={{ borderColor: 'var(--app-border)' }}>
              <StatusRow
                label={t.dashboard.draft}
                value={data.projects_draft}
                to="/projects?status=draft"
                dot="bg-slate-400"
              />
              <StatusRow
                label={t.dashboard.inProgress}
                value={data.projects_in_progress}
                to="/projects?status=in_progress"
                dot="bg-warning"
              />
              <StatusRow
                label={t.dashboard.completed}
                value={data.projects_completed}
                to="/projects?status=completed"
                dot="bg-success"
              />
            </div>
          </Section>

          <Section
            title={`🕒 ${t.dashboard.recent}`}
            action={
              <Link to="/projects" className="text-sm font-semibold text-brand-600">
                {t.dashboard.viewAll}
              </Link>
            }
          >
            {data.recent_projects.length === 0 ? (
              <div className="card">
                <EmptyState
                  icon="📁"
                  title={t.dashboard.emptyRecent}
                  action={
                    <Button size="sm" onClick={() => navigate('/projects/new')}>
                      {t.dashboard.newProject}
                    </Button>
                  }
                />
              </div>
            ) : (
              <div className="space-y-3">
                {data.recent_projects.map((project) => (
                  <ProjectCard key={project.id} project={project} />
                ))}
              </div>
            )}
          </Section>

          {isAdmin && data.per_measurer.length > 0 && (
            <Section title={t.dashboard.staff}>
              <div className="card divide-y" style={{ borderColor: 'var(--app-border)' }}>
                {data.per_measurer.map((row) => (
                  <div key={row.user_id} className="flex items-center justify-between gap-3 px-4 py-3">
                    <span className="min-w-0 truncate text-sm font-medium">{row.full_name}</span>
                    <span className="shrink-0 text-sm text-hint tabular-nums">
                      {row.projects_count} / <span className="text-success">{row.completed_count}</span>
                    </span>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </>
      ) : null}
    </Screen>
  )
}

function StatusRow({ label, value, to, dot }: { label: string; value: number; to: string; dot: string }) {
  return (
    <Link to={to} className="tap-scale flex items-center justify-between gap-3 px-4 py-3.5">
      <span className="flex items-center gap-2.5 text-sm font-medium">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
        {label}
      </span>
      <span className="text-sm font-bold tabular-nums">{value}</span>
    </Link>
  )
}
