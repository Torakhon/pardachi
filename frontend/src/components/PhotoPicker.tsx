import { useCallback, useEffect, useRef, useState } from 'react'

import { t } from '../i18n/uz'
import { QueuedError, api } from '../lib/api'
import { cn } from '../lib/cn'
import { compressImage, formatBytes, isImageFile } from '../lib/image'
import { useToast } from '../store/toast'
import type { RoomImage } from '../types'
import { Button } from './Button'
import { Spinner } from './Feedback'

interface PhotoPickerProps {
  roomId: string
  image: RoomImage | null
  onUploaded: (image: RoomImage | null) => void
  disabled?: boolean
}

type State = 'idle' | 'compressing' | 'uploading'

export function PhotoPicker({ roomId, image, onUploaded, disabled = false }: PhotoPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<State>('idle')
  const [preview, setPreview] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const handleFile = useCallback(
    async (file: File) => {
      if (!isImageFile(file)) {
        toast.error('Faqat rasm fayllarini yuklash mumkin (JPG, PNG, WEBP).')
        return
      }

      setState('compressing')
      try {
        const compressed = await compressImage(file)
        setPreview((previous) => {
          if (previous) URL.revokeObjectURL(previous)
          return compressed.previewUrl
        })
        setInfo(`${formatBytes(compressed.originalSize)} → ${formatBytes(compressed.size)}`)

        setState('uploading')
        const uploaded = await api.upload<RoomImage>(
          `/rooms/${roomId}/image`,
          compressed.blob,
          `xona-${roomId}.jpg`,
          `${t.room.photo}: ${roomId}`,
        )
        onUploaded(uploaded)
        toast.success(t.room.photoUploaded)
      } catch (error) {
        if (error instanceof QueuedError) {
          toast.warning(t.offline.savedLocally)
        } else {
          toast.error(error instanceof Error ? error.message : t.app.somethingWrong)
          setPreview(null)
        }
      } finally {
        setState('idle')
        if (inputRef.current) inputRef.current.value = ''
      }
    },
    [onUploaded, roomId, toast],
  )

  const remove = useCallback(async () => {
    try {
      await api.delete(`/rooms/${roomId}/image`, { label: `${t.room.deletePhoto}: ${roomId}` })
      setPreview(null)
      setInfo(null)
      onUploaded(null)
      toast.success(t.room.photoDeleted)
    } catch (error) {
      if (error instanceof QueuedError) toast.warning(t.offline.savedLocally)
      else toast.error(error instanceof Error ? error.message : t.app.somethingWrong)
    }
  }, [onUploaded, roomId, toast])

  const busy = state !== 'idle'
  const source = preview ?? image?.url ?? null

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) void handleFile(file)
        }}
      />

      {source ? (
        <div className="relative overflow-hidden rounded-2xl border" style={{ borderColor: 'var(--app-border)' }}>
          <img src={source} alt={t.room.photo} className="aspect-[4/3] w-full object-cover" loading="lazy" />
          {busy && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/55 text-white">
              <Spinner className="h-7 w-7 border-white" />
              <span className="text-sm font-medium">
                {state === 'compressing' ? t.room.photoCompressing : t.room.photoUploading}
              </span>
            </div>
          )}
          {info && !busy && (
            <span className="absolute left-2 top-2 rounded-lg bg-black/60 px-2 py-1 text-[11px] font-medium text-white">
              {info}
            </span>
          )}
        </div>
      ) : (
        <button
          type="button"
          disabled={disabled || busy}
          onClick={() => inputRef.current?.click()}
          className={cn(
            'flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed text-hint transition',
            'hover:border-brand-500 hover:text-brand-600 disabled:opacity-60',
          )}
          style={{ borderColor: 'var(--app-border)' }}
        >
          {busy ? (
            <>
              <Spinner className="h-7 w-7" />
              <span className="text-sm font-medium">
                {state === 'compressing' ? t.room.photoCompressing : t.room.photoUploading}
              </span>
            </>
          ) : (
            <>
              <span className="text-4xl" aria-hidden>
                📷
              </span>
              <span className="text-sm font-semibold">{t.room.addPhoto}</span>
              <span className="max-w-[16rem] text-center text-xs">{t.room.photoHint}</span>
            </>
          )}
        </button>
      )}

      {source && (
        <div className="flex gap-3">
          <Button variant="secondary" fullWidth disabled={disabled || busy} onClick={() => inputRef.current?.click()}>
            {t.room.replacePhoto}
          </Button>
          <Button variant="ghost" disabled={disabled || busy} onClick={() => void remove()} className="text-danger">
            {t.app.delete}
          </Button>
        </div>
      )}
    </div>
  )
}
