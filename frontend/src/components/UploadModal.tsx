import React, { useCallback, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { ConfigurationDetail } from '../api/types'

interface ParsedPreview {
  betaflight_version: string | null
  board_name: string | null
  manufacturer_id: string | null
  craft_name: string | null
  pilot_name: string | null
  config_revision: string | null
}

function parseConfigPreview(text: string): ParsedPreview | null {
  // Quick client-side parse for preview
  const versionMatch = text.match(/# Betaflight \/ \S+ \([^)]+\)\s+(\d+\.\d+(?:\.\d+)?)/i)
  const boardMatch = text.match(/^board_name\s+(\S+)/im)
  const mfrMatch = text.match(/^manufacturer_id\s+(\S+)/im)
  const craftMatch =
    text.match(/^set\s+craft_name\s*=\s*(.+)$/im) ||
    text.match(/^#\s+name:\s*(.+)$/im) ||
    text.match(/^name\s+(.+)$/im)
  const pilotMatch = text.match(/^set\s+pilot_name\s*=\s*(.+)$/im)
  const revMatch = text.match(/# config rev:\s*(\S+)/i)

  // Must have version header to be valid
  if (!versionMatch) return null

  return {
    betaflight_version: versionMatch?.[1] ?? null,
    board_name: boardMatch?.[1] ?? null,
    manufacturer_id: mfrMatch?.[1] ?? null,
    craft_name: craftMatch?.[1]?.trim() ?? null,
    pilot_name: pilotMatch?.[1]?.trim() ?? null,
    config_revision: revMatch?.[1] ?? null,
  }
}

interface UploadModalProps {
  configId?: string // If provided, uploading a new revision
  onClose: () => void
  onSuccess?: (config: ConfigurationDetail) => void
}

export default function UploadModal({ configId, onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ParsedPreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const MAX_SIZE = 64 * 1024 // 64KB, matches backend Settings.max_upload_size

  const handleFile = useCallback((f: File) => {
    setError(null)
    setPreviewError(null)
    setPreview(null)

    if (f.size > MAX_SIZE) {
      setError('File exceeds 64KB maximum size.')
      return
    }

    setFile(f)

    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      const parsed = parseConfigPreview(text)
      if (!parsed) {
        setPreviewError('File does not appear to be a valid Betaflight CLI backup.')
      } else {
        setPreview(parsed)
      }
    }
    reader.readAsText(f)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setDragOver(false)
      const dropped = e.dataTransfer.files[0]
      if (dropped) handleFile(dropped)
    },
    [handleFile]
  )

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected')
      const formData = new FormData()
      formData.append('file', file)

      const url = configId ? `/configurations/${configId}/revisions` : '/configurations'
      const { data } = await api.post<ConfigurationDetail>(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['configurations'] })
      if (configId) {
        queryClient.invalidateQueries({ queryKey: ['configuration', configId] })
      }
      onSuccess?.(data)
      onClose()
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Upload failed. Please try again.'
      setError(message)
    },
  })

  const canUpload = file !== null && preview !== null && !mutation.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-lg shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">
            {configId ? 'Upload New Revision' : 'Upload Configuration'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? 'border-orange-500 bg-orange-500/10'
              : 'border-slate-600 hover:border-slate-500 bg-slate-700/50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.conf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFile(f)
            }}
          />
          {file ? (
            <div>
              <svg className="w-8 h-8 text-orange-500 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-slate-200 font-medium">{file.name}</p>
              <p className="text-slate-400 text-sm">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div>
              <svg className="w-10 h-10 text-slate-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-slate-300 font-medium">Drop your Betaflight backup here</p>
              <p className="text-slate-500 text-sm mt-1">or click to browse · .txt files up to 64KB</p>
            </div>
          )}
        </div>

        {/* Preview */}
        {preview && (
          <div className="mt-4 bg-slate-700/50 rounded-lg p-4 space-y-2">
            <h3 className="text-sm font-semibold text-orange-400 uppercase tracking-wide">
              Config Preview
            </h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              {[
                ['Betaflight', preview.betaflight_version],
                ['Board', preview.board_name],
                ['Manufacturer', preview.manufacturer_id],
                ['Craft Name', preview.craft_name],
                ['Pilot', preview.pilot_name],
                ['Config Rev', preview.config_revision],
              ].map(([label, value]) =>
                value ? (
                  <div key={label} className="flex gap-1">
                    <span className="text-slate-400">{label}:</span>
                    <span className="text-slate-200 font-mono truncate">{value}</span>
                  </div>
                ) : null
              )}
            </div>
          </div>
        )}

        {/* Errors */}
        {(previewError || error) && (
          <div className="mt-3 bg-red-900/30 border border-red-800 rounded-lg px-4 py-2 text-sm text-red-400">
            {previewError || error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-5 justify-end">
          <button onClick={onClose} className="btn-secondary" disabled={mutation.isPending}>
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!canUpload}
            className="btn-primary"
          >
            {mutation.isPending ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Uploading…
              </span>
            ) : (
              'Upload'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
