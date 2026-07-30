import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button, StickyAction } from '../components/Button'
import { FullScreenLoader } from '../components/Feedback'
import { Input, TextArea } from '../components/Input'
import { PageHeader, Screen, Section } from '../components/Layout'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { ApiError, QueuedError, api } from '../lib/api'
import { maskPhoneInput, phoneToApi } from '../lib/format'
import { buildOptimisticProject, cacheProject, newId } from '../lib/optimistic'
import { getCurrentLocation, haptic } from '../lib/telegram'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'
import type { GeoResult } from '../lib/telegram'
import type { Project } from '../types'

interface FormState {
  name: string
  order_number: string
  customer_name: string
  customer_phone: string
  address: string
  note: string
}

const EMPTY: FormState = {
  name: '',
  order_number: '',
  customer_name: '',
  customer_phone: '',
  address: '',
  note: '',
}

export function ProjectFormPage({ mode }: { mode: 'create' | 'edit' }) {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { user: currentUser } = useAuth()
  useTelegramBack(mode === 'edit' && projectId ? `/projects/${projectId}` : '/projects')

  const [form, setForm] = useState<FormState>(EMPTY)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(mode === 'edit')
  const [saving, setSaving] = useState(false)
  const [location, setLocation] = useState<GeoResult | null>(null)
  const [locating, setLocating] = useState(false)

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setErrors((previous) => ({ ...previous, [key]: '' }))
  }

  // Tahrirlash: mavjud ma'lumotni yuklaymiz
  useEffect(() => {
    if (mode !== 'edit' || !projectId) return
    let active = true
    void api
      .get<Project>(`/projects/${projectId}`)
      .then((project) => {
        if (!active) return
        setForm({
          name: project.name,
          order_number: project.order_number,
          customer_name: project.customer_name,
          customer_phone: maskPhoneInput(project.customer_phone),
          address: project.address,
          note: project.note ?? '',
        })
      })
      .catch((error: unknown) => toast.error(error instanceof Error ? error.message : t.app.somethingWrong))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [mode, projectId, toast])

  // Yaratish: buyurtma raqamini oldindan to'ldiramiz va lokatsiyani olamiz
  useEffect(() => {
    if (mode !== 'create') return
    void api
      .get<{ order_number: string }>('/projects/next-order-number')
      .then((response) => setForm((previous) => (previous.order_number ? previous : { ...previous, order_number: response.order_number })))
      .catch(() => undefined)
    void captureLocation(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  const captureLocation = useCallback(
    async (silent = false) => {
      setLocating(true)
      try {
        const result = await getCurrentLocation()
        setLocation(result)
        if (!silent) {
          haptic.success()
          toast.success(t.project.locationSaved)
        }
      } catch {
        if (!silent) toast.error(t.project.locationError)
      } finally {
        setLocating(false)
      }
    },
    [toast],
  )

  const validate = (): boolean => {
    const next: Record<string, string> = {}
    if (form.name.trim().length < 2) next.name = t.validation.required
    if (!form.order_number.trim()) next.order_number = t.validation.required
    if (form.customer_name.trim().length < 2) next.customer_name = t.validation.required
    if (phoneToApi(form.customer_phone).replace(/\D/g, '').length < 9) next.customer_phone = t.validation.phone
    setErrors(next)
    if (Object.keys(next).length > 0) haptic.error()
    return Object.keys(next).length === 0
  }

  const submit = async () => {
    if (!validate()) {
      toast.error(t.validation.checkForm)
      return
    }
    setSaving(true)

    const payload = {
      name: form.name.trim(),
      order_number: form.order_number.trim(),
      customer_name: form.customer_name.trim(),
      customer_phone: phoneToApi(form.customer_phone),
      address: form.address.trim(),
      note: form.note.trim() || null,
    }

    try {
      if (mode === 'edit' && projectId) {
        await api.patch<Project>(`/projects/${projectId}`, payload, { label: `${t.project.editTitle}: ${payload.name}` })
        toast.success(t.project.updated)
        navigate(`/projects/${projectId}`, { replace: true })
        return
      }

      const id = newId()
      const body = {
        ...payload,
        id,
        location: location
          ? {
              latitude: location.latitude.toFixed(6),
              longitude: location.longitude.toFixed(6),
              accuracy_m: location.accuracy ? location.accuracy.toFixed(2) : null,
              source: location.source,
            }
          : null,
      }

      try {
        const project = await api.post<Project>('/projects', body, { label: `${t.project.newTitle}: ${payload.name}` })
        toast.success(t.project.created)
        navigate(`/projects/${project.id}`, { replace: true })
      } catch (error) {
        if (error instanceof QueuedError) {
          // Oflayn: yozuvni lokal keshga qo'yamiz, navbat internet qaytganda yuboradi.
          await cacheProject(
            buildOptimisticProject({
              ...payload,
              id,
              team_id: currentUser?.team_id ?? null,
              team_name: currentUser?.team_name ?? null,
            }),
          )
          toast.warning(t.offline.savedLocally)
          navigate(`/projects/${id}`, { replace: true })
          return
        }
        throw error
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.fields)
        toast.error(error.message)
      } else {
        toast.error(error instanceof Error ? error.message : t.app.somethingWrong)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <FullScreenLoader />

  return (
    <Screen>
      <PageHeader
        title={mode === 'create' ? t.project.newTitle : t.project.editTitle}
        back={mode === 'edit' && projectId ? `/projects/${projectId}` : '/projects'}
      />

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <Input
          label={t.project.name}
          required
          autoFocus={mode === 'create'}
          value={form.name}
          error={errors.name}
          placeholder={t.project.namePlaceholder}
          onChange={(event) => setField('name', event.target.value)}
        />

        <Input
          label={t.project.orderNumber}
          required
          value={form.order_number}
          error={errors.order_number}
          hint={mode === 'create' ? t.project.orderNumberHint : undefined}
          onChange={(event) => setField('order_number', event.target.value)}
        />

        <Input
          label={t.project.customerName}
          required
          value={form.customer_name}
          error={errors.customer_name}
          placeholder={t.project.customerNamePlaceholder}
          onChange={(event) => setField('customer_name', event.target.value)}
        />

        <Input
          label={t.project.phone}
          required
          type="tel"
          inputMode="tel"
          value={form.customer_phone}
          error={errors.customer_phone}
          placeholder={t.project.phonePlaceholder}
          onChange={(event) => setField('customer_phone', maskPhoneInput(event.target.value))}
        />

        <Input
          label={t.project.address}
          value={form.address}
          error={errors.address}
          placeholder={t.project.addressPlaceholder}
          onChange={(event) => setField('address', event.target.value)}
        />

        {mode === 'create' && (
          <Section title={t.project.location}>
            <div className="card flex items-center justify-between gap-3 p-4">
              <div className="min-w-0 text-sm">
                {locating ? (
                  <span className="text-hint">{t.project.locationLoading}</span>
                ) : location ? (
                  <span className="font-medium tabular-nums">
                    📍 {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
                  </span>
                ) : (
                  <span className="text-hint">{t.project.noLocation}</span>
                )}
              </div>
              <Button type="button" size="sm" variant="secondary" loading={locating} onClick={() => void captureLocation()}>
                {location ? t.app.refresh : t.project.captureLocation}
              </Button>
            </div>
          </Section>
        )}

        <TextArea
          label={t.project.note}
          value={form.note}
          placeholder={t.project.notePlaceholder}
          onChange={(event) => setField('note', event.target.value)}
        />

        <StickyAction>
          <Button type="submit" fullWidth size="lg" loading={saving}>
            {mode === 'create' ? t.project.create : t.app.save}
          </Button>
        </StickyAction>
      </form>
    </Screen>
  )
}
