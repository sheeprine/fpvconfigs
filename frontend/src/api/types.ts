export interface User {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active: boolean
}

export interface RevisionInfo {
  id: string
  revision_number: number
  betaflight_version: string | null
  msp_api_version: string | null
  config_revision: string | null
  file_size: number
  created_at: string
}

export interface ConfigurationSummary {
  id: string
  name: string
  board_name: string | null
  manufacturer_id: string | null
  craft_name: string | null
  pilot_name: string | null
  created_at: string
  updated_at: string
  revision_count: number
  latest_revision: RevisionInfo | null
}

export interface ConfigurationDetail {
  id: string
  name: string
  board_name: string | null
  manufacturer_id: string | null
  craft_name: string | null
  pilot_name: string | null
  created_at: string
  updated_at: string
  revisions: RevisionInfo[]
}

export interface DiffResponse {
  diff: string
  rev1: RevisionInfo
  rev2: RevisionInfo
}

export interface AdminUser {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface AdminConfigSummary {
  id: string
  name: string
  board_name: string | null
  craft_name: string | null
  pilot_name: string | null
  user_id: string
  username: string
  revision_count: number
  created_at: string
  updated_at: string
}
