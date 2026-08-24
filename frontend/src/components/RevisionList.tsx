import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RevisionInfo } from '../api/types'
import api from '../api/client'

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
  const navigate = useNavigate()

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
                      <button
                        onClick={() => handleDownload(rev)}
                        className="text-slate-400 hover:text-orange-400 transition-colors"
                        title="Download"
                      >
                        <svg className="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
