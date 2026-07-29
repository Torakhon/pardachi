import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { setBackButton } from '../lib/telegram'

/** Telegram "orqaga" tugmasini sahifa bilan bog'laydi. */
export function useTelegramBack(target?: string | number): void {
  const navigate = useNavigate()

  useEffect(() => {
    const handler = () => {
      if (typeof target === 'string') navigate(target)
      else navigate(target ?? -1)
    }
    return setBackButton(true, handler)
  }, [navigate, target])
}
