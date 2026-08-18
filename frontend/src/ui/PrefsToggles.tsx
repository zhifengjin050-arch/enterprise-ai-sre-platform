import { Sun, Moon } from 'lucide-react'
import { usePrefs } from '../store/prefs'

export default function PrefsToggles({ compact = false }: { compact?: boolean }) {
  const { locale, theme, setLocale, setTheme, t } = usePrefs()

  return (
    <div className={`flex items-center ${compact ? 'gap-1.5' : 'gap-2'}`}>
      <div className="prefs-seg" role="group" aria-label="Language">
        <button
          type="button"
          className={`prefs-seg__btn ${locale === 'zh' ? 'is-active' : ''}`}
          onClick={() => setLocale('zh')}
        >
          {t('header.langZh')}
        </button>
        <button
          type="button"
          className={`prefs-seg__btn ${locale === 'en' ? 'is-active' : ''}`}
          onClick={() => setLocale('en')}
        >
          {t('header.langEn')}
        </button>
      </div>
      <button
        type="button"
        className="theme-toggle btn-ghost p-2"
        onClick={() => setTheme(theme === 'night' ? 'day' : 'night')}
        title={theme === 'night' ? t('header.themeDay') : t('header.themeNight')}
        aria-label={theme === 'night' ? t('header.themeDay') : t('header.themeNight')}
      >
        <span className="theme-toggle-icon" key={theme}>
          {theme === 'night' ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
        </span>
      </button>
    </div>
  )
}
