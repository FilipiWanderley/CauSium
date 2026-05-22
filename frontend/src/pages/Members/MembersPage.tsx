import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import clsx from 'clsx'
import { membersApi, type MemberCreatePayload, type MemberItem } from '../../api/members'
import { invitesApi, type InviteOut, type InviteRole, type InviteStatus } from '../../api/invites'
import { adminApi } from '../../api/admin'
import { useAuth } from '../../hooks/useAuth'
import { usePageTitle } from '../../hooks/usePageTitle'
import { useI18n } from '../../contexts/I18nContext'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonTable } from '../../components/UX/Skeleton'
import type { UserRole } from '../../types'

type MembersTab = 'members' | 'invites'
type FeedbackTone = 'success' | 'error' | 'info'

const ROLES: UserRole[] = ['viewer', 'executive', 'finops', 'engineer', 'admin']

const INVITE_STATUS_OPTIONS: Array<'all' | InviteStatus> = [
  'all',
  'pending',
  'accepted',
  'expired',
  'revoked',
]

const INVITES_PAGE_SIZE = 10
const MEMBERS_PAGE_SIZE = 10

const ACTION_BUTTON_BASE =
  'rounded-md px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-60 disabled:cursor-not-allowed'
const ACTION_BUTTON_SECONDARY =
  `${ACTION_BUTTON_BASE} text-gray-500 hover:bg-gray-50 hover:text-gray-700`
const ACTION_BUTTON_PRIMARY =
  `${ACTION_BUTTON_BASE} border border-gray-300 bg-white text-gray-700 hover:bg-gray-50`
const ACTION_BUTTON_WARNING =
  `${ACTION_BUTTON_BASE} border border-amber-200 bg-amber-50/70 text-amber-700 hover:bg-amber-100/80`
const ACTION_BUTTON_DANGER =
  `${ACTION_BUTTON_BASE} text-red-600 hover:bg-red-50`

type DeactivateModalState = { member: MemberItem; reason: string }
type EditModalState = { member: MemberItem; full_name: string; role: UserRole }
type DeleteModalState = { member: MemberItem; reason: string }

