import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import api from '../../api/client'
import { AdminUser, PaginatedResponse } from '../../api/types'
import ConfirmModal from '../../components/ConfirmModal'

// ── User form modal ───────────────────────────────────────────────────────────

interface UserFormProps {
  user?: AdminUser
  onClose: () => void
  onSaved: () => void
}

function UserFormModal({ user, onClose, onSaved }: UserFormProps) {
  const [username, setUsername] = useState(user?.username ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [password, setPassword] = useState('')
  const [isAdmin, setIsAdmin] = useState(user?.is_admin ?? false)
  const [isActive, setIsActive] = useState(user?.is_active ?? true)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      if (user) {
        // Update
        const body: Record<string, unknown> = { username, email, is_admin: isAdmin, is_active: isActive }
        if (password) body.password = password
        await api.put(`/admin/users/${user.id}`, body)
      } else {
        // Create
        await api.post('/admin/users', { username, email, password, is_admin: isAdmin })
      }
      onSaved()
      onClose()
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>
      setError(axiosErr.response?.data?.detail ?? 'Save failed.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">
          {user ? 'Edit User' : 'Create User'}
        </h2>

        {error && (
          <div className="mb-4 bg-red-900/30 border border-red-800 rounded-lg px-4 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input"
              required
              minLength={3}
              maxLength={64}
            />
          </div>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              required
            />
          </div>
          <div>
            <label className="label">{user ? 'New Password (leave blank to keep)' : 'Password'}</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              placeholder={user ? '••••••••' : 'At least 8 characters'}
              minLength={user ? undefined : 8}
              required={!user}
            />
          </div>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-orange-500 focus:ring-orange-500"
              />
              <span className="text-slate-300 text-sm">Administrator</span>
            </label>
            {user && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-orange-500 focus:ring-orange-500"
                />
                <span className="text-slate-300 text-sm">Active</span>
              </label>
            )}
          </div>

          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary" disabled={isLoading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Saving…' : user ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UsersManagement() {
  const [page, setPage] = useState(1)
  const [editUser, setEditUser] = useState<AdminUser | null | 'new'>(null)
  const [deleteUser, setDeleteUser] = useState<AdminUser | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<AdminUser>>(
        `/admin/users?page=${page}&page_size=20`
      )
      return data
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/admin/users/${userId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setDeleteUser(null)
    },
  })

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Users</h1>
          {data && <p className="text-slate-500 text-sm mt-0.5">{data.total} total</p>}
        </div>
        <button onClick={() => setEditUser('new')} className="btn-primary text-sm flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New User
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-700/50 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700">
                <th className="px-4 py-3 text-left">Username</th>
                <th className="px-4 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Role</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {data?.items.map((u) => (
                <tr key={u.id} className="hover:bg-slate-700/20 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-200">{u.username}</td>
                  <td className="px-4 py-3 text-slate-400">{u.email}</td>
                  <td className="px-4 py-3">
                    {u.is_admin ? (
                      <span className="badge bg-orange-500/20 text-orange-400">Admin</span>
                    ) : (
                      <span className="badge bg-slate-700 text-slate-400">User</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="badge bg-green-900/40 text-green-400">Active</span>
                    ) : (
                      <span className="badge bg-red-900/40 text-red-400">Disabled</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditUser(u)}
                        className="text-slate-400 hover:text-orange-400 transition-colors"
                        title="Edit"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setDeleteUser(u)}
                        className="text-slate-400 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {data && data.total > data.page_size && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700 text-sm text-slate-400">
              <span>
                Page {data.page} of {Math.ceil(data.total / data.page_size)}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary text-xs py-1 px-2"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= Math.ceil(data.total / data.page_size)}
                  className="btn-secondary text-xs py-1 px-2"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {editUser !== null && (
        <UserFormModal
          user={editUser === 'new' ? undefined : editUser}
          onClose={() => setEditUser(null)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['admin-users'] })}
        />
      )}

      {deleteUser && (
        <ConfirmModal
          title="Delete User"
          message={`Delete user "${deleteUser.username}" and all their configurations? This cannot be undone.`}
          confirmLabel="Delete User"
          isDanger
          isLoading={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleteUser.id)}
          onCancel={() => setDeleteUser(null)}
        />
      )}
    </div>
  )
}
