import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout() {
  const { pathname } = useLocation()
  const fullBleed = pathname === '/ops' || pathname === '/chat'

  return (
    <div className="theme-canvas flex h-screen overflow-hidden transition-colors duration-300">
      <Sidebar />
      <div className="theme-canvas flex-1 flex flex-col overflow-hidden min-w-0">
        <Header />
        <main className={`theme-canvas flex-1 overflow-hidden ${fullBleed ? '' : 'overflow-y-auto p-6'}`}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
