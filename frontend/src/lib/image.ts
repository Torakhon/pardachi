/** Rasmni yuklashdan oldin brauzerda siqish. */

export interface CompressOptions {
  maxDimension?: number
  quality?: number
  maxBytes?: number
}

export interface CompressedImage {
  blob: Blob
  width: number
  height: number
  originalSize: number
  size: number
  previewUrl: string
}

const DEFAULTS: Required<CompressOptions> = {
  maxDimension: 1600,
  quality: 0.82,
  maxBytes: 1.5 * 1024 * 1024,
}

/**
 * Rasmni kichraytiradi va JPEG ga o'giradi. Fayl hajmi `maxBytes` dan katta
 * bo'lsa, sifatni bosqichma-bosqich pasaytiradi (mobil internet uchun).
 */
export async function compressImage(file: File, options: CompressOptions = {}): Promise<CompressedImage> {
  const config = { ...DEFAULTS, ...options }
  const bitmap = await loadImage(file)

  const scale = Math.min(1, config.maxDimension / Math.max(bitmap.width, bitmap.height))
  const width = Math.max(1, Math.round(bitmap.width * scale))
  const height = Math.max(1, Math.round(bitmap.height * scale))

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Rasmni qayta ishlab bo‘lmadi')
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(bitmap, 0, 0, width, height)
  if ('close' in bitmap) bitmap.close()

  let quality = config.quality
  let blob = await toBlob(canvas, quality)
  while (blob.size > config.maxBytes && quality > 0.45) {
    quality -= 0.12
    blob = await toBlob(canvas, quality)
  }

  return {
    blob,
    width,
    height,
    originalSize: file.size,
    size: blob.size,
    previewUrl: URL.createObjectURL(blob),
  }
}

function toBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('Rasmni siqib bo‘lmadi'))),
      'image/jpeg',
      quality,
    )
  })
}

async function loadImage(file: File): Promise<ImageBitmap | HTMLImageElement> {
  if ('createImageBitmap' in window) {
    try {
      // EXIF burilishini hisobga oladi
      return await createImageBitmap(file, { imageOrientation: 'from-image' })
    } catch {
      // Ba'zi brauzerlarda qo'llab-quvvatlanmaydi — pastdagi usulga o'tamiz
    }
  }
  return new Promise((resolve, reject) => {
    const image = new Image()
    const url = URL.createObjectURL(file)
    image.onload = () => {
      URL.revokeObjectURL(url)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Rasmni o‘qib bo‘lmadi'))
    }
    image.src = url
  })
}

export function isImageFile(file: File): boolean {
  return ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'].includes(file.type)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
