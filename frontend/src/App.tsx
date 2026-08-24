import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ConfigurationDetail from './pages/ConfigurationDetail'
import DiffView from './pages/DiffView'
import AdminLayout from './pages/admin/AdminLayout'
import UsersManagement from './pages/admin/UsersManagement'
import ConfigurationsManagement from './pages/admin/ConfigurationsManagement'
import Navbar from './components/Navbar'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user?.is_admin) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return null
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          <GuestOnly>
            <Login />
          </GuestOnly>
        }
      />
      <Route
        path="/register"
        element={
          <GuestOnly>
            <Register />
          </GuestOnly>
        }
      />

      {/* Authenticated routes */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <div className="min-h-screen bg-slate-900">
              <Navbar />
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Navigate to="/dashboard" replace />
              </main>
            </div>
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <div className="min-h-screen bg-slate-900">
              <Navbar />
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Dashboard />
              </main>
            </div>
          </RequireAuth>
        }
      />
      <Route
        path="/configurations/:configId"
        element={
          <RequireAuth>
            <div className="min-h-screen bg-slate-900">
              <Navbar />
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <ConfigurationDetail />
              </main>
            </div>
          </RequireAuth>
        }
      />
      <Route
        path="/configurations/:configId/diff/:rev1Id/:rev2Id"
        element={
          <RequireAuth>
            <div className="min-h-screen bg-slate-900">
              <Navbar />
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <DiffView />
              </main>
            </div>
          </RequireAuth>
        }
      />

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/admin/users" replace />} />
        <Route path="users" element={<UsersManagement />} />
        <Route path="configurations" element={<ConfigurationsManagement />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
