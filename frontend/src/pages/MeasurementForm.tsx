import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Button, StickyAction } from '../components/Button'
import { FullScreenLoader } from '../components/Feedback'
import { Combobox, Input, NumberInput, Segmented, TextArea } from '../components/Input'
import { PageHeader, Screen, Section } from '../components/Layout'
import { useEnums } from '../hooks/useEnums'
import { useTelegramBack } from '../hooks/useTelegramBack'
import { t } from '../i18n/uz'
import { ApiError, QueuedError, api } from '../lib/api'
import { formatCm } from '../lib/format'
import { buildOptimisticItem, cacheItem, newId } from '../lib/optimistic'
import { haptic } from '../lib/telegram'
import { useToast } from '../store/toast'
import type { ItemType, MeasurementItem } from '../types'

interface FormState {
  name: string
  item_type: ItemType
  width_cm: string
  height_cm: string
  curtain_width_cm: string
  curtain_height_cm: string
  cornice_width_cm: string
  cornice_height_cm: string
  fabric_type: string
  curtain_model: string
  fabric_color: string
  quantity: string
  notes: string
}

const EMPTY: FormState = {
  name: '',
  item_type: 'window',
  width_cm: '',
  height_cm: '',
  curtain_width_cm: '',
  curtain_height_cm: '',
  cornice_width_cm: '',
  cornice_height_cm: '',
  fabric_type: '',
  curtain_model: '',
  fabric_color: '',
  quantity: '1',
  notes: '',
}

const COLORS = ['Oq', 'Bej', 'Kulrang', 'To‘q ko‘k', 'Yashil', 'Shokolad', 'Bordo', 'Oltin']

const toNumber = (value: string): string | null => {
  const normalized = value.replace(',', '.').trim()
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) && parsed > 0 ? parsed.toFixed(2) : null
}

