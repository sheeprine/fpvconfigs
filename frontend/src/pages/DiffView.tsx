import { useEffect, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as Diff2Html from 'diff2html'
import 'diff2html/bundles/css/diff2html.min.css'
import api from '../api/client'
import { DiffResponse } from '../api/types'

export default function DiffView() {
  const { configId, rev1Id, rev2Id } = useParams<{
    configId: string
    rev1Id: string
    rev2Id: string
  }>()
  const diffContainerRef = useRef<HTMLDivElement>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['diff', configId, rev1Id, rev2Id],
    queryFn: async () => {
      const { data } = await api.get<DiffResponse>(
        `/configurations/${configId}/diff/${rev1Id}/${rev2Id}`
      )
      return data
    },
    enabled: !!(configId && rev1Id && rev2Id),
  })

  useEffect(() => {
    if (!data || !diffContainerRef.current) return

    const html = Diff2Html.html(data.diff, {
      drawFileList: false,
      matching: 'lines',
      outputFormat: 'side-by-side',
      renderNothingWhenEmpty: false,
    })
    diffContainerRef.current.innerHTML = html
  }, [data])

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-orange-400 transition-colors">
          My Configs
        </Link>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <Link
          to={`/configurations/${configId}`}
          className="hover:text-orange-400 transition-colors"
        >
          Configuration
        </Link>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-slate-300">Diff</span>
      </nav>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">Revision Comparison</h1>
        <Link to={`/configurations/${configId}`} className="btn-secondary text-sm">
          Back to Config
        </Link>
      </div>

      {/* Revision metadata */}
      {data && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'From', rev: data.rev1 },
            { label: 'To', rev: data.rev2 },
          ].map(({ label, rev }) => (
            <div key={rev.id} className="card">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">{label}</p>
              <div className="flex items-baseline gap-2">
                <span className="text-orange-400 font-bold font-mono text-lg">
                  #{rev.revision_number}
                </span>
                {rev.betaflight_version && (
                  <span className="text-slate-300 text-sm">BF {rev.betaflight_version}</span>
                )}
              </div>
              {rev.config_revision && (
                <p className="text-slate-500 font-mono text-xs mt-1">
                  config rev: {rev.config_revision}
                </p>
              )}
              <p className="text-slate-600 text-xs mt-1">{formatDate(rev.created_at)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-900/20 border-red-800 text-red-400 text-center py-8">
          Failed to load diff. Please try again.
        </div>
      )}

      {/* Empty diff */}
      {data && !data.diff && (
        <div className="card text-center py-10">
          <p className="text-slate-400">These revisions are identical — no differences found.</p>
        </div>
      )}

      {/* Diff output */}
      {data && data.diff && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 bg-slate-700/50 border-b border-slate-700 flex items-center gap-2">
            <svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            <span className="text-slate-300 text-sm font-medium">
              Side-by-side diff · revision #{data.rev1.revision_number} → #{data.rev2.revision_number}
            </span>
          </div>
          <div className="overflow-x-auto">
            <div ref={diffContainerRef} className="d2h-wrapper" />
          </div>
        </div>
      )}
    </div>
  )
}
