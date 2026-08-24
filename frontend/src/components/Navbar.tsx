import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2 group">
            <span className="text-orange-500 font-bold text-xl tracking-tight group-hover:text-orange-400 transition-colors">
              FPV
            </span>
            <span className="text-slate-100 font-semibold text-xl">Configs</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden sm:flex items-center gap-4">
            <Link
              to="/dashboard"
              className="text-slate-300 hover:text-orange-400 transition-colors font-medium"
            >
              My Configs
            </Link>
            {user?.is_admin && (
              <Link
                to="/admin"
                className="text-slate-300 hover:text-orange-400 transition-colors font-medium"
              >
                Admin
              </Link>
            )}

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 rounded-lg px-3 py-1.5 transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-orange-500 flex items-center justify-center text-white text-sm font-bold">
                  {user?.username[0]?.toUpperCase() ?? '?'}
                </div>
                <span className="text-slate-200 text-sm">{user?.username}</span>
                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-slate-700 rounded-lg shadow-lg border border-slate-600 py-1 z-50">
                  <div className="px-4 py-2 border-b border-slate-600">
                    <p className="text-sm font-medium text-slate-200">{user?.username}</p>
                    <p className="text-xs text-slate-400">{user?.email}</p>
                    {user?.is_admin && (
                      <span className="badge bg-orange-500/20 text-orange-400 mt-1">Admin</span>
                    )}
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-slate-600 transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Mobile menu button */}
          <button
            className="sm:hidden text-slate-300 hover:text-slate-100"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={menuOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'}
              />
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="sm:hidden pb-4 space-y-2 border-t border-slate-700 pt-4">
            <Link
              to="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="block text-slate-300 hover:text-orange-400 py-1 font-medium"
            >
              My Configs
            </Link>
            {user?.is_admin && (
              <Link
                to="/admin"
                onClick={() => setMenuOpen(false)}
                className="block text-slate-300 hover:text-orange-400 py-1 font-medium"
              >
                Admin
              </Link>
            )}
            <div className="pt-2 border-t border-slate-700">
              <p className="text-sm text-slate-400 mb-2">{user?.username} · {user?.email}</p>
              <button
                onClick={handleLogout}
                className="text-sm text-red-400 hover:text-red-300 font-medium"
              >
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Close menu on outside click */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setMenuOpen(false)}
        />
      )}
    </nav>
  )
}
