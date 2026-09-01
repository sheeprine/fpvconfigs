import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { RevisionInfo } from '../api/types'
import BetaflightSyntax from '../components/BetaflightSyntax'

interface RevisionContentResponse {
  content: string
  revision: RevisionInfo
}

export default function RevisionView() {
  const { configId, revisionId } = useParams<{ configId: string; revisionId: string }>()

  const { data, isLoading, error } = useQuery({
    queryKey: ['revision-content', configId, revisionId],
    queryFn: async () => {
      const { data } = await api.get<RevisionContentResponse>(
        `/configurations/${configId}/revisions/${revisionId}/content`
      )
      return data
    },
    enabled: !!(configId && revisionId),
  })

  const handleDownload = () => {
    if (!data) return
    const blob = new Blob([data.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `config-rev${data.revision.revision_number}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

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
        <span className="text-slate-300">
          Revision {data ? `#${data.revision.revision_number}` : ''}
        </span>
      </nav>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">
          Revision {data ? `#${data.revision.revision_number}` : ''}
        </h1>
        <div className="flex items-center gap-2">
          <button onClick={handleDownload} disabled={!data} className="btn-secondary text-sm">
            Download
          </button>
          <Link to={`/configurations/${configId}`} className="btn-secondary text-sm">
            Back to Config
          </Link>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
        </div>
      )}

      {error && (
        <div className="card bg-red-900/20 border-red-800 text-red-400 text-center py-8">
          Failed to load revision content.
        </div>
      )}

      {data && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 bg-slate-700/50 border-b border-slate-700 flex items-center gap-2">
            <svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="text-slate-300 text-sm font-medium">
              {data.revision.betaflight_version
                ? `Betaflight ${data.revision.betaflight_version}`
                : 'Config content'}
              {data.revision.config_revision && ` · config rev: ${data.revision.config_revision}`}
            </span>
          </div>
          <BetaflightSyntax content={data.content} />
        </div>
      )}
    </div>
  )
}
