export interface ClientOptions {
  endpoint: string
  appId: string
  appSecret: string
  instanceId: string
  orgId?: string
  timeout?: number
  source?: string
}
export interface RequestOptions {
  signal?: AbortSignal
}
export interface EventHandlerOptions {
  readonly signal: AbortSignal
}
export interface KnownRevision {
  key: string
  revision: number
}
export interface Credential {
  key: string
  revision: number
  /** True only when an unavailable backend required using the latest retained credential. */
  readonly fromLocal: boolean
  asset: {
    id: string
    name: string
    address: string
    platform: { id: string; name: string; category: string; type: string }
  }
  account: { id: string; name: string; username: string; secretType: string; secret: string }
}
export interface CredentialConfirmation extends KnownRevision {}
export interface SnapshotCredential extends KnownRevision {
  credentialMode: string
  accountId?: string
}
export interface Event {
  event: string
  eventId?: string
  commandId?: string
  credentialKey?: string
  key?: string
  credentialMode?: string
  accountId?: string
  revision?: number
  credentials?: SnapshotCredential[]
  [name: string]: unknown
}
export interface CommandResult {
  accepted: boolean
  status: string
}
export interface EventSubscription {
  readonly done: Promise<void>
  readonly running: boolean
  stop(): Promise<void>
}
export interface AgentSync {
  configDigest: string
  dateLastSynced: string
  credentials: Array<KnownRevision & { available: boolean; changed: boolean }>
  removedKeys: string[]
  scope?: Record<string, unknown> | null
}
export class PAMError extends Error {
  code: string
  statusCode?: number
  detail?: string
  requestId?: string
}
export class Client {
  constructor(options: ClientOptions)
  getCredential(
    options: RequestOptions & { allowLocalFallback?: boolean } &
      ({ key: string; accountId?: never } | { key?: never; accountId: string }),
  ): Promise<Credential>
  confirmCredential(
    options: RequestOptions & { key: string; revision: number; accountId: string },
  ): Promise<CredentialConfirmation>
  watchCredentialEvents(options?: RequestOptions): AsyncGenerator<Event>
  watchEvents(options?: RequestOptions): Promise<void>
  startEvents(options?: RequestOptions): EventSubscription
  stopEvents(): Promise<void>
  onEvent(event: Event, options: EventHandlerOptions): void | Promise<void>
  onCredentialChanged(credential: Credential, options: EventHandlerOptions): void | Promise<void>
  onCredentialRevoked(event: Event, options: EventHandlerOptions): void | Promise<void>
  onEventError(error: unknown, event?: Event): void | Promise<void>
  listApplicationCommands(options?: RequestOptions): Promise<Event[]>
  reportApplicationCommandResult(
    options: RequestOptions & {
      commandId: string
      status: 'running' | 'success' | 'failed'
      errorCode?: string
    },
  ): Promise<CommandResult>
  executeApplicationCommand(
    event: Event,
    handler: (event: Event) => unknown | Promise<unknown>,
    options?: RequestOptions,
  ): Promise<CommandResult>
  syncAgent(
    options: RequestOptions & {
      credentials: KnownRevision[]
      deliveredCredentials: KnownRevision[]
      configDigest?: string
      syncStatus?: string
      syncError?: string
    },
  ): Promise<AgentSync>
  clone(): Client
  close(): void
}
export const VERSION: string
export const PROTOCOL_VERSION: number
export const CONFIG_SCHEMA_VERSION: number
