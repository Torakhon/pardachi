import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { Button } from '../components/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/Feedback'
import { Select } from '../components/Input'
import { OfflineBanner, PageHeader, Screen } from '../components/Layout'
import { Sheet } from '../components/Sheet'
import { ProjectCard } from '../components/cards'
import { useDebounce } from '../hooks/useDebounce'
import { useEnums } from '../hooks/useEnums'
import { useResource } from '../hooks/useResource'
import { t } from '../i18n/uz'
import { useAuth } from '../store/auth'
import type { Paginated, ProjectSummary, Team, UserShort } from '../types'

const PAGE_SIZE = 20

export function ProjectsPage() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const { isAdmin, canWrite } = useAuth()
  const enums = useEnums()

  const [search, setSearch] = useState(params.get('search') ?? '')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search)

  const status = params.get('status') ?? ''
  const measurerId = params.get('measurer_id') ?? ''
  const teamId = params.get('team_id') ?? ''
  const dateFrom = params.get('date_from') ?? ''
  const dateTo = params.get('date_to') ?? ''

  const query = useMemo(() => {
    const query = new URLSearchParams({ page: String(page), size: String(PAGE_SIZE) })
    if (debouncedSearch.trim()) query.set('search', debouncedSearch.trim())
    if (status) query.set('status', status)
    if (measurerId) query.set('measurer_id', measurerId)
    if (teamId) query.set('team_id', teamId)
    if (dateFrom) query.set('date_from', dateFrom)
    if (dateTo) query.set('date_to', dateTo)
    return query.toString()
  }, [debouncedSearch, status, measurerId, teamId, dateFrom, dateTo, page])

  const { data, loading, error, fromCache, reload } = useResource<Paginated<ProjectSummary>>(
    `/projects?${query}`,
  )
  const measurers = useResource<UserShort[]>(isAdmin ? '/users/measurers' : null)
  const teams = useResource<Team[]>(isAdmin ? '/teams' : null)

  const activeFilters = [status, measurerId, teamId, dateFrom, dateTo].filter(Boolean).length

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
    setPage(1)
  }

  const resetFilters = () => {
    setParams(new URLSearchParams(), { replace: true })
    setPage(1)
  }

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={t.project.listTitle}
        subtitle={data ? `${data.meta.total} ta obyekt` : undefined}
        action={
          <Button size="sm" onClick={() => navigate('/projects/new')}>
            ➕
          </Button>
        }
      />

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <svg
            viewBox="0 0 24 24"
            className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-hint"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            placeholder={t.project.searchPlaceholder}
            className="field pl-11"
            aria-label={t.app.search}
          />
        </div>
        <button
          type="button"
          onClick={() => setFiltersOpen(true)}
          className="card tap-scale relative flex h-12 w-12 shrink-0 items-center justify-center"
          aria-label={t.app.filter}
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 6h16M7 12h10M10 18h4" strokeLinecap="round" />
          </svg>
          {activeFilters > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-[11px] font-bold text-white">
              {activeFilters}
            </span>
          )}
        </button>
      </div>

      {fromCache && <p className="mb-3 text-xs text-hint">{t.offline.cachedView}</p>}

      {loading && !data ? (
        <CardSkeleton count={4} />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          icon="🔍"
          title={t.project.emptyList}
          description={activeFilters || search ? t.project.emptyListHint : undefined}
          action={
            activeFilters > 0 ? (
              <Button size="sm" variant="secondary" onClick={resetFilters}>
                {t.filters.reset}
              </Button>
            ) : (
              canWrite ? (
                <Button size="sm" onClick={() => navigate('/projects/new')}>
                  {t.dashboard.newProject}
                </Button>
              ) : undefined
            )
          }
        />
      ) : data ? (
        <>
          <div className="space-y-3">
            {data.items.map((project) => (
              <ProjectCard key={project.id} project={project} showTeam={isAdmin} />
            ))}
          </div>

          {data.meta.pages > 1 && (
            <div className="mt-5 flex items-center justify-between gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                ← {t.app.back}
              </Button>
              <span className="text-sm text-hint tabular-nums">
                {data.meta.page} / {data.meta.pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= data.meta.pages}
                onClick={() => setPage((value) => value + 1)}
              >
                Keyingi →
              </Button>
            </div>
          )}
        </>
      ) : null}

      <Sheet
        open={filtersOpen}
        title={t.filters.title}
        onClose={() => setFiltersOpen(false)}
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth onClick={resetFilters}>
              {t.filters.reset}
            </Button>
            <Button fullWidth onClick={() => setFiltersOpen(false)}>
              {t.app.apply}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Select
            label={t.filters.status}
            value={status}
            placeholder={t.app.all}
            options={enums.project_statuses}
            onChange={(event) => updateFilter('status', event.target.value)}
          />

          {isAdmin && (
            <Select
              label={t.teams.team}
              value={teamId}
              placeholder={t.teams.allTeams}
              options={(teams.data ?? []).map((team) => ({ value: team.id, label: team.name }))}
              onChange={(event) => updateFilter('team_id', event.target.value)}
            />
          )}

          {isAdmin && (
            <Select
              label={t.filters.measurer}
              value={measurerId}
              placeholder={t.app.all}
              options={(measurers.data ?? []).map((user) => ({ value: user.id, label: user.full_name }))}
              onChange={(event) => updateFilter('measurer_id', event.target.value)}
            />
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="date-from">
                {t.filters.dateFrom}
              </label>
              <input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(event) => updateFilter('date_from', event.target.value)}
                className="field"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="date-to">
                {t.filters.dateTo}
              </label>
              <input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(event) => updateFilter('date_to', event.target.value)}
                className="field"
              />
            </div>
          </div>
        </div>
      </Sheet>
    </Screen>
  )
}
