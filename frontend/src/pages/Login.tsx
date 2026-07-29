import { t } from '../i18n/uz'
import { isTelegram } from '../lib/telegram'
import { useAuth } from '../store/auth'
import { Button } from '../components/Button'

/** Telegramdan tashqarida ochilganda yoki kirish muvaffaqiyatsiz bo'lganda. */
export function LoginPage() {
  const { error, signIn, devSignIn } = useAuth()
  const devAllowed = import.meta.env.DEV || Boolean(import.meta.env.VITE_DEV_LOGIN_SECRET)

  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-md flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-brand-600 text-4xl shadow-lg">
        🪟
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl font-bold">{t.app.name}</h1>
        <p className="text-sm text-hint">{t.app.tagline}</p>
      </div>

      {error ? (
        <div className="w-full rounded-xl bg-danger/10 px-4 py-3 text-sm font-medium text-danger">{error}</div>
      ) : (
        <p className="text-sm text-hint">{t.auth.openInTelegram}</p>
      )}

      <div className="w-full space-y-3">
        {isTelegram && (
          <Button fullWidth size="lg" onClick={() => void signIn()}>
            {t.auth.retry}
          </Button>
        )}

        {devAllowed && !isTelegram && (
          <>
            <Button fullWidth size="lg" onClick={() => void devSignIn('measurer')}>
              {t.auth.devLogin} — {t.users.role}: O‘lchovchi
            </Button>
            <Button fullWidth size="lg" variant="secondary" onClick={() => void devSignIn('admin')}>
              {t.auth.devLogin} — {t.users.role}: Administrator
            </Button>
            <p className="text-xs text-hint">{t.auth.devLoginHint}</p>
          </>
        )}
      </div>
    </div>
  )
}
