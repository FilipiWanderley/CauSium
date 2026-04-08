import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../api/admin'
import type { AdminOrgListItem, AdminUserItem } from '../../api/admin'
import { Shield, Users, Ban, RefreshCw, Archive, ChevronLeft, ChevronRight, KeyRound } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { Navigate } from 'react-router-dom'

const STATE_BADGE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  suspended: 'bg-yellow-100 text-yellow-700',
  archived: 'bg-gray-100 text-gray-500',
}

type ActionType = 'suspend' | 'restore' | 'archive' | null

interface ActionDialogState {
  action: ActionType
  org: AdminOrgListItem | null
  reason: string
}

interface UserActionFeedback {
  level: 'success' | 'error'
  message: string
}

const PAGE_SIZE = 20

export function WorkspacesPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState<ActionDialogState>({ action: null, org: null, reason: '' })
  const [expandedOrgId, setExpandedOrgId] = useState<string | null>(null)
  const [userFeedback, setUserFeedback] = useState<UserActionFeedback | null>(null)

  if (user?.role !== 'platform_admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const { data, isLoading } = useQuery({
    queryKey: ['admin-orgs', page],
    queryFn: () => adminApi.listOrgs(page, PAGE_SIZE).then((r) => r.data),
  })

  const { data: expandedUsers, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-org-users', expandedOrgId],
    queryFn: () => adminApi.listOrgUsers(expandedOrgId!, 1, 50).then((r) => r.data),
    enabled: !!expandedOrgId,
  })

  const actionMutation = useMutation({
    mutationFn: ({ action, orgId, reason }: { action: ActionType; orgId: string; reason: string }) => {
      if (action === 'suspend') return adminApi.suspendOrg(orgId, reason)
      if (action === 'restore') return adminApi.restoreOrg(orgId, reason)
      if (action === 'archive') return adminApi.archiveOrg(orgId, reason)
      return Promise.reject(new Error('Unknown action'))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-orgs'] })
      setDialog({ action: null, org: null, reason: '' })
    },
  })

  const resetMfaMutation = useMutation({
    mutationFn: (userId: string) => adminApi.resetUserMfa(userId).then((r) => r.data),
    onSuccess: (payload, userId) => {
      queryClient.invalidateQueries({ queryKey: ['admin-org-users', expandedOrgId] })
      const targetUser = expandedUsers?.items.find((u) => u.id === userId)
      const userLabel = targetUser?.email ?? 'Selected user'
      setUserFeedback({
        level: 'success',
        message: `MFA reset completed for ${userLabel}. Revoked passkeys: ${payload.revoked_passkeys}.`,
      })
    },
    onError: (error) => {
      setUserFeedback({
        level: 'error',
        message: (error as Error)?.message ?? 'Could not reset MFA for this user.',
      })
    },
  })

  const openDialog = (action: ActionType, org: AdminOrgListItem) => {
    setDialog({ action, org, reason: '' })
  }

  const closeDialog = () => {
    setDialog({ action: null, org: null, reason: '' })
  }

  const handleConfirm = () => {
    if (!dialog.action || !dialog.org) return
    if (dialog.action !== 'restore' && !dialog.reason.trim()) return
    actionMutation.mutate({
      action: dialog.action,
      orgId: dialog.org.id,
      reason: dialog.reason.trim() || 'No reason provided',
    })
  }

  const handleResetMfa = (member: AdminUserItem) => {
    const confirmed = window.confirm(
      `Reset MFA for ${member.email}? This will revoke all registered passkeys.`
    )
    if (!confirmed) return
    setUserFeedback(null)
    resetMfaMutation.mutate(member.id)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-brand-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Workspaces</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage all organizations — suspend, restore, or archive workspaces.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-700">
            All Organizations{data ? ` (${data.total})` : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs text-gray-500">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">Loading workspaces…</div>
        ) : !data?.items.length ? (
          <div className="py-12 text-center text-sm text-gray-500">No organizations found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-5 py-3">Organization</th>
                <th className="px-4 py-3">Plan</th>
                <th className="px-4 py-3">Members</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((org) => (
                <>
                  <tr key={org.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-gray-900">{org.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{org.slug}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                        {org.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-gray-600">{org.member_quota}</td>
                    <td className="px-4 py-3.5">
                      <span
                        className={clsx(
                          'rounded-full px-2.5 py-0.5 text-xs font-semibold',
                          STATE_BADGE[org.lifecycle_state] ?? 'bg-gray-100 text-gray-600'
                        )}
                      >
                        {org.lifecycle_state}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-gray-500">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() =>
                            setExpandedOrgId(expandedOrgId === org.id ? null : org.id)
                          }
                          title="View users"
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        >
                          <Users className="h-4 w-4" />
                        </button>
                        {org.lifecycle_state !== 'archived' && (
                          <>
                            {org.lifecycle_state === 'active' ? (
                              <button
                                onClick={() => openDialog('suspend', org)}
                                title="Suspend workspace"
                                className="rounded p-1.5 text-gray-400 hover:bg-yellow-50 hover:text-yellow-600"
                              >
                                <Ban className="h-4 w-4" />
                              </button>
                            ) : (
                              <button
                                onClick={() => openDialog('restore', org)}
                                title="Restore workspace"
                                className="rounded p-1.5 text-gray-400 hover:bg-green-50 hover:text-green-600"
                              >
                                <RefreshCw className="h-4 w-4" />
                              </button>
                            )}
                            <button
                              onClick={() => openDialog('archive', org)}
                              title="Archive workspace (irreversible)"
                              className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
                            >
                              <Archive className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedOrgId === org.id && (
                    <tr key={`${org.id}-users`}>
                      <td colSpan={6} className="bg-gray-50 px-8 py-4">
                        {usersLoading ? (
                          <p className="text-xs text-gray-400">Loading users…</p>
                        ) : !expandedUsers?.items.length ? (
                          <p className="text-xs text-gray-500">No users in this workspace.</p>
                        ) : (
                          <div className="space-y-1">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                              Users ({expandedUsers.total})
                            </p>
                            {userFeedback && (
                              <div
                                className={clsx(
                                  'mb-2 rounded border px-3 py-2 text-xs',
                                  userFeedback.level === 'success'
                                    ? 'border-green-200 bg-green-50 text-green-700'
                                    : 'border-red-200 bg-red-50 text-red-700'
                                )}
                              >
                                {userFeedback.message}
                              </div>
                            )}
                            {expandedUsers.items.map((u) => (
                              <div
                                key={u.id}
                                className="flex items-center justify-between rounded border border-gray-100 bg-white px-3 py-2"
                              >
                                <div>
                                  <span className="text-sm font-medium text-gray-800">
                                    {u.full_name}
                                  </span>
                                  <span className="ml-2 text-xs text-gray-500">{u.email}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                                    {u.role}
                                  </span>
                                  {!u.is_active && (
                                    <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-600">
                                      inactive
                                    </span>
                                  )}
                                  <button
                                    onClick={() => handleResetMfa(u)}
                                    disabled={resetMfaMutation.isPending}
                                    title="Reset MFA / Passkeys"
                                    className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-60"
                                  >
                                    <KeyRound className="h-3.5 w-3.5" />
                                    {resetMfaMutation.isPending && resetMfaMutation.variables === u.id
                                      ? 'Resetting...'
                                      : 'Reset MFA'}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Action confirmation dialog */}
      {dialog.action && dialog.org && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={(e) => e.target === e.currentTarget && closeDialog()}
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-gray-900 mb-1">
              {dialog.action === 'suspend' && 'Suspend Workspace'}
              {dialog.action === 'restore' && 'Restore Workspace'}
              {dialog.action === 'archive' && 'Archive Workspace'}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              <span className="font-medium text-gray-800">{dialog.org.name}</span>
              {dialog.action === 'archive' && (
                <span className="ml-1 text-red-600 font-semibold">
                  — this action is irreversible.
                </span>
              )}
            </p>

            {dialog.action !== 'restore' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={dialog.reason}
                  onChange={(e) => setDialog({ ...dialog, reason: e.target.value })}
                  rows={3}
                  placeholder="Describe the reason for this action…"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            )}

            {dialog.action === 'restore' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason (optional)
                </label>
                <textarea
                  value={dialog.reason}
                  onChange={(e) => setDialog({ ...dialog, reason: e.target.value })}
                  rows={2}
                  placeholder="Describe the reason for restoring…"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            )}

            {actionMutation.isError && (
              <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                {(actionMutation.error as Error)?.message ?? 'Action failed. Please try again.'}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={closeDialog}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={
                  actionMutation.isPending ||
                  (dialog.action !== 'restore' && !dialog.reason.trim())
                }
                className={clsx(
                  'rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 transition-colors',
                  dialog.action === 'archive'
                    ? 'bg-red-600 hover:bg-red-700'
                    : dialog.action === 'suspend'
                      ? 'bg-yellow-500 hover:bg-yellow-600'
                      : 'bg-green-600 hover:bg-green-700'
                )}
              >
                {actionMutation.isPending
                  ? 'Processing…'
                  : dialog.action === 'suspend'
                    ? 'Suspend'
                    : dialog.action === 'restore'
                      ? 'Restore'
                      : 'Archive'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
