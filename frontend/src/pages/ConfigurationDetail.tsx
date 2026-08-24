import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { ConfigurationDetail as ConfigDetail } from '../api/types'
import RevisionList from '../components/RevisionList'
import UploadModal from '../components/UploadModal'
import ConfirmModal from '../components/ConfirmModal'

export default function ConfigurationDetail() {
  const { configId } = useParams<{ configId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showUpload, setShowUpload] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  const { data: config, isLoading, error } = useQuery({
    queryKey: ['configuration', configId],
    queryFn: async () => {
      const { data } = await api.get<ConfigDetail>(`/configurations/${configId}`)
      return data
    },
    enabled: !!configId,
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/configurations/${configId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configurations'] })
      navigate('/dashboard')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
      </div>
    )
  }

  if (error || !config) {
    return (
      <div className="card bg-red-900/20 border-red-800 text-red-400 text-center py-10">
        Configuration not found or access denied.{' '}
        <Link to="/dashboard" className="text-orange-400 underline">
          Back to dashboard
        </Link>
      </div>
    )
  }

  const latestRevision = config.revisions.at(-1)

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
        <span className="text-slate-300">{config.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">{config.name}</h1>
          {config.pilot_name && (
            <p className="text-slate-400 mt-1">Pilot: {config.pilot_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowUpload(true)} className="btn-secondary flex items-center gap-2 text-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            New Revision
          </button>
          <button
            onClick={() => setShowDelete(true)}
            className="btn-danger flex items-center gap-2 text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        </div>
      </div>

      {/* Metadata card */}
      <div className="card">
        <h2 className="text-sm font-semibold text-orange-400 uppercase tracking-wide mb-4">
          Configuration Details
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            ['Board', config.board_name],
            ['Manufacturer', config.manufacturer_id],
            ['Craft Name', config.craft_name],
            ['Pilot', config.pilot_name],
            ['Latest BF Version', latestRevision?.betaflight_version ?? null],
            ['MSP API', latestRevision?.msp_api_version ?? null],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">{label}</p>
              <p className="text-slate-200 font-mono text-sm">{value ?? '—'}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-slate-700 flex gap-6 text-xs text-slate-500">
          <span>Created {new Date(config.created_at).toLocaleDateString()}</span>
          <span>Updated {new Date(config.updated_at).toLocaleDateString()}</span>
          <span>{config.revisions.length} revision{config.revisions.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Revisions */}
      <div className="card">
        <RevisionList configId={config.id} revisions={config.revisions} />
      </div>

      {/* Modals */}
      {showUpload && (
        <UploadModal
          configId={configId}
          onClose={() => setShowUpload(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['configuration', configId] })
          }}
        />
      )}

      {showDelete && (
        <ConfirmModal
          title="Delete Configuration"
          message={`Delete "${config.name}" and all ${config.revisions.length} revision(s)? This cannot be undone.`}
          confirmLabel="Delete"
          isDanger
          isLoading={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setShowDelete(false)}
        />
      )}
    </div>
  )
}
