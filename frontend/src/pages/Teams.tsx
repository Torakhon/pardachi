import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '../components/Button'
import { CardSkeleton, Chip, EmptyState, ErrorState } from '../components/Feedback'
import { Input, TextArea } from '../components/Input'
import { OfflineBanner, PageHeader, Screen } from '../components/Layout'
import { Sheet } from '../components/Sheet'
import { useResource } from '../hooks/useResource'
import { t } from '../i18n/uz'
import { api } from '../lib/api'
import { useToast } from '../store/toast'
import type { Team } from '../types'

/** Jamoalar ro'yxati — faqat administrator uchun. */
export function TeamsPage() {
  const toast = useToast()
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data, loading, error: loadError, reload } = useResource<Team[]>('/teams')

  const submit = async () => {
    if (name.trim().length < 2) {
      setError(t.validation.required)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api.post<Team>(
        '/teams',
        { name: name.trim(), description: description.trim() || null },
        { label: `${t.teams.newTitle}: ${name.trim()}` },
      )
      toast.success(t.teams.created)
      setCreating(false)
      setName('')
      setDescription('')
      await reload()
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : t.app.somethingWrong
      setError(message)
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={t.teams.title}
        subtitle={data ? `${data.length} ta jamoa` : undefined}
        action={
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-2xl leading-none text-white"
            aria-label={t.teams.newTitle}
          >
            +
          </button>
        }
      />

      {loading && !data ? (
        <CardSkeleton count={3} />
      ) : loadError && !data ? (
        <ErrorState message={loadError} onRetry={() => void reload()} />
      ) : data && data.length === 0 ? (
        <EmptyState
          icon="👥"
          title={t.teams.empty}
          description={t.teams.emptyHint}
          action={<Button onClick={() => setCreating(true)}>{t.teams.newTitle}</Button>}
        />
      ) : (
        <ul className="space-y-3">
          {data?.map((team) => (
            <li key={team.id}>
              <Link
                to={`/teams/${team.id}`}
                className="block rounded-2xl bg-card p-4 transition active:scale-[0.99]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold">{team.name}</p>
                    {team.description ? (
                      <p className="mt-0.5 line-clamp-2 text-sm text-hint">{team.description}</p>
                    ) : null}
                  </div>
                  <Chip tone={team.is_active ? 'brand' : 'default'}>{team.status_label}</Chip>
                </div>
                <p className="mt-3 text-sm text-hint">{t.teams.membersCount(team.members_count)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Sheet open={creating} onClose={() => setCreating(false)} title={t.teams.newTitle}>
        <div className="space-y-4">
          <Input
            label={t.teams.name}
            required
            autoFocus
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t.teams.namePlaceholder}
            error={error ?? undefined}
          />
          <TextArea
            label={t.teams.description}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t.teams.descriptionPlaceholder}
            rows={3}
          />
          <Button fullWidth size="lg" loading={busy} onClick={() => void submit()}>
            {t.app.save}
          </Button>
        </div>
      </Sheet>
    </Screen>
  )
}
