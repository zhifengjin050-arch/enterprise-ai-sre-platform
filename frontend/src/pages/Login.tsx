import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { usePrefs } from '../store/prefs'
import PrefsToggles from '../ui/PrefsToggles'

export default function Login() {
  const { login, register } = useAuth()
  const { t } = usePrefs()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'register') {
        await register(username, email || `${username}@local.test`, password)
      } else {
        await login(username, password)
      }
      navigate('/overview')
    } catch (err: any) {
      setError(err.response?.data?.detail || (mode === 'register' ? t('login.failRegister') : t('login.failLogin')))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="theme-canvas min-h-screen text-ink grid grid-cols-1 lg:grid-cols-2">
      <div className="theme-chrome hidden lg:flex flex-col justify-between p-12 border-r border-line">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-ink-muted">{t('login.kicker')}</p>
          <h1 className="text-3xl font-semibold text-ink mt-3 leading-tight">
            {t('login.headline1')}
            <br />
            {t('login.headline2')}
          </h1>
          <p className="text-sm text-ink-muted mt-4 max-w-md">{t('login.desc')}</p>
        </div>
        <p className="text-xs text-ink-muted">{t('login.footer')}</p>
      </div>

      <div className="flex items-center justify-center p-8 relative">
        <div className="absolute top-6 right-6">
          <PrefsToggles />
        </div>
        <div className="w-full max-w-sm">
          <h2 className="text-xl font-semibold mb-1">
            {mode === 'login' ? t('login.titleLogin') : t('login.titleRegister')}
          </h2>
          <p className="text-sm text-ink-muted mb-6">{t('login.subtitle')}</p>

          {error && (
            <div className="bg-danger/10 border border-danger/20 text-danger text-sm rounded-lg p-3 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-ink-muted mb-1">{t('login.username')}</label>
              <input
                type="text"
                className="input-field"
                placeholder={t('login.usernamePh')}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            {mode === 'register' && (
              <div>
                <label className="block text-xs text-ink-muted mb-1">{t('login.email')}</label>
                <input
                  type="email"
                  className="input-field"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-ink-muted mb-1">{t('login.password')}</label>
              <input
                type="password"
                className="input-field"
                placeholder={t('login.passwordPh')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading
                ? t('login.processing')
                : mode === 'login'
                  ? t('login.submitLogin')
                  : t('login.submitRegister')}
            </button>
          </form>

          <button
            className="mt-4 text-sm text-ink-muted hover:text-ink"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError('')
            }}
          >
            {mode === 'login' ? t('login.goRegister') : t('login.goLogin')}
          </button>
        </div>
      </div>
    </div>
  )
}
