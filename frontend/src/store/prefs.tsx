import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react'
import { dictionaries, lookup, type Locale, type MessageKey } from '../i18n'

export type Theme = 'night' | 'day'

const LOCALE_KEY = 'sre-locale'
const THEME_KEY = 'sre-theme'

function readStored<T extends string>(key: string, fallback: T, allowed: T[]): T {
  try {
    const v = localStorage.getItem(key)
    if (v && (allowed as string[]).includes(v)) return v as T
  } catch {
    /* ignore */
  }
  return fallback
}

function applyDom(locale: Locale, theme: Theme) {
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
  root.setAttribute('data-lang', locale)
  root.lang = locale === 'zh' ? 'zh-CN' : 'en'
  root.style.colorScheme = theme === 'day' ? 'light' : 'dark'
  // 同步 body class，确保背景不被残留样式拆开
  document.body.classList.remove('theme-day', 'theme-night')
  document.body.classList.add(theme === 'day' ? 'theme-day' : 'theme-night')
  document.body.style.backgroundColor = ''
  document.body.style.color = ''
}

interface PrefsValue {
  locale: Locale
  theme: Theme
  setLocale: (locale: Locale) => void
  setTheme: (theme: Theme) => void
  t: (key: MessageKey) => string
}

const PrefsContext = createContext<PrefsValue | null>(null)

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() =>
    typeof window === 'undefined' ? 'zh' : readStored(LOCALE_KEY, 'zh', ['zh', 'en']),
  )
  const [theme, setThemeState] = useState<Theme>(() =>
    typeof window === 'undefined' ? 'night' : readStored(THEME_KEY, 'night', ['night', 'day']),
  )

  useEffect(() => {
    applyDom(locale, theme)
    try {
      localStorage.setItem(LOCALE_KEY, locale)
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [locale, theme])

  const value = useMemo<PrefsValue>(() => {
    const dict = dictionaries[locale]
    return {
      locale,
      theme,
      setLocale: setLocaleState,
      setTheme: setThemeState,
      t: (key: MessageKey) => lookup(dict, key),
    }
  }, [locale, theme])

  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>
}

export function usePrefs() {
  const ctx = useContext(PrefsContext)
  if (!ctx) throw new Error('usePrefs must be used within PrefsProvider')
  return ctx
}
