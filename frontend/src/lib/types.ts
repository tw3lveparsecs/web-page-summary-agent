export type AuthMethod = 'entra' | 'apikey'

export type EntraAuthType = 'managed-identity' | 'service-principal'

export interface EntraCredentials {
  authType: EntraAuthType
  clientId: string
  tenantId?: string
  clientSecret?: string
}

export interface ApiKeyCredentials {
  apiKey: string
}

export interface AgentConfig {
  authMethod: AuthMethod
  entraCredentials: EntraCredentials
  apiKeyCredentials: ApiKeyCredentials
  systemPrompt: string
  urls: string[]
}

export interface AgentResult {
  success: boolean
  output: string
  timestamp: number
}

export type ExecutionStatus = 'idle' | 'running' | 'success' | 'error'

export type ResultViewMode = 'console' | 'markdown'
