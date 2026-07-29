import { useState } from 'react'

import { Button } from '../components/Button'
import { Chip } from '../components/Feedback'
import { Input, Segmented } from '../components/Input'
import { OfflineBanner, PageHeader, Screen, Section } from '../components/Layout'
import { InfoRow } from '../components/cards'
import { t } from '../i18n/uz'
import { api } from '../lib/api'
import { formatDateTime, initials, maskPhoneInput, phoneToApi } from '../lib/format'
import { cacheClear, clearQueue } from '../lib/offline'
import { getStoredTheme, setStoredTheme } from '../lib/telegram'
import type { ThemePreference } from '../lib/telegram'
import { useAuth } from '../store/auth'
import { useNetwork } from '../store/network'
import { useToast } from '../store/toast'
import type { User } from '../types'

export function ProfilePage() {
  const { user, setUser, signOut } = useAuth()
  const { online, pending, syncing, sync } = useNetwork()
  const toast = useToast()

  const [phone, setPhone] = useState(maskPhoneInput(user?.phone ?? ''))
  const [saving, setSaving] = useState(false)
  const [theme, setTheme] = useState<ThemePreference>(getStoredTheme())

  if (!user) return null

  const save = async () => {
    setSaving(true)
    try {
      const updated = await api.patch<User>('/auth/me', { phone: phoneToApi(phone) })
      setUser(updated)
      toast.success(t.profile.saved)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
    } finally {
      setSaving(false)
    }
  }

  const changeTheme = (value: ThemePreference) => {
    setTheme(value)
    setStoredTheme(value)
  }

  const clearLocalData = async () => {
    await cacheClear()
    await clearQueue()
    toast.info('Lokal ma’lumotlar tozalandi')
  }

  return (
    <Screen>
      <OfflineBanner />
      <PageHeader title={t.profile.title} />

      <div className="card mb-5 flex items-center gap-4 p-4">
        {user.photo_url ? (
          <img src={user.photo_url} alt={user.full_name} className="h-16 w-16 rounded-full object-cover" />
        ) : (
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-600 text-xl font-bold text-white">
            {initials(user.full_name)}
          </span>
        )}
        <div className="min-w-0">
          <h2 className="truncate text-lg font-bold">{user.full_name}</h2>
          {user.username && <p className="truncate text-sm text-hint">@{user.username}</p>}
          <div className="mt-1">
            <Chip tone="brand">{user.role_label}</Chip>
          </div>
        </div>
      </div>

      <Section title={t.profile.phone}>
        <div className="space-y-3">
          <Input
            label={t.profile.phone}
            type="tel"
            inputMode="tel"
            value={phone}
            placeholder={t.project.phonePlaceholder}
            onChange={(event) => setPhone(maskPhoneInput(event.target.value))}
          />
          <Button fullWidth loading={saving} onClick={() => void save()}>
            {t.profile.save}
          </Button>
        </div>
      </Section>

      <Section title={t.profile.theme}>
        <Segmented
          value={theme}
          options={[
            { value: 'auto', label: t.profile.themeAuto },
            { value: 'light', label: t.profile.themeLight },
            { value: 'dark', label: t.profile.themeDark },
          ]}
          onChange={changeTheme}
        />
      </Section>

      <Section title={t.offline.pending}>
        <div className="card divide-y px-4" style={{ borderColor: 'var(--app-border)' }}>
          <InfoRow label="Internet" value={online ? '🟢 Bor' : '🔴 Yo‘q'} />
          <InfoRow label={t.offline.pending} value={pending} />
        </div>
        {pending > 0 && (
          <Button fullWidth variant="secondary" className="mt-3" loading={syncing} onClick={() => void sync()}>
            {t.offline.syncNow}
          </Button>
        )}
      </Section>

      <Section>
        <div className="card divide-y px-4" style={{ borderColor: 'var(--app-border)' }}>
          <InfoRow label={t.profile.telegramId} value={user.telegram_id ?? '—'} />
          <InfoRow label={t.users.lastLogin} value={formatDateTime(user.last_login_at)} />
          <InfoRow label={t.profile.appVersion} value="1.0.0" />
        </div>
      </Section>

      <div className="space-y-2">
        <Button fullWidth variant="secondary" onClick={() => void clearLocalData()}>
          Lokal ma’lumotlarni tozalash
        </Button>
        <Button fullWidth variant="ghost" className="text-danger" onClick={signOut}>
          {t.auth.logout}
        </Button>
      </div>
    </Screen>
  )
}
