import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { ConfigurationSummary } from '../api/types'
import UploadModal from '../components/UploadModal'
import ConfirmModal from '../components/ConfirmModal'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function ConfigCard({
  config,
  onDelete,
}: {
  config: ConfigurationSummary
  onDelete: (id: string) => void
}) {
  return (
    <div className="card hover:border-slate-600 transition-colors group flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <Link
            to={`/configurations/${config.id}`}
            className="text-lg font-semibold text-slate-100 hover:text-orange-400 transition-colors truncate block"
          >
            {config.name}
          </Link>
          {config.craft_name && config.craft_name !== config.name && (
            <p className="text-slate-400 text-sm truncate">{config.craft_name}</p>
          )}
        </div>
        <button
          onClick={() => onDelete(config.id)}
          className="text-slate-600 hover:text-red-400 transition-colors ml-2 opacity-0 group-hover:opacity-100"
          title="Delete configuration"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-4 flex-1">
        {config.board_name && (
          <>
            <span className="text-slate-500">Board</span>
            <span className="text-slate-300 font-mono text-xs">{config.board_name}</span>
          </>
        )}
        {config.manufacturer_id && (
          <>
            <span className="text-slate-500">Manufacturer</span>
            <span className="text-slate-300 font-mono text-xs">{config.manufacturer_id}</span>
          </>
        )}
        {config.latest_revision?.betaflight_version && (
          <>
            <span className="text-slate-500">Betaflight</span>
            <span className="text-slate-300">{config.latest_revision.betaflight_version}</span>
          </>
        )}
        {config.pilot_name && (
          <>
            <span className="text-slate-500">Pilot</span>
            <span className="text-slate-300">{config.pilot_name}</span>
          </>
        )}
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-slate-700 text-xs text-slate-500">
        <span>
          {config.revision_count} revision{config.revision_count !== 1 ? 's' : ''}
        </span>
        <span>Created {formatDate(config.created_at)}</span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [showUpload, setShowUpload] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: configs, isLoading, error } = useQuery({
    queryKey: ['configurations'],
    queryFn: async () => {
      const { data } = await api.get<ConfigurationSummary[]>('/configurations')
      return data
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/configurations/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configurations'] })
      setDeleteId(null)
    },
  })

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My Configurations</h1>
          <p className="text-slate-400 text-sm mt-1">
            {configs?.length ?? 0} configuration{(configs?.length ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn-primary flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Config
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-900/20 border-red-800 text-red-400 text-center py-8">
          Failed to load configurations. Please refresh.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && configs?.length === 0 && (
        <div className="card text-center py-16">
          <svg className="w-16 h-16 text-slate-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-slate-400 text-lg font-medium mb-2">No configurations yet</p>
          <p className="text-slate-600 text-sm mb-6">
            Upload your first Betaflight CLI backup to get started.
          </p>
          <button onClick={() => setShowUpload(true)} className="btn-primary">
            Upload Configuration
          </button>
        </div>
      )}

      {/* Grid */}
      {!isLoading && !error && configs && configs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {configs.map((cfg) => (
            <ConfigCard key={cfg.id} config={cfg} onDelete={setDeleteId} />
          ))}
        </div>
      )}

      {/* Modals */}
      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}

      {deleteId && (
        <ConfirmModal
          title="Delete Configuration"
          message="This will permanently delete the configuration and all its revisions. This action cannot be undone."
          confirmLabel="Delete"
          isDanger
          isLoading={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleteId)}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  )
}
