import { useMemo, useState } from 'react'

import { Button } from '../components/Button'
import { CardSkeleton, Chip, EmptyState, ErrorState } from '../components/Feedback'
import { OfflineBanner, PageHeader, Screen } from '../components/Layout'
import { Sheet } from '../components/Sheet'
import { Select } from '../components/Input'
import { InfoRow } from '../components/cards'
import { useDebounce } from '../hooks/useDebounce'
import { useResource } from '../hooks/useResource'
import { t } from '../i18n/uz'
import { api } from '../lib/api'
import { cn } from '../lib/cn'
import { formatDateTime, formatPhone, initials } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'
import type { Paginated, Team, User, UserRole } from '../types'

export function UsersPage() {
  const toast = useToast()
  const { user: currentUser } = useAuth()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<User | null>(null)
  const [busy, setBusy] = useState(false)
  const debounced = useDebounce(search)

  const query = useMemo(() => {
    const params = new URLSearchParams({ page: '1', size: '100' })
    if (debounced.trim()) params.set('search', debounced.trim())
    return params.toString()
  }, [debounced])

  const { data, loading, error, reload } = useResource<Paginated<User>>(`/users?${query}`)
  const { data: teams } = useResource<Team[]>('/teams')

  const update = async (
    user: User,
    payload: Partial<Pick<User, 'role' | 'is_active'>> & { team_id?: string | null },
  ) => {
    setBusy(true)
    try {
      const updated = await api.patch<User>(`/users/${user.id}`, payload, {
        label: `${t.users.title}: ${user.full_name}`,
      })
      toast.success(t.users.updated)
      setSelected(updated)
      await reload()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader title={t.users.title} subtitle={data ? `${data.meta.total} ta xodim` : undefined} />

      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t.users.searchPlaceholder}
        className="field mb-4"
        aria-label={t.app.search}
      />

      {loading && !data ? (
        <CardSkeleton count={4} />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : data && data.items.length === 0 ? (
        <EmptyState icon="👥" title={t.users.empty} />
      ) : (
        <div className="space-y-2.5">
          {data?.items.map((user) => (
            <button
              key={user.id}
              type="button"
              onClick={() => setSelected(user)}
              className="card tap-scale flex w-full items-center gap-3 p-3 text-left"
            >
              <span
                className={cn(
                  'flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold',
                  user.role === 'admin' ? 'bg-brand-600 text-white' : 'bg-black/5 text-hint dark:bg-white/10',
                )}
              >
                {initials(user.full_name)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="truncate font-semibold">{user.full_name}</span>
                  {user.id === currentUser?.id && <Chip tone="brand">siz</Chip>}
                </span>
                <span className="mt-0.5 block truncate text-sm text-hint">
                  {user.team_name ?? t.teams.noTeam}
                  {user.telegram_id ? ` · ID: ${user.telegram_id}` : ''}
                </span>
              </span>
              <span className="flex shrink-0 flex-col items-end gap-1">
                <Chip tone={user.role === 'admin' ? 'brand' : 'default'}>{user.role_label}</Chip>
                {!user.is_active && <Chip>{t.users.blocked}</Chip>}
              </span>
            </button>
          ))}
        </div>
      )}

      <Sheet open={selected !== null} title={selected?.full_name ?? ''} onClose={() => setSelected(null)}>
        {selected && (
          <div className="space-y-4">
            <div className="divide-y" style={{ borderColor: 'var(--app-border)' }}>
              <InfoRow label={t.users.role} value={selected.role_label} />
              <InfoRow label={t.teams.team} value={selected.team_name ?? t.teams.noTeam} />
              <InfoRow label={t.profile.phone} value={formatPhone(selected.phone)} />
              <InfoRow label={t.profile.telegramId} value={selected.telegram_id ?? '—'} />
              <InfoRow
                label={t.users.lastLogin}
                value={selected.last_login_at ? formatDateTime(selected.last_login_at) : t.users.never}
              />
              <InfoRow label={t.users.active} value={selected.is_active ? t.app.yes : t.app.no} />
            </div>

            {selected.id !== currentUser?.id && (
              <div className="space-y-3">
                <Select
                  label={t.users.role}
                  value={selected.role}
                  disabled={busy}
                  onChange={(event) => void update(selected, { role: event.target.value as UserRole })}
                  options={[
                    { value: 'admin', label: `${t.roles.admin} — ${t.roles.adminHint}` },
                    { value: 'measurer', label: `${t.roles.measurer} — ${t.roles.measurerHint}` },
                    { value: 'viewer', label: `${t.roles.viewer} — ${t.roles.viewerHint}` },
                  ]}
                />

                <Select
                  label={t.teams.team}
                  value={selected.team_id ?? ''}
                  disabled={busy}
                  placeholder={t.teams.noTeam}
                  onChange={(event) =>
                    void update(selected, { team_id: event.target.value || null })
                  }
                  options={(teams ?? []).map((team) => ({ value: team.id, label: team.name }))}
                />
                <Button
                  fullWidth
                  variant={selected.is_active ? 'danger' : 'success'}
                  loading={busy}
                  onClick={() => void update(selected, { is_active: !selected.is_active })}
                >
                  {selected.is_active ? t.users.block : t.users.unblock}
                </Button>
              </div>
            )}
          </div>
        )}
      </Sheet>
    </Screen>
  )
}
