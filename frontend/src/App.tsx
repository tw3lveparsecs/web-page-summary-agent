import { useState, useRef } from 'react'
import { useKV } from '@github/spark/hooks'
import { 
  Key, 
  ShieldCheck, 
  Play, 
  Stop,
  FileCode, 
  Globe, 
  Terminal, 
  FileText, 
  Download,
  Copy,
  CheckCircle,
  XCircle,
  Cloud,
  UserCircle
} from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ThemeProvider } from '@/components/theme-provider'
import { ThemeToggle } from '@/components/theme-toggle'
import type { AuthMethod, EntraAuthType, ExecutionStatus, ResultViewMode } from '@/lib/types'
import { toast } from 'sonner'

function App() {
  const [authMethod, setAuthMethod] = useKV<AuthMethod>('auth-method', 'entra')
  const [entraAuthType, setEntraAuthType] = useKV<EntraAuthType>('entra-auth-type', 'managed-identity')
  const [tenantId, setTenantId] = useKV('tenant-id', '')
  const [clientId, setClientId] = useKV('client-id', '')
  const [clientSecret, setClientSecret] = useKV('client-secret', '')
  const [apiKey, setApiKey] = useKV('api-key', '')
  const [foundryEndpoint, setFoundryEndpoint] = useKV('foundry-endpoint', '')
  const [foundryDeployment, setFoundryDeployment] = useKV('foundry-deployment', '')
  const [systemPrompt, setSystemPrompt] = useKV('system-prompt', 'You are a helpful assistant that summarises web content.')
  const [urlsText, setUrlsText] = useKV('urls-text', '')
  
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>('idle')
  const [resultOutput, setResultOutput] = useState('')
  const [resultViewMode, setResultViewMode] = useState<ResultViewMode>('console')
  const [summaries, setSummaries] = useState<{ title: string; summary: string; url: string }[]>([])
  const [errorMessage, setErrorMessage] = useState('')
  const abortControllerRef = useRef<AbortController | null>(null)

  const urls = (urlsText || '').split('\n').filter(url => url.trim() !== '')
  const urlCount = urls.length

  const isAuthValid = authMethod === 'entra' 
    ? entraAuthType === 'managed-identity' 
      ? clientId 
      : tenantId && clientId && clientSecret
    : apiKey

  const canExecute = foundryEndpoint && foundryDeployment && isAuthValid && systemPrompt && urlCount > 0 && executionStatus !== 'running'

  const getApiBaseUrl = () => {
    const envUrl = import.meta.env.VITE_API_URL
    if (envUrl) return envUrl.replace(/\/+$/, '')
    const { hostname, protocol } = window.location
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    return `${protocol}//${hostname.replace('-web', '-api')}`
  }

  const cancelAgent = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  const runAgent = async () => {
    setExecutionStatus('running')
    setErrorMessage('')
    setResultOutput('')
    setSummaries([])

    const controller = new AbortController()
    abortControllerRef.current = controller

    const baseUrl = getApiBaseUrl()
    console.log('[summariser] API base URL:', baseUrl)
    let output = ''

    try {
      const response = await fetch(`${baseUrl}/summarise`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          urls,
          foundry_endpoint: foundryEndpoint,
          foundry_deployment: foundryDeployment,
          system_prompt: systemPrompt,
          auth: {
            method: authMethod === 'entra' ? 'entra' : 'apikey',
            entra_type: authMethod === 'entra' ? entraAuthType : undefined,
            api_key: authMethod === 'apikey' ? apiKey : undefined,
            client_id: authMethod === 'entra' && entraAuthType === 'service-principal' ? clientId : undefined,
            tenant_id: authMethod === 'entra' && entraAuthType === 'service-principal' ? tenantId : undefined,
            client_secret: authMethod === 'entra' && entraAuthType === 'service-principal' ? clientSecret : undefined,
          },
        }),
      })

      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`API returned ${response.status}: ${detail}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7)
          } else if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))

            if (currentEvent === 'status') {
              output += `> ${data.message}\n`
              setResultOutput(output)
            } else if (currentEvent === 'error') {
              output += `\n**ERROR:** ${data.message}\n`
              setResultOutput(output)
            } else if (currentEvent === 'result') {
              if (!data.success) {
                output += `\n---\n\n## URL: ${data.url}\n\n**Error:** ${data.error}\n`
              } else {
                output += `\n---\n\n## ${data.title}\n\n**URL:** ${data.url}\n\n${data.summary}\n`
                setSummaries(prev => [...prev, { title: data.title, summary: data.summary, url: data.url }])
              }
              setResultOutput(output)
            } else if (currentEvent === 'done') {
              output += `\n---\n\n> Done — ${data.succeeded} succeeded, ${data.failed} failed out of ${data.total} URL(s)\n`
              setResultOutput(output)
            }
            currentEvent = ''
          }
        }
      }

      setExecutionStatus('success')
      toast.success('Agent execution completed successfully')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        output += '\n> **Cancelled by user**\n'
        setResultOutput(output)
        setExecutionStatus('idle')
        toast('Agent execution cancelled')
      } else {
        setExecutionStatus('error')
        setErrorMessage(error instanceof Error ? error.message : 'Unknown error occurred')
        toast.error('Agent execution failed')
      }
    } finally {
      abortControllerRef.current = null
    }
  }

  const downloadResult = () => {
    const blob = new Blob([resultOutput], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `foundry-results-${Date.now()}.${resultViewMode === 'markdown' ? 'md' : 'txt'}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Results downloaded')
  }

  const combinedSummaryText = summaries.map(s => s.summary).join('\n')

  const copySummaries = async () => {
    try {
      await navigator.clipboard.writeText(combinedSummaryText)
      toast.success('Summaries copied to clipboard')
    } catch {
      toast.error('Failed to copy to clipboard')
    }
  }

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-background p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <header className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <h1 className="font-mono text-3xl md:text-4xl font-bold text-accent tracking-tight">
                Web Page Summariser Agent
              </h1>
              <p className="text-muted-foreground text-sm md:text-base">
                Extracts content from any web page, including JavaScript rendered SPAs and dynamically loaded content, and generates structured summaries using Microsoft Foundry
              </p>
            </div>
            <ThemeToggle />
          </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-mono text-lg">
                <ShieldCheck className="text-accent" weight="bold" />
                Microsoft Foundry
              </CardTitle>
              <CardDescription>Endpoint, model deployment, and authentication</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="foundry-endpoint" className="text-xs uppercase tracking-wider text-muted-foreground">
                    Endpoint URL
                  </Label>
                  <Input
                    id="foundry-endpoint"
                    type="password"
                    placeholder="https://your-resource.cognitiveservices.azure.com/"
                    value={foundryEndpoint}
                    onChange={(e) => setFoundryEndpoint(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="foundry-deployment" className="text-xs uppercase tracking-wider text-muted-foreground">
                    Deployment Name
                  </Label>
                  <Input
                    id="foundry-deployment"
                    type="password"
                    placeholder="gpt-4o"
                    value={foundryDeployment}
                    onChange={(e) => setFoundryDeployment(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
              </div>

              <Separator />

              <Tabs value={authMethod} onValueChange={(v) => setAuthMethod(v as AuthMethod)}>
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="entra" className="font-mono text-xs md:text-sm">
                    <ShieldCheck className="mr-2 h-4 w-4" weight="bold" />
                    Entra ID
                  </TabsTrigger>
                  <TabsTrigger value="apikey" className="font-mono text-xs md:text-sm">
                    <Key className="mr-2 h-4 w-4" weight="bold" />
                    API Key
                  </TabsTrigger>
                </TabsList>
                
                <TabsContent value="entra" className="space-y-4">
                  <Tabs value={entraAuthType} onValueChange={(v) => setEntraAuthType(v as EntraAuthType)}>
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                      <TabsTrigger value="managed-identity" className="font-mono text-xs">
                        <Cloud className="mr-2 h-4 w-4" weight="bold" />
                        Managed Identity
                      </TabsTrigger>
                      <TabsTrigger value="service-principal" className="font-mono text-xs">
                        <UserCircle className="mr-2 h-4 w-4" weight="bold" />
                        Service Principal
                      </TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="managed-identity" className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="client-id-mi" className="text-xs uppercase tracking-wider text-muted-foreground">
                          Client ID
                        </Label>
                        <Input
                          id="client-id-mi"
                          type="password"
                          placeholder="00000000-0000-0000-0000-000000000000"
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                          className="font-mono text-sm"
                        />
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="service-principal" className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="tenant-id" className="text-xs uppercase tracking-wider text-muted-foreground">
                          Tenant ID
                        </Label>
                        <Input
                          id="tenant-id"
                          type="password"
                          placeholder="00000000-0000-0000-0000-000000000000"
                          value={tenantId}
                          onChange={(e) => setTenantId(e.target.value)}
                          className="font-mono text-sm"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="client-id" className="text-xs uppercase tracking-wider text-muted-foreground">
                          Client ID
                        </Label>
                        <Input
                          id="client-id"
                          type="password"
                          placeholder="00000000-0000-0000-0000-000000000000"
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                          className="font-mono text-sm"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="client-secret" className="text-xs uppercase tracking-wider text-muted-foreground">
                          Client Secret
                        </Label>
                        <Input
                          id="client-secret"
                          type="password"
                          placeholder="••••••••••••••••"
                          value={clientSecret}
                          onChange={(e) => setClientSecret(e.target.value)}
                          className="font-mono text-sm"
                        />
                      </div>
                    </TabsContent>
                  </Tabs>
                </TabsContent>
                
                <TabsContent value="apikey" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="api-key" className="text-xs uppercase tracking-wider text-muted-foreground">
                      API Key
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      placeholder="••••••••••••••••••••••••••••••••"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="font-mono text-sm"
                    />
                  </div>
                </TabsContent>
              </Tabs>
              
              <div className="mt-4 flex items-center gap-2">
                {isAuthValid ? (
                  <>
                    <CheckCircle className="text-accent h-5 w-5" weight="fill" />
                    <span className="text-sm text-accent font-medium">Credentials configured</span>
                  </>
                ) : (
                  <>
                    <XCircle className="text-muted-foreground h-5 w-5" weight="fill" />
                    <span className="text-sm text-muted-foreground">Credentials required</span>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-mono text-lg">
                <FileCode className="text-accent" weight="bold" />
                System Prompt
              </CardTitle>
              <CardDescription>Define how the AI should summarise content</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="You are a helpful assistant that summarises web content..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="font-mono text-sm min-h-[200px] resize-none"
              />
            </CardContent>
          </Card>

          <Card className="border-border lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 font-mono text-lg">
                  <Globe className="text-accent" weight="bold" />
                  URLs to Process
                </CardTitle>
                {urlCount > 0 && (
                  <Badge variant="secondary" className="font-mono">
                    {urlCount} URL{urlCount !== 1 ? 's' : ''}
                  </Badge>
                )}
              </div>
              <CardDescription>Enter one URL per line</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="https://example.com&#x0a;https://example.org&#x0a;https://example.net"
                value={urlsText}
                onChange={(e) => setUrlsText(e.target.value)}
                className="font-mono text-sm min-h-[150px] resize-none"
              />
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-center gap-3">
          <Button
            size="lg"
            onClick={runAgent}
            disabled={!canExecute}
            className="bg-accent text-accent-foreground hover:bg-accent/90 font-semibold px-8 transition-all duration-200"
          >
            {executionStatus === 'running' ? (
              <>
                <div className="animate-spin h-5 w-5 mr-2 border-2 border-accent-foreground border-t-transparent rounded-full" />
                Running Agent...
              </>
            ) : (
              <>
                <Play className="mr-2 h-5 w-5" weight="fill" />
                Run Agent
              </>
            )}
          </Button>
          {executionStatus === 'running' && (
            <Button
              size="lg"
              variant="destructive"
              onClick={cancelAgent}
              className="font-semibold px-8 transition-all duration-200"
            >
              <Stop className="mr-2 h-5 w-5" weight="fill" />
              Cancel
            </Button>
          )}
        </div>

        {errorMessage && (
          <Alert variant="destructive">
            <XCircle className="h-5 w-5" weight="fill" />
            <AlertDescription className="ml-2">{errorMessage}</AlertDescription>
          </Alert>
        )}

        {resultOutput && (
          <Card className="border-border">
            <CardHeader>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <CardTitle className="flex items-center gap-2 font-mono text-lg">
                  {executionStatus === 'success' && (
                    <CheckCircle className="text-accent" weight="fill" />
                  )}
                  Results
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Tabs value={resultViewMode} onValueChange={(v) => setResultViewMode(v as ResultViewMode)}>
                    <TabsList>
                      <TabsTrigger value="console" className="font-mono text-xs">
                        <Terminal className="mr-2 h-4 w-4" weight="bold" />
                        Console
                      </TabsTrigger>
                      <TabsTrigger value="markdown" className="font-mono text-xs">
                        <FileText className="mr-2 h-4 w-4" weight="bold" />
                        Markdown
                      </TabsTrigger>
                      <TabsTrigger value="summary" className="font-mono text-xs">
                        <Copy className="mr-2 h-4 w-4" weight="bold" />
                        Combined
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                  <Separator orientation="vertical" className="h-8" />
                  {resultViewMode === 'summary' && summaries.length > 0 && (
                    <Button variant="outline" size="sm" onClick={copySummaries}>
                      <Copy className="mr-2 h-4 w-4" weight="bold" />
                      Copy
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={downloadResult}>
                    <Download className="mr-2 h-4 w-4" weight="bold" />
                    Download
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] w-full rounded-md border border-border p-4">
                {resultViewMode === 'summary' ? (
                  summaries.length > 0 ? (
                    <pre className="font-mono text-xs md:text-sm text-foreground whitespace-pre-wrap">{combinedSummaryText}</pre>
                  ) : (
                    <p className="text-sm text-muted-foreground">No summaries yet. Summaries will appear here as they are processed.</p>
                  )
                ) : (
                  <pre className="font-mono text-xs md:text-sm text-foreground whitespace-pre-wrap">
                    {resultOutput}
                  </pre>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
    </ThemeProvider>
  )
}

export default App
