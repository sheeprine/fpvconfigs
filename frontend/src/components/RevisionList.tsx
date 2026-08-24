import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { RevisionInfo } from '../api/types'
import api from '../api/client'
import ConfirmModal from './ConfirmModal'

interface RevisionListProps {
  configId: string
  revisions: RevisionInfo[]
  onDownload?: (revisionId: string) => void
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

export default function RevisionList({ configId, revisions, onDownload }: RevisionListProps) {
  const [selected, setSelected] = useState<string[]>([])
  const [revisionToDelete, setRevisionToDelete] = useState<RevisionInfo | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: async (revisionId: string) => {
      await api.delete(`/configurations/${configId}/revisions/${revisionId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configuration', configId] })
      setRevisionToDelete(null)
    },
  })

  const toggle = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return [prev[1], id]
      return [...prev, id]
    })
  }

  const canDiff = selected.length === 2

  const handleDiff = () => {
    if (!canDiff) return
    navigate(`/configurations/${configId}/diff/${selected[0]}/${selected[1]}`)
  }

  const handleDownload = async (revision: RevisionInfo) => {
    try {
      const { data } = await api.get<{ content: string }>(
        `/configurations/${configId}/revisions/${revision.id}/content`
      )
      const blob = new Blob([data.content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `config-rev${revision.revision_number}.txt`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download failed', e)
    }
    onDownload?.(revision.id)
  }

  const sorted = [...revisions].sort((a, b) => b.revision_number - a.revision_number)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-slate-100">Revisions</h3>
        {selected.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            {selected.length < 2 && <span>Select one more revision to compare</span>}
            <button
              onClick={handleDiff}
              disabled={!canDiff}
              className="btn-primary text-sm py-1.5"
            >
              Compare Selected
            </button>
          </div>
        )}
      </div>

      {sorted.length === 0 ? (
        <p className="text-slate-500 text-sm">No revisions yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-700/50 text-slate-400 text-xs uppercase tracking-wider">
                <th className="px-3 py-2 text-left w-8">
                  <span className="sr-only">Select</span>
                </th>
                <th className="px-3 py-2 text-left">Rev</th>
                <th className="px-3 py-2 text-left">Betaflight</th>
                <th className="px-3 py-2 text-left">Config Hash</th>
                <th className="px-3 py-2 text-left">Size</th>
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {sorted.map((rev) => {
                const isSelected = selected.includes(rev.id)
                return (
                  <tr
                    key={rev.id}
                    className={`transition-colors ${
                      isSelected ? 'bg-orange-500/10' : 'hover:bg-slate-700/30'
                    }`}
                  >
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggle(rev.id)}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-orange-500 focus:ring-orange-500 focus:ring-offset-slate-800"
                      />
                    </td>
                    <td className="px-3 py-3 font-mono text-orange-400 font-semibold">
                      #{rev.revision_number}
                    </td>
                    <td className="px-3 py-3 text-slate-200">
                      {rev.betaflight_version ?? '—'}
                    </td>
                    <td className="px-3 py-3 font-mono text-slate-400 text-xs">
                      {rev.config_revision ?? '—'}
                    </td>
                    <td className="px-3 py-3 text-slate-400">
                      {formatBytes(rev.file_size)}
                    </td>
                    <td className="px-3 py-3 text-slate-400 whitespace-nowrap">
                      {formatDate(rev.created_at)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button
                          onClick={() => handleDownload(rev)}
                          className="text-slate-400 hover:text-orange-400 transition-colors"
                          title="Download"
                        >
                          <svg className="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                        </button>
                        <button
                          onClick={() => setRevisionToDelete(rev)}
                          disabled={sorted.length <= 1}
                          className="text-slate-400 hover:text-red-400 transition-colors disabled:opacity-30 disabled:hover:text-slate-400 disabled:cursor-not-allowed"
                          title={sorted.length <= 1 ? 'Cannot delete the only revision' : 'Delete revision'}
                        >
                          <svg className="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {revisionToDelete && (
        <ConfirmModal
          title="Delete Revision"
          message={`Delete revision #${revisionToDelete.revision_number}? This cannot be undone.`}
          confirmLabel="Delete"
          isDanger
          isLoading={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(revisionToDelete.id)}
          onCancel={() => setRevisionToDelete(null)}
        />
      )}
    </div>
  )
}
