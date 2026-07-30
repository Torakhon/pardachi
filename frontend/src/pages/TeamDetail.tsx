import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { Button } from '../components/Button'
import { Chip, EmptyState, ErrorState, FullScreenLoader } from '../components/Feedback'
import { Input, Select, TextArea } from '../components/Input'
import { OfflineBanner, PageHeader, Screen, Section } from '../components/Layout'
import { ConfirmDialog, Sheet } from '../components/Sheet'
import { InfoRow } from '../components/cards'
import { useResource } from '../hooks/useResource'
import { t } from '../i18n/uz'
import { api } from '../lib/api'
import { initials } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'
import type { TeamWithMembers, UserRole, UserShort } from '../types'

const ROLE_OPTIONS = [
  { value: 'measurer', label: `${t.roles.measurer} — ${t.roles.measurerHint}` },
  { value: 'viewer', label: `${t.roles.viewer} — ${t.roles.viewerHint}` },
]

/** Jamoa tafsilotlari: a'zolarni Telegram ID bo'yicha qo'shish va rol berish. */
export function TeamDetailPage() {
  const { teamId = '' } = useParams()
  const toast = useToast()
  const { user: currentUser, isAdmin } = useAuth()

  const { data: team, loading, error, reload } = useResource<TeamWithMembers>(`/teams/${teamId}`)

  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState<UserShort | null>(null)
  const [busy, setBusy] = useState(false)

  const [telegramId, setTelegramId] = useState('')
  const [memberName, setMemberName] = useState('')
  const [role, setRole] = useState<UserRole>('measurer')
  const [formError, setFormError] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const openEdit = () => {
    if (!team) return
    setName(team.name)
    setDescription(team.description ?? '')
    setEditing(true)
  }

  const addMember = async () => {
    const parsed = Number(telegramId.replace(/\D/g, ''))
    if (!parsed) {
      setFormError(t.teams.telegramIdHint)
      return
    }
    setBusy(true)
    setFormError(null)
    try {
      await api.post<UserShort>(
        `/teams/${teamId}/members`,
        { telegram_id: parsed, first_name: memberName.trim() || null, role },
        { label: `${t.teams.addMember}: ${parsed}` },
      )
      toast.success(t.teams.memberAdded)
      setAdding(false)
      setTelegramId('')
      setMemberName('')
      setRole('measurer')
      await reload()
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : t.app.somethingWrong
      setFormError(message)
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  const changeRole = async (member: UserShort, nextRole: UserRole) => {
    setBusy(true)
    try {
      await api.post<UserShort>(
        `/teams/${teamId}/members`,
        { user_id: member.id, role: nextRole },
        { label: `${t.users.role}: ${member.full_name}` },
      )
      toast.success(t.users.updated)
      await reload()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
    }
  }

  const removeMember = async () => {
    if (!removing) return
    setBusy(true)
    try {
      await api.delete(`/teams/${teamId}/members/${removing.id}`, {
        label: `${t.teams.removeMember}: ${removing.full_name}`,
      })
      toast.success(t.teams.memberRemoved)
      setRemoving(null)
      await reload()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
    }
  }

  const saveTeam = async () => {
    setBusy(true)
    try {
      await api.patch(
        `/teams/${teamId}`,
        { name: name.trim(), description: description.trim() || null },
        { label: `${t.teams.editTitle}: ${name.trim()}` },
      )
      toast.success(t.teams.updated)
      setEditing(false)
      await reload()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setBusy(false)
    }
  }

  if (loading && !team) return <FullScreenLoader />
  if (error && !team) return <ErrorState message={error} onRetry={() => void reload()} />
  if (!team) return null

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader
        title={team.name}
        subtitle={t.teams.membersCount(team.members_count)}
        back="/teams"
        action={
          isAdmin ? (
            <button
              type="button"
              onClick={openEdit}
              className="tap-scale flex h-9 w-9 items-center justify-center rounded-xl text-hint"
              aria-label={t.teams.editTitle}
            >
              ✏️
            </button>
          ) : undefined
        }
      />

      <div className="mb-4 card p-4">
        <InfoRow label={t.teams.name} value={team.name} />
        {team.description ? <InfoRow label={t.teams.description} value={team.description} /> : null}
        <InfoRow label={t.teams.isActive} value={team.status_label} />
      </div>

      <Section
        title={t.teams.members}
        action={
          isAdmin ? (
            <button type="button" className="text-sm font-semibold text-brand-600" onClick={() => setAdding(true)}>
              + {t.teams.addMember}
            </button>
          ) : undefined
        }
      >
        {team.members.length === 0 ? (
          <EmptyState icon="🧑‍🤝‍🧑" title={t.teams.noMembers} description={t.teams.telegramIdHint} />
        ) : (
          <ul className="space-y-2">
            {team.members.map((member) => (
              <li key={member.id} className="card flex items-center gap-3 p-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600/12 text-sm font-bold text-brand-600">
                  {initials(member.full_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">
                    {member.full_name}
                    {member.id === currentUser?.id ? ' (siz)' : ''}
                  </p>
                  <p className="text-xs text-hint">
                    {member.telegram_id ? `ID: ${member.telegram_id}` : t.users.notLoggedIn}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Chip tone={member.role === 'measurer' ? 'brand' : 'default'}>{member.role_label}</Chip>
                  {isAdmin && member.id !== currentUser?.id && member.role !== 'admin' ? (
                    <>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void changeRole(member, member.role === 'measurer' ? 'viewer' : 'measurer')
                        }
                        className="text-xs font-semibold text-brand-600 disabled:opacity-50"
                      >
                        {member.role === 'measurer' ? t.roles.viewer : t.roles.measurer}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => setRemoving(member)}
                        className="text-xs font-semibold text-danger disabled:opacity-50"
                        aria-label={t.teams.removeMember}
                      >
                        ✕
                      </button>
                    </>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Sheet open={adding} onClose={() => setAdding(false)} title={t.teams.addMember}>
        <div className="space-y-4">
          <Input
            label={t.teams.telegramId}
            required
            autoFocus
            inputMode="numeric"
            value={telegramId}
            onChange={(event) => setTelegramId(event.target.value)}
            placeholder="123456789"
            hint={t.teams.telegramIdHint}
            error={formError ?? undefined}
          />
          <Input
            label={t.teams.memberName}
            value={memberName}
            onChange={(event) => setMemberName(event.target.value)}
            placeholder="Masalan: Rustam Qodirov"
          />
          <Select
            label={t.users.role}
            value={role}
            onChange={(event) => setRole(event.target.value as UserRole)}
            options={ROLE_OPTIONS}
          />
          <Button fullWidth size="lg" loading={busy} onClick={() => void addMember()}>
            {t.teams.addMember}
          </Button>
        </div>
      </Sheet>

      <Sheet open={editing} onClose={() => setEditing(false)} title={t.teams.editTitle}>
        <div className="space-y-4">
          <Input
            label={t.teams.name}
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <TextArea
            label={t.teams.description}
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <Button fullWidth size="lg" loading={busy} onClick={() => void saveTeam()}>
            {t.app.save}
          </Button>
        </div>
      </Sheet>

      <ConfirmDialog
        open={removing !== null}
        title={t.teams.removeConfirm}
        message={removing?.full_name ?? ''}
        confirmLabel={t.teams.removeMember}
        tone="danger"
        loading={busy}
        onConfirm={() => void removeMember()}
        onCancel={() => setRemoving(null)}
      />
    </Screen>
  )
}
