import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import { auditChainApi } from '../../api/auditChain'
import type { AuditEventItem, Page } from '../../api/auditChain'
import { useAuth } from '../../hooks/useAuth'

const PAGE_SIZE = 25

const EVENT_TYPE_OPTIONS = [
  '',
  'auth.password.login',
  'auth.password.changed',
  'auth.password.admin_reset',
  'auth.mfa.totp.enabled',
  'auth.mfa.totp.disabled',
  'auth.mfa.admin_reset',
  'auth.passkey.registered',
  'auth.passkey.login',
  'auth.passkey.revoked',
  'auth.user.deactivated',
  'auth.user.updated',
  'auth.user.deleted',
  'invite.created',
]

export function AuditLog() {
  const { user } = useAuth()
  const orgId = user?.org_id

  const [page, setPage] = useState(1)
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [createdAfter, setCreatedAfter] = useState('')

  const { data, isLoading, error } = useQuery<AxiosResponse<Page<AuditEventItem>>>({
    queryKey: ['audit-events', orgId, page, eventTypeFilter, createdAfter],
    queryFn: () =>
      auditChainApi.listAuthEvents(orgId!, page, PAGE_SIZE, {
        eventType: eventTypeFilter || undefined,
        createdAfter: createdAfter || undefined,
      }),
    enabled: !!orgId,
  })

  if (!orgId) return <div className="text-sm text-gray-500">Org não encontrada.</div>
  if (isLoading) return <div className="text-sm text-gray-500">Carregando auditoria...</div>
  if (error) return <div className="text-sm text-red-600">Erro ao carregar auditoria.</div>

  const items = data?.data.items ?? []
  const total = data?.data.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const resetFilters = () => {
    setEventTypeFilter('')
    setCreatedAfter('')
    setPage(1)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Auditoria de Ações Sensíveis</h2>
        <span className="text-xs text-gray-400">{total} evento{total !== 1 ? 's' : ''} encontrado{total !== 1 ? 's' : ''}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <select
          value={eventTypeFilter}
          onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs focus:border-brand-500 focus:outline-none"
        >
          <option value="">Todos os tipos</option>
          {EVENT_TYPE_OPTIONS.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={createdAfter}
          onChange={(e) => { setCreatedAfter(e.target.value); setPage(1) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs focus:border-brand-500 focus:outline-none"
        />

        <button
          onClick={resetFilters}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          Limpar filtros
        </button>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-gray-500">Nenhum evento encontrado.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs border border-gray-200 rounded">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="p-2 border-b text-left whitespace-nowrap">Data (UTC)</th>
                <th className="p-2 border-b text-left whitespace-nowrap">Tipo</th>
                <th className="p-2 border-b text-left">Entidade</th>
                <th className="p-2 border-b text-left">ID</th>
                <th className="p-2 border-b text-left">Ator</th>
                <th className="p-2 border-b text-left">Payload</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <tr key={ev.id} className="hover:bg-gray-50">
                  <td className="p-2 border-b whitespace-nowrap">
                    {new Date(ev.created_at).toISOString().replace('T', ' ').slice(0, 19)} UTC
                  </td>
                  <td className="p-2 border-b font-mono whitespace-nowrap">{ev.event_type}</td>
                  <td className="p-2 border-b">{ev.entity_type}</td>
                  <td className="p-2 border-b font-mono text-gray-400 max-w-[8rem] truncate" title={ev.entity_id}>
                    {ev.entity_id}
                  </td>
                  <td className="p-2 border-b font-mono text-gray-400 max-w-[8rem] truncate" title={ev.actor_user_id ?? ''}>
                    {ev.actor_user_id ?? '—'}
                  </td>
                  <td className="p-2 border-b max-w-xs truncate text-gray-500" title={JSON.stringify(ev.payload)}>
                    {JSON.stringify(ev.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
          >
            Anterior
          </button>
          <span>Página {page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