export function MembersPage() {
  const { user } = useAuth()
  const { t, lang } = useI18n()
  usePageTitle('Members')
  const m = t.members
  const queryClient = useQueryClient()
  const locale = lang === 'pt' ? 'pt-BR' : 'en-US'

  const [tab, setTab] = useState<MembersTab>('members')
  const [feedback, setFeedback] = useState<{ tone: FeedbackTone; message: string } | null>(null)
  const [memberActionId, setMemberActionId] = useState<string | null>(null)
  const [inviteActionId, setInviteActionId] = useState<string | null>(null)
  const [membersPage, setMembersPage] = useState(1)

  const [memberForm, setMemberForm] = useState<MemberCreatePayload>({
    email: '',
    full_name: '',
    password: '',
    role: 'viewer',
  })

  const [tempPasswordModal, setTempPasswordModal] = useState<{ email: string; password: string } | null>(null)
  const [deactivateModal, setDeactivateModal] = useState<DeactivateModalState | null>(null)
  const [editModal, setEditModal] = useState<EditModalState | null>(null)
  const [deleteModal, setDeleteModal] = useState<DeleteModalState | null>(null)

  const [inviteForm, setInviteForm] = useState({
    email: '',
    role: 'viewer' as InviteRole,
    expiresInDays: 7,
  })
  const [inviteQuery, setInviteQuery] = useState('')
  const [inviteStatusFilter, setInviteStatusFilter] = useState<'all' | InviteStatus>('all')
  const [invitePage, setInvitePage] = useState(1)

  const isAdmin = user?.role === 'admin' || user?.role === 'platform_admin'
  if (!isAdmin) return <Navigate to="/app/dashboard" replace />

  const showSuccess = (message: string) => setFeedback({ tone: 'success', message })
  const showError = (message: string) => setFeedback({ tone: 'error', message })

  const membersQuery = useQuery<MemberItem[]>({
    queryKey: ['members-list'],
    queryFn: () => membersApi.list().then((r) => r.data.items),
  })

  const invitesQuery = useQuery({
    queryKey: ['members-invites', invitePage, inviteStatusFilter, inviteQuery],
    queryFn: () =>
      invitesApi
        .list(invitePage, INVITES_PAGE_SIZE, {
          status: inviteStatusFilter === 'all' ? undefined : inviteStatusFilter,
          q: inviteQuery || undefined,
        })
        .then((r) => r.data),
    enabled: tab === 'invites',
  })

  const createMemberMutation = useMutation({
    mutationFn: () =>
      membersApi.create({
        ...memberForm,
        email: memberForm.email.trim().toLowerCase(),
        full_name: memberForm.full_name.trim(),
      }),
    onMutate: () => {
      setFeedback(null)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['members-list'] })
      setMemberForm({ email: '', full_name: '', password: '', role: 'viewer' })
      showSuccess(m.toastCreated)
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastCreateError)
    },
  })

  const resetPasswordMutation = useMutation({
    mutationFn: (member: MemberItem) => adminApi.resetUserPassword(member.id).then((r) => ({ member, payload: r.data })),
    onMutate: (member) => {
      setMemberActionId(member.id)
      setFeedback(null)
    },
    onSuccess: ({ member, payload }) => {
      setTempPasswordModal({
        email: member.email,
        password: payload.temporary_password,
      })
      showSuccess(m.toastPasswordReset.replace('{{email}}', member.email))
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastPasswordError)
    },
    onSettled: () => {
      setMemberActionId(null)
    },
  })

  const resetMfaMutation = useMutation({
    mutationFn: (member: MemberItem) => adminApi.resetUserMfa(member.id).then((r) => ({ member, payload: r.data })),
    onMutate: (member) => {
      setMemberActionId(member.id)
      setFeedback(null)
    },
    onSuccess: ({ member, payload }) => {
      showSuccess(
        m.toastMfaReset
          .replace('{{email}}', member.email)
          .replace('{{count}}', String(payload.revoked_passkeys))
      )
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastMfaError)
    },
    onSettled: () => {
      setMemberActionId(null)
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: ({ member, reason }: { member: MemberItem; reason: string }) =>
      adminApi.deactivateUser(member.id, reason).then((r) => ({ member, payload: r.data })),
    onMutate: ({ member }) => {
      setMemberActionId(member.id)
      setFeedback(null)
    },
    onSuccess: async ({ member }) => {
      await queryClient.invalidateQueries({ queryKey: ['members-list'] })
      showSuccess(m.toastDeactivated.replace('{{email}}', member.email))
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastDeactivateError)
    },
    onSettled: () => {
      setMemberActionId(null)
    },
  })

  // --- PATCH membro ---
  const editMemberMutation = useMutation({
    mutationFn: ({ member, updates }: { member: MemberItem; updates: Partial<Pick<MemberItem, 'full_name' | 'email' | 'role'>> }) =>
      membersApi.update(member.id, updates).then((r) => ({ member, payload: r.data })),
    onMutate: ({ member }) => {
      setMemberActionId(member.id)
      setFeedback(null)
    },
    onSuccess: async ({ member }) => {
      await queryClient.invalidateQueries({ queryKey: ['members-list'] })
      showSuccess(m.toastUpdated.replace('{{email}}', member.email))
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastUpdateError)
    },
    onSettled: () => {
      setMemberActionId(null)
    },
  })

  // --- DELETE membro (soft) ---
  const deleteMemberMutation = useMutation({
    mutationFn: ({ member, reason }: { member: MemberItem; reason: string }) =>
      membersApi.delete(member.id, reason).then((r) => ({ member, payload: r.data })),
    onMutate: ({ member }) => {
      setMemberActionId(member.id)
      setFeedback(null)
    },
    onSuccess: async ({ member }) => {
      await queryClient.invalidateQueries({ queryKey: ['members-list'] })
      showSuccess(m.toastRemoved.replace('{{email}}', member.email))
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastRemoveError)
    },
    onSettled: () => {
      setMemberActionId(null)
    },
  })

  const createInviteMutation = useMutation({
    mutationFn: () =>
      invitesApi.create({
        email: inviteForm.email.trim().toLowerCase(),
        role: inviteForm.role,
        expires_in_days: inviteForm.expiresInDays,
      }),
    onMutate: () => {
      setFeedback(null)
    },
    onSuccess: async ({ data }) => {
      await queryClient.invalidateQueries({ queryKey: ['members-invites'] })
      setInviteForm({ email: '', role: 'viewer', expiresInDays: 7 })
      const link = `${window.location.origin}/activate?token=${data.token}`
      showSuccess(
        m.toastInviteCreated
          .replace('{{email}}', data.invited_email)
          .replace('{{link}}', link)
      )
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastInviteError)
    },
  })

  const revokeInviteMutation = useMutation({
    mutationFn: (invite: InviteOut) => invitesApi.revoke(invite.id).then(() => invite),
    onMutate: (invite) => {
      setInviteActionId(invite.id)
      setFeedback(null)
    },
    onSuccess: async (invite) => {
      await queryClient.invalidateQueries({ queryKey: ['members-invites'] })
      showSuccess(m.toastInviteRevoked.replace('{{email}}', invite.invited_email))
    },
    onError: (error) => {
      showError((error as Error)?.message ?? m.toastInviteRevokeError)
    },
    onSettled: () => {
      setInviteActionId(null)
    },
  })

  const allMembers = membersQuery.data ?? []
  const totalMemberPages = Math.max(1, Math.ceil(allMembers.length / MEMBERS_PAGE_SIZE))
  const members = allMembers.slice((membersPage - 1) * MEMBERS_PAGE_SIZE, membersPage * MEMBERS_PAGE_SIZE)
  const invites = invitesQuery.data?.items ?? []
  const totalInvitePages = invitesQuery.data
    ? Math.max(1, Math.ceil(invitesQuery.data.total / invitesQuery.data.page_size))
    : 1

  const canCreateMember = useMemo(() => {
    return (
      memberForm.email.trim().length > 0 &&
      memberForm.full_name.trim().length >= 2 &&
      memberForm.password.length >= 8
    )
  }, [memberForm])
  const hasMemberMutationInFlight =
    createMemberMutation.isPending ||
    resetPasswordMutation.isPending ||
    resetMfaMutation.isPending ||
    deactivateMutation.isPending
  const hasInviteMutationInFlight = createInviteMutation.isPending || revokeInviteMutation.isPending

  const handleDeactivate = (member: MemberItem) => {
    if (!member.is_active) return
    setDeactivateModal({ member, reason: 'Member offboarding' })
  }

  const handleEdit = (member: MemberItem) => {
    setEditModal({ member, full_name: member.full_name, role: member.role })
  }

  const handleDelete = (member: MemberItem) => {
    setDeleteModal({ member, reason: 'Member offboarding' })
  }

  const copyInviteLink = async (invite: InviteOut) => {
    const link = `${window.location.origin}/activate?token=${invite.token}`
    try {
      await navigator.clipboard.writeText(link)
      showSuccess(m.toastInviteCreated.replace('{{email}}', invite.invited_email).replace('{{link}}', link))
    } catch {
      showError(`Could not copy invite link. Link: ${link}`)
    }
  }

  // Helper: render invite status label from translation keys
  const inviteStatusLabel = (status: 'all' | InviteStatus): string => {
    if (status === 'all') return t.common.all
    if (status === 'pending') return m.statusPending
    if (status === 'accepted') return m.statusAccepted
    if (status === 'expired') return m.statusExpired
    return m.statusRevoked
  }

  const formatDateTime = (value: string) => new Date(value).toLocaleString(locale)

  return (
    <div className="page-container max-w-6xl">
      <PageHeader
        title={m.title}
        subtitle={m.subtitle}
        meta={
          <>
            <span>Workspace administration</span>
            <span>Identity & access controls</span>
          </>
        }
      />

      <Panel compact>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTab('members')}
            disabled={hasMemberMutationInFlight || hasInviteMutationInFlight}
            className={clsx(
              'rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
              tab === 'members' ? 'bg-brand-600 text-white shadow-sm' : 'text-gray-700 hover:bg-gray-50'
            )}
          >
            {m.tabMembers}
          </button>
          <button
            onClick={() => setTab('invites')}
            disabled={hasMemberMutationInFlight || hasInviteMutationInFlight}
            className={clsx(
              'rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
              tab === 'invites' ? 'bg-brand-600 text-white shadow-sm' : 'text-gray-700 hover:bg-gray-50'
            )}
          >
            {m.tabInvites}
          </button>
        </div>
      </Panel>

      {feedback && (
        <div
          className={clsx(
            'rounded-xl border px-4 py-3 text-sm',
            feedback.tone === 'success' && 'border border-green-200 bg-green-50 text-green-700',
            feedback.tone === 'error' && 'border border-red-200 bg-red-50 text-red-700',
            feedback.tone === 'info' && 'border border-blue-200 bg-blue-50 text-blue-700'
          )}
        >
          {feedback.message}
        </div>
      )}

      {tab === 'members' && (
        <div className="space-y-4">
          <Panel>
            <PanelHeader
              title={m.createMember}
              subtitle="Provision a workspace member and assign an initial role from the same command surface."
            />
            <div className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <input
                  type="email"
                  value={memberForm.email}
                  onChange={(e) => setMemberForm((prev) => ({ ...prev, email: e.target.value }))}
                  placeholder={m.emailPlaceholder}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                />
                <input
                  type="text"
                  value={memberForm.full_name}
                  onChange={(e) => setMemberForm((prev) => ({ ...prev, full_name: e.target.value }))}
                  placeholder={m.fullNamePlaceholder}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                />
                <input
                  type="password"
                  value={memberForm.password}
                  onChange={(e) => setMemberForm((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder={m.tempPasswordPlaceholder}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                />
                <select
                  value={memberForm.role}
                  onChange={(e) => setMemberForm((prev) => ({ ...prev, role: e.target.value as UserRole }))}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-4">
                <button
                  onClick={() => createMemberMutation.mutate()}
                  disabled={!canCreateMember || hasMemberMutationInFlight}
                  className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
                >
                  {createMemberMutation.isPending ? m.creating : m.createMember}
                </button>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title={m.workspaceMembers.replace('{{count}}', String(allMembers.length))}
              subtitle="Review current workspace access and manage account-level member actions."
              actions={
                totalMemberPages > 1 ? (
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <button
                      onClick={() => setMembersPage((p) => Math.max(1, p - 1))}
                      disabled={membersPage <= 1 || hasMemberMutationInFlight}
                      className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {m.prev}
                    </button>
                    <span className="text-xs text-gray-500">
                      {m.pageOf
                        .replace('{{page}}', String(membersPage))
                        .replace('{{total}}', String(totalMemberPages))}
                    </span>
                    <button
                      onClick={() => setMembersPage((p) => Math.min(totalMemberPages, p + 1))}
                      disabled={membersPage >= totalMemberPages || hasMemberMutationInFlight}
                      className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {m.next}
                    </button>
                  </div>
                ) : undefined
              }
            />
            <div className="mt-4">
              {membersQuery.isLoading ? (
                <SkeletonTable rows={6} columns={5} />
              ) : membersQuery.isError ? (
                <ErrorState
                  title="Could not load members"
                  description="Workspace members are currently unavailable. Please try again."
                  onRetry={() => membersQuery.refetch()}
                  retryLabel="Retry"
                />
              ) : !allMembers.length ? (
                <EmptyState
                  icon="document"
                  title={m.noMembers}
                  description="Create the first workspace member to start delegating access and ownership."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left">
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{t.common.name}</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Email</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{t.common.role}</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Status</th>
                        <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {members.map((member) => (
                        <tr key={member.id} className="transition hover:bg-gray-50/50">
                          <td className="py-3 pr-4 font-medium text-gray-900">{member.full_name}</td>
                          <td className="py-3 pr-4 text-gray-700">{member.email}</td>
                          <td className="py-3 pr-4">
                            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                              {member.role}
                            </span>
                          </td>
                          <td className="py-3 pr-4">
                            <span
                              className={clsx(
                                'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                                member.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'
                              )}
                            >
                              {member.is_active ? 'active' : 'inactive'}
                            </span>
                          </td>
                          <td className="py-3">
                            <div className="flex flex-wrap items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleEdit(member)}
                                disabled={!member.is_active || hasMemberMutationInFlight}
                                className={ACTION_BUTTON_PRIMARY}
                              >
                                {editMemberMutation.isPending && memberActionId === member.id ? m.saving : m.edit}
                              </button>
                              <button
                                onClick={() => resetMfaMutation.mutate(member)}
                                disabled={hasMemberMutationInFlight}
                                className={ACTION_BUTTON_SECONDARY}
                              >
                                {resetMfaMutation.isPending && memberActionId === member.id ? m.resettingMfa : m.resetMfa}
                              </button>
                              <button
                                onClick={() => resetPasswordMutation.mutate(member)}
                                disabled={hasMemberMutationInFlight}
                                className={ACTION_BUTTON_SECONDARY}
                              >
                                {resetPasswordMutation.isPending && memberActionId === member.id ? m.resettingPassword : m.resetPassword}
                              </button>
                              <span className="hidden h-5 w-px bg-gray-200 md:block" aria-hidden="true" />
                              <button
                                onClick={() => handleDeactivate(member)}
                                disabled={!member.is_active || hasMemberMutationInFlight}
                                className={ACTION_BUTTON_WARNING}
                              >
                                {deactivateMutation.isPending && memberActionId === member.id ? m.deactivating : m.deactivate}
                              </button>
                              <button
                                onClick={() => handleDelete(member)}
                                disabled={hasMemberMutationInFlight}
                                className={ACTION_BUTTON_DANGER}
                              >
                                {deleteMemberMutation.isPending && memberActionId === member.id ? m.removing : m.remove}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Panel>
        </div>
      )}

      {tab === 'invites' && (
        <div className="space-y-4">
          <Panel>
            <PanelHeader
              title={m.createInvite}
              subtitle="Create a role-scoped invite without leaving the access management surface."
            />
            <div className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder={m.emailPlaceholder}
                pattern="[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
                required
                className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, role: e.target.value as InviteRole }))}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
              <select
                value={inviteForm.expiresInDays}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, expiresInDays: Number(e.target.value) }))}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value={3}>{m.days3}</option>
                <option value={7}>{m.days7}</option>
                <option value={14}>{m.days14}</option>
                <option value={30}>{m.days30}</option>
              </select>
              <button
                onClick={() => createInviteMutation.mutate()}
                disabled={!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(inviteForm.email.trim()) || hasInviteMutationInFlight}
                className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
              >
                {createInviteMutation.isPending ? m.creating : m.createInvite}
              </button>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title="Invite inventory"
              subtitle="Search pending and historical invites while keeping the same table behavior."
            />
            <div className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  type="text"
                  value={inviteQuery}
                  disabled={hasInviteMutationInFlight}
                  onChange={(e) => {
                    setInviteQuery(e.target.value)
                    setInvitePage(1)
                  }}
                  placeholder={m.searchInvite}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                />
                <select
                  value={inviteStatusFilter}
                  disabled={hasInviteMutationInFlight}
                  onChange={(e) => {
                    setInviteStatusFilter(e.target.value as 'all' | InviteStatus)
                    setInvitePage(1)
                  }}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                >
                  {INVITE_STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {inviteStatusLabel(status)}
                    </option>
                  ))}
                </select>
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => setInvitePage((p) => Math.max(1, p - 1))}
                    disabled={invitePage <= 1 || hasInviteMutationInFlight}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {m.prev}
                  </button>
                  <span className="text-xs text-gray-500">
                    {m.pageOf
                      .replace('{{page}}', String(invitePage))
                      .replace('{{total}}', String(totalInvitePages))}
                  </span>
                  <button
                    onClick={() => setInvitePage((p) => Math.min(totalInvitePages, p + 1))}
                    disabled={invitePage >= totalInvitePages || hasInviteMutationInFlight}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {m.next}
                  </button>
                </div>
              </div>
            </div>
            <div className="mt-4">
              {invitesQuery.isLoading ? (
                <SkeletonTable rows={6} columns={5} />
              ) : invitesQuery.isError ? (
                <ErrorState
                  title="Could not load invites"
                  description="Workspace invites are currently unavailable. Please try again."
                  onRetry={() => invitesQuery.refetch()}
                  retryLabel="Retry"
                />
              ) : !invites.length ? (
                <EmptyState
                  icon="document"
                  title={m.noInvites}
                  description={
                    inviteQuery || inviteStatusFilter !== 'all'
                      ? 'No invites match the current filters.'
                      : 'Create an invite to onboard another workspace member.'
                  }
                  action={
                    inviteQuery || inviteStatusFilter !== 'all'
                      ? {
                          label: 'Clear filters',
                          onClick: () => {
                            setInviteQuery('')
                            setInviteStatusFilter('all')
                            setInvitePage(1)
                          },
                        }
                      : undefined
                  }
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left">
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Email</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{t.common.role}</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Status</th>
                        <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Expires</th>
                        <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {invites.map((invite) => (
                        <tr key={invite.id} className="transition hover:bg-gray-50/50">
                          <td className="py-3 pr-4 font-medium text-gray-900">{invite.invited_email}</td>
                          <td className="py-3 pr-4">
                            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                              {invite.role}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-gray-700">{inviteStatusLabel(invite.status)}</td>
                          <td className="py-3 pr-4 text-gray-700">{formatDateTime(invite.expires_at)}</td>
                          <td className="py-3">
                            <div className="flex flex-wrap items-center justify-end gap-1.5">
                              <button
                                onClick={() => copyInviteLink(invite)}
                                disabled={hasInviteMutationInFlight}
                                className={ACTION_BUTTON_PRIMARY}
                              >
                                {m.copyLink}
                              </button>
                              <button
                                onClick={() => revokeInviteMutation.mutate(invite)}
                                disabled={invite.status !== 'pending' || hasInviteMutationInFlight}
                                className={ACTION_BUTTON_DANGER}
                              >
                                {revokeInviteMutation.isPending && inviteActionId === invite.id ? m.revoking : m.revoke}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Panel>
        </div>
      )}

      {tempPasswordModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={(e) => e.target === e.currentTarget && setTempPasswordModal(null)}
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-gray-900 mb-2">{m.tempPasswordTitle}</h3>
            <p className="text-sm text-gray-500 mb-3">
              {m.tempPasswordUser.replace('{{email}}', tempPasswordModal.email)}
            </p>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 mb-3">
              {m.tempPasswordNote}
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="font-mono text-sm text-gray-800 break-all flex-1">{tempPasswordModal.password}</span>
              <button
                onClick={() => navigator.clipboard.writeText(tempPasswordModal.password)}
                className="text-xs text-brand-600 hover:underline shrink-0"
              >
                {m.copy}
              </button>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setTempPasswordModal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                {m.close}
              </button>
            </div>
          </div>
        </div>
      )}

      {deactivateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-gray-900 mb-1">{m.deactivateTitle}</h3>
            <p className="text-sm text-gray-500 mb-4">
              {m.deactivateDesc.replace('{{email}}', deactivateModal.member.email)}
            </p>
            <label className="block text-xs font-medium text-gray-700 mb-1">{m.reason}</label>
            <input
              type="text"
              value={deactivateModal.reason}
              onChange={(e) => setDeactivateModal((s) => s && { ...s, reason: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeactivateModal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                {m.cancel}
              </button>
              <button
                disabled={deactivateModal.reason.trim().length < 3 || hasMemberMutationInFlight}
                onClick={() => {
                  deactivateMutation.mutate(
                    { member: deactivateModal.member, reason: deactivateModal.reason.trim() },
                    { onSettled: () => setDeactivateModal(null) }
                  )
                }}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
              >
                {deactivateMutation.isPending ? m.deactivating : m.confirmDeactivate}
              </button>
            </div>
          </div>
        </div>
      )}

      {editModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-gray-900 mb-4">{m.editMember}</h3>
            <label className="block text-xs font-medium text-gray-700 mb-1">{m.fullName}</label>
            <input
              type="text"
              value={editModal.full_name}
              onChange={(e) => setEditModal((s) => s && { ...s, full_name: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none mb-3"
            />
            <label className="block text-xs font-medium text-gray-700 mb-1">{m.role}</label>
            <select
              value={editModal.role}
              onChange={(e) => setEditModal((s) => s && { ...s, role: e.target.value as UserRole })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none mb-4"
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditModal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                {m.cancel}
              </button>
              <button
                disabled={editModal.full_name.trim().length < 2 || hasMemberMutationInFlight}
                onClick={() => {
                  editMemberMutation.mutate(
                    { member: editModal.member, updates: { full_name: editModal.full_name.trim(), role: editModal.role } },
                    { onSettled: () => setEditModal(null) }
                  )
                }}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {editMemberMutation.isPending ? m.saving : m.save}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-gray-900 mb-1">{m.removeTitle}</h3>
            <p className="text-sm text-gray-500 mb-4">
              {m.removeDesc.replace('{{email}}', deleteModal.member.email)}
            </p>
            <label className="block text-xs font-medium text-gray-700 mb-1">{m.reason}</label>
            <input
              type="text"
              value={deleteModal.reason}
              onChange={(e) => setDeleteModal((s) => s && { ...s, reason: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteModal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                {m.cancel}
              </button>
              <button
                disabled={deleteModal.reason.trim().length < 3 || hasMemberMutationInFlight}
                onClick={() => {
                  deleteMemberMutation.mutate(
                    { member: deleteModal.member, reason: deleteModal.reason.trim() },
                    { onSettled: () => setDeleteModal(null) }
                  )
                }}
                className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-60"
              >
                {deleteMemberMutation.isPending ? m.removing : m.confirmRemove}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


