import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { AdminConfigSummary, PaginatedResponse } from '../../api/types'
import ConfirmModal from '../../components/ConfirmModal'

export default function ConfigurationsManagement() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteConfig, setDeleteConfig] = useState<AdminConfigSummary | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-configurations', page, searchQuery],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: '20',
      })
      if (searchQuery) params.set('name', searchQuery)
      const { data } = await api.get<PaginatedResponse<AdminConfigSummary>>(
        `/admin/configurations?${params}`
      )
      return data
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (configId: string) => {
      await api.delete(`/admin/configurations/${configId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-configurations'] })
      setDeleteConfig(null)
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    setSearchQuery(search)
  }

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
          <h1 className="text-xl font-bold text-slate-100">All Configurations</h1>
          {data && <p className="text-slate-500 text-sm mt-0.5">{data.total} total</p>}
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input max-w-xs"
          placeholder="Search by name…"
        />
        <button type="submit" className="btn-secondary text-sm">
          Search
        </button>
        {searchQuery && (
          <button
            type="button"
            onClick={() => { setSearch(''); setSearchQuery(''); setPage(1) }}
            className="text-slate-400 hover:text-slate-200 text-sm px-2"
          >
            Clear
          </button>
        )}
      </form>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-700/50 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700">
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Board</th>
                <th className="px-4 py-3 text-left">Owner</th>
                <th className="px-4 py-3 text-left">Revisions</th>
                <th className="px-4 py-3 text-left">Updated</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {data?.items.map((cfg) => (
                <tr key={cfg.id} className="hover:bg-slate-700/20 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-200">{cfg.name}</p>
                    {cfg.craft_name && cfg.craft_name !== cfg.name && (
                      <p className="text-slate-500 text-xs">{cfg.craft_name}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-400 text-xs">
                    {cfg.board_name ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-400">{cfg.username}</td>
                  <td className="px-4 py-3 text-slate-400">{cfg.revision_count}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(cfg.updated_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setDeleteConfig(cfg)}
                      className="text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                    No configurations found.
                  </td>
                </tr>
              )}
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

      {deleteConfig && (
        <ConfirmModal
          title="Delete Configuration"
          message={`Delete "${deleteConfig.name}" (owner: ${deleteConfig.username}) and all its revisions? This cannot be undone.`}
          confirmLabel="Delete"
          isDanger
          isLoading={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleteConfig.id)}
          onCancel={() => setDeleteConfig(null)}
        />
      )}
    </div>
  )
}