export function MeasurementFormPage({ mode }: { mode: 'create' | 'edit' }) {
  const { roomId, itemId } = useParams<{ roomId: string; itemId: string }>()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const toast = useToast()
  const enums = useEnums()
  const widthRef = useRef<HTMLInputElement>(null)

  const initialType = (params.get('type') as ItemType) || 'window'
  const [form, setForm] = useState<FormState>({ ...EMPTY, item_type: initialType })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(mode === 'edit')
  const [saving, setSaving] = useState(false)
  const [ownerRoomId, setOwnerRoomId] = useState<string | null>(roomId ?? null)

  useTelegramBack(ownerRoomId ? `/rooms/${ownerRoomId}` : '/projects')

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setErrors((previous) => ({ ...previous, [key]: '' }))
  }

  // Tahrirlash rejimi — mavjud o'lchovni yuklaymiz
  useEffect(() => {
    if (mode !== 'edit' || !itemId) return
    let active = true
    void api
      .get<MeasurementItem>(`/measurements/${itemId}`)
      .then((item) => {
        if (!active) return
        setOwnerRoomId(item.room_id)
        setForm({
          name: item.name,
          item_type: item.item_type,
          width_cm: formatCm(item.width_cm),
          height_cm: formatCm(item.height_cm),
          curtain_width_cm: item.curtain_width_cm ? formatCm(item.curtain_width_cm) : '',
          curtain_height_cm: item.curtain_height_cm ? formatCm(item.curtain_height_cm) : '',
          cornice_width_cm: item.cornice_width_cm ? formatCm(item.cornice_width_cm) : '',
          cornice_height_cm: item.cornice_height_cm ? formatCm(item.cornice_height_cm) : '',
          fabric_type: item.fabric_type ?? '',
          curtain_model: item.curtain_model ?? '',
          fabric_color: item.fabric_color ?? '',
          quantity: String(item.quantity),
          notes: item.notes ?? '',
        })
      })
      .catch((caught: unknown) => toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [mode, itemId, toast])

  // Yaratish rejimi — nom taklifini olamiz va eni maydoniga fokus qo'yamiz
  useEffect(() => {
    if (mode !== 'create' || !roomId) return
    void api
      .get<{ name: string }>(`/rooms/${roomId}/items/suggest-name?item_type=${form.item_type}`)
      .then((response) => setForm((previous) => ({ ...previous, name: response.name })))
      .catch(() =>
        setForm((previous) => ({
          ...previous,
          name: previous.name || (previous.item_type === 'window' ? 'Oyna 1' : 'Eshik 1'),
        })),
      )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, roomId, form.item_type])

  useEffect(() => {
    if (mode === 'create') widthRef.current?.focus()
  }, [mode])

  const validate = (): boolean => {
    const next: Record<string, string> = {}
    if (!form.name.trim()) next.name = t.validation.required
    if (!toNumber(form.width_cm)) next.width_cm = form.width_cm ? t.validation.positive : t.validation.required
    if (!toNumber(form.height_cm)) next.height_cm = form.height_cm ? t.validation.positive : t.validation.required
    for (const key of ['curtain_width_cm', 'curtain_height_cm', 'cornice_width_cm', 'cornice_height_cm'] as const) {
      if (form[key] && !toNumber(form[key])) next[key] = t.validation.positive
    }
    setErrors(next)
    if (Object.keys(next).length > 0) haptic.error()
    return Object.keys(next).length === 0
  }

  const buildPayload = () => ({
    name: form.name.trim(),
    item_type: form.item_type,
    quantity: Math.max(1, Number(form.quantity) || 1),
    width_cm: toNumber(form.width_cm),
    height_cm: toNumber(form.height_cm),
    curtain_width_cm: toNumber(form.curtain_width_cm),
    curtain_height_cm: toNumber(form.curtain_height_cm),
    cornice_width_cm: toNumber(form.cornice_width_cm),
    cornice_height_cm: toNumber(form.cornice_height_cm),
    fabric_type: form.fabric_type.trim() || null,
    curtain_model: form.curtain_model.trim() || null,
    fabric_color: form.fabric_color.trim() || null,
    notes: form.notes.trim() || null,
  })

  const submit = async (addAnother = false) => {
    if (!validate()) {
      toast.error(t.validation.checkForm)
      return
    }
    setSaving(true)
    const payload = buildPayload()

    try {
      if (mode === 'edit' && itemId) {
        await api.patch(`/measurements/${itemId}`, payload, { label: `${t.measurement.editTitle}: ${payload.name}` })
        toast.success(t.measurement.updated)
        navigate(`/rooms/${ownerRoomId}`, { replace: true })
        return
      }

      if (!roomId) return
      const id = newId()
      try {
        await api.post<MeasurementItem>(`/rooms/${roomId}/items`, { ...payload, id }, {
          label: `${t.measurement.newTitle}: ${payload.name}`,
        })
        toast.success(t.measurement.created)
      } catch (caught) {
        if (caught instanceof QueuedError) {
          await cacheItem(
            buildOptimisticItem({
              id,
              room_id: roomId,
              name: payload.name,
              item_type: payload.item_type,
              width_cm: payload.width_cm ?? '0',
              height_cm: payload.height_cm ?? '0',
              curtain_width_cm: payload.curtain_width_cm,
              curtain_height_cm: payload.curtain_height_cm,
              cornice_width_cm: payload.cornice_width_cm,
              cornice_height_cm: payload.cornice_height_cm,
              fabric_type: payload.fabric_type,
              curtain_model: payload.curtain_model,
              fabric_color: payload.fabric_color,
              quantity: payload.quantity,
              notes: payload.notes,
              sort_order: 0,
            }),
          )
          toast.warning(t.offline.savedLocally)
        } else {
          throw caught
        }
      }

      if (addAnother) {
        // Mato/model/rangni saqlab qolamiz — keyingi oyna odatda bir xil bo'ladi.
        setForm((previous) => ({
          ...previous,
          name: '',
          width_cm: '',
          height_cm: '',
          curtain_width_cm: '',
          curtain_height_cm: '',
          cornice_width_cm: '',
          cornice_height_cm: '',
          notes: '',
        }))
        haptic.success()
        widthRef.current?.focus()
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } else {
        navigate(`/rooms/${roomId}`, { replace: true })
      }
    } catch (caught) {
      if (caught instanceof ApiError) {
        setErrors(caught.fields)
        toast.error(caught.message)
      } else {
        toast.error(caught instanceof Error ? caught.message : t.app.somethingWrong)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <FullScreenLoader />

  const area = (() => {
    const width = Number(form.width_cm.replace(',', '.'))
    const height = Number(form.height_cm.replace(',', '.'))
    if (!width || !height) return null
    return ((width * height) / 10000).toFixed(2)
  })()

  return (
    <Screen>
      <PageHeader
        title={mode === 'create' ? t.measurement.newTitle : t.measurement.editTitle}
        subtitle={t.measurement.hint}
        back={ownerRoomId ? `/rooms/${ownerRoomId}` : undefined}
      />

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void submit(false)
        }}
      >
        <Segmented
          label={t.measurement.type}
          value={form.item_type}
          options={[
            { value: 'window', label: t.room.windows, icon: '🪟' },
            { value: 'door', label: t.room.doors, icon: '🚪' },
          ]}
          onChange={(value) => setField('item_type', value)}
        />

        <Input
          label={t.measurement.name}
          required
          value={form.name}
          error={errors.name}
          onChange={(event) => setField('name', event.target.value)}
        />

        <Section title={t.measurement.sizes}>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              inputRef={widthRef}
              label={t.measurement.width}
              required
              value={form.width_cm}
              error={errors.width_cm}
              placeholder="150"
              onChange={(event) => setField('width_cm', event.target.value)}
            />
            <NumberInput
              label={t.measurement.height}
              required
              value={form.height_cm}
              error={errors.height_cm}
              placeholder="220"
              onChange={(event) => setField('height_cm', event.target.value)}
            />
          </div>
          {area && (
            <p className="mt-2 px-1 text-xs text-hint">
              {t.measurement.area}: <span className="font-semibold tabular-nums">{area} m²</span>
            </p>
          )}
        </Section>

        <Section title={t.measurement.curtain}>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label={t.measurement.curtainWidth}
              value={form.curtain_width_cm}
              error={errors.curtain_width_cm}
              onChange={(event) => setField('curtain_width_cm', event.target.value)}
            />
            <NumberInput
              label={t.measurement.curtainHeight}
              value={form.curtain_height_cm}
              error={errors.curtain_height_cm}
              onChange={(event) => setField('curtain_height_cm', event.target.value)}
            />
          </div>
        </Section>

        <Section title={t.measurement.cornice}>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label={t.measurement.corniceWidth}
              value={form.cornice_width_cm}
              error={errors.cornice_width_cm}
              onChange={(event) => setField('cornice_width_cm', event.target.value)}
            />
            <NumberInput
              label={t.measurement.corniceHeight}
              value={form.cornice_height_cm}
              error={errors.cornice_height_cm}
              onChange={(event) => setField('cornice_height_cm', event.target.value)}
            />
          </div>
        </Section>

        <Section title={t.measurement.material}>
          <div className="space-y-4">
            <Combobox
              label={t.measurement.fabricType}
              value={form.fabric_type}
              suggestions={enums.fabric_types}
              placeholder={t.measurement.selectPlaceholder}
              onChange={(event) => setField('fabric_type', event.target.value)}
            />
            <Combobox
              label={t.measurement.curtainModel}
              value={form.curtain_model}
              suggestions={enums.curtain_models}
              placeholder={t.measurement.selectPlaceholder}
              onChange={(event) => setField('curtain_model', event.target.value)}
            />
            <Combobox
              label={t.measurement.fabricColor}
              value={form.fabric_color}
              suggestions={COLORS}
              placeholder={t.measurement.selectPlaceholder}
              onChange={(event) => setField('fabric_color', event.target.value)}
            />
            <Input
              label={t.measurement.quantity}
              type="number"
              inputMode="numeric"
              min={1}
              max={100}
              value={form.quantity}
              suffix={t.app.pcs}
              onChange={(event) => setField('quantity', event.target.value)}
            />
          </div>
        </Section>

        <TextArea
          label={t.measurement.notes}
          value={form.notes}
          onChange={(event) => setField('notes', event.target.value)}
        />

        <StickyAction>
          <div className="space-y-2">
            <Button type="submit" fullWidth size="lg" loading={saving}>
              {t.app.save}
            </Button>
            {mode === 'create' && (
              <Button
                type="button"
                fullWidth
                variant="secondary"
                loading={saving}
                onClick={() => void submit(true)}
              >
                {t.measurement.saveAndAdd}
              </Button>
            )}
          </div>
        </StickyAction>
      </form>
    </Screen>
  )
}
