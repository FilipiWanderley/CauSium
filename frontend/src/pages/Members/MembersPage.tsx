import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import clsx from 'clsx'
import { membersApi, type MemberCreatePayload, type MemberItem } from '../../api/members'
import { invitesApi, type InviteOut, type InviteRole, type InviteStatus } from '../../api/invites'
import { adminApi } from '../../api/admin'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
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

type DeactivateModalState = { member: MemberItem; reason: string }
type EditModalState = { member: MemberItem; full_name: string; role: UserRole }
type DeleteModalState = { member: MemberItem; reason: string }

export function MembersPage() {
  const { user } = useAuth()
  const { t } = useI18n()
  const m = t.members
  const queryClient = useQueryClient()

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
      showError(`Copy failed. Link: ${link}`)
    }
  }

  // Helper: render invite status label from translation keys
  const inviteStatusLabel = (status: 'all' | InviteStatus): string => {
    if (status === 'all') return 'all'
    if (status === 'pending') return m.statusPending
    if (status === 'accepted') return m.statusAccepted
    if (status === 'expired') return m.statusExpired
    return m.statusRevoked
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{m.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{m.subtitle}</p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTab('members')}
            disabled={hasMemberMutationInFlight || hasInviteMutationInFlight}
            className={clsx(
              'rounded-lg px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50',
              tab === 'members' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            )}
          >
            {m.tabMembers}
          </button>
          <button
            onClick={() => setTab('invites')}
            disabled={hasMemberMutationInFlight || hasInviteMutationInFlight}
            className={clsx(
              'rounded-lg px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50',
              tab === 'invites' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            )}
          >
            {m.tabInvites}
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={clsx(
            'rounded px-3 py-2 text-sm',
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
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">{m.createMember}</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <input
                type="email"
                value={memberForm.email}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder={m.emailPlaceholder}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <input
                type="text"
                value={memberForm.full_name}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, full_name: e.target.value }))}
                placeholder={m.fullNamePlaceholder}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <input
                type="password"
                value={memberForm.password}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, password: e.target.value }))}
                placeholder={m.tempPasswordPlaceholder}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <select
                value={memberForm.role}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, role: e.target.value as UserRole }))}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </div>
            <div className="mt-3">
              <button
                onClick={() => createMemberMutation.mutate()}
                disabled={!canCreateMember || hasMemberMutationInFlight}
                className="rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {createMemberMutation.isPending ? m.creating : m.createMember}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-900">
                {m.workspaceMembers.replace('{{count}}', String(allMembers.length))}
              </h2>
              {totalMemberPages > 1 && (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <button
                    onClick={() => setMembersPage((p) => Math.max(1, p - 1))}
                    disabled={membersPage <= 1 || hasMemberMutationInFlight}
                    className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {m.prev}
                  </button>
                  <span>
                    {m.pageOf
                      .replace('{{page}}', String(membersPage))
                      .replace('{{total}}', String(totalMemberPages))}
                  </span>
                  <button
                    onClick={() => setMembersPage((p) => Math.min(totalMemberPages, p + 1))}
                    disabled={membersPage >= totalMemberPages || hasMemberMutationInFlight}
                    className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {m.next}
                  </button>
                </div>
              )}
            </div>
            {membersQuery.isLoading ? (
              <div className="text-sm text-gray-500">{m.loadingMembers}</div>
            ) : !allMembers.length ? (
              <div className="text-sm text-gray-500">{m.noMembers}</div>
            ) : (
              <div className="space-y-2">
                {members.map((member) => (
                  <div key={member.id} className="flex items-center justify-between rounded border border-gray-200 px-3 py-2">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{member.full_name}</div>
                      <div className="text-xs text-gray-500">
                        {member.email} · {member.role} · {member.is_active ? 'active' : 'inactive'}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => resetMfaMutation.mutate(member)}
                        disabled={hasMemberMutationInFlight}
                        className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      >
                        {resetMfaMutation.isPending && memberActionId === member.id ? m.resettingMfa : m.resetMfa}
                      </button>
                      <button
                        onClick={() => resetPasswordMutation.mutate(member)}
                        disabled={hasMemberMutationInFlight}
                        className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      >
                        {resetPasswordMutation.isPending && memberActionId === member.id ? m.resettingPassword : m.resetPassword}
                      </button>
                      <button
                        onClick={() => handleDeactivate(member)}
                        disabled={!member.is_active || hasMemberMutationInFlight}
                        className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        {deactivateMutation.isPending && memberActionId === member.id ? m.deactivating : m.deactivate}
                      </button>
                      <button
                        onClick={() => handleEdit(member)}
                        disabled={!member.is_active || hasMemberMutationInFlight}
                        className="rounded border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-60"
                      >
                        {editMemberMutation.isPending && memberActionId === member.id ? m.saving : m.edit}
                      </button>
                      <button
                        onClick={() => handleDelete(member)}
                        disabled={hasMemberMutationInFlight}
                        className="rounded border border-red-400 px-2 py-1 text-xs font-medium text-red-900 hover:bg-red-100 disabled:opacity-60"
                      >
                        {deleteMemberMutation.isPending && memberActionId === member.id ? m.removing : m.remove}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'invites' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">{m.createInvite}</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder={m.emailPlaceholder}
                pattern="[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
                required
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, role: e.target.value as InviteRole }))}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
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
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                <option value={3}>{m.days3}</option>
                <option value={7}>{m.days7}</option>
                <option value={14}>{m.days14}</option>
                <option value={30}>{m.days30}</option>
              </select>
              <button
                onClick={() => createInviteMutation.mutate()}
                disabled={!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(inviteForm.email.trim()) || hasInviteMutationInFlight}
                className="rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {createInviteMutation.isPending ? m.creating : m.createInvite}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="mb-3 grid grid-cols-1 md:grid-cols-3 gap-2">
              <input
                type="text"
                value={inviteQuery}
                disabled={hasInviteMutationInFlight}
                onChange={(e) => {
                  setInviteQuery(e.target.value)
                  setInvitePage(1)
                }}
                placeholder={m.searchInvite}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <select
                value={inviteStatusFilter}
                disabled={hasInviteMutationInFlight}
                onChange={(e) => {
                  setInviteStatusFilter(e.target.value as 'all' | InviteStatus)
                  setInvitePage(1)
                }}
                className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                {INVITE_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {inviteStatusLabel(status)}
                  </option>
                ))}
              </select>
              <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                <button
                  onClick={() => setInvitePage((p) => Math.max(1, p - 1))}
                  disabled={invitePage <= 1 || hasInviteMutationInFlight}
                  className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {m.prev}
                </button>
                <span>
                  {m.pageOf
                    .replace('{{page}}', String(invitePage))
                    .replace('{{total}}', String(totalInvitePages))}
                </span>
                <button
                  onClick={() => setInvitePage((p) => Math.min(totalInvitePages, p + 1))}
                  disabled={invitePage >= totalInvitePages || hasInviteMutationInFlight}
                  className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {m.next}
                </button>
              </div>
            </div>

            {!invites.length ? (
              <div className="text-sm text-gray-500">{m.noInvites}</div>
            ) : (
              <div className="space-y-2">
                {invites.map((invite) => (
                  <div key={invite.id} className="flex items-center justify-between rounded border border-gray-200 px-3 py-2">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{invite.invited_email}</div>
                      <div className="text-xs text-gray-500">
                        {invite.role} · {invite.status} · expires {new Date(invite.expires_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => copyInviteLink(invite)}
                        disabled={hasInviteMutationInFlight}
                        className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      >
                        {m.copyLink}
                      </button>
                      <button
                        onClick={() => revokeInviteMutation.mutate(invite)}
                        disabled={invite.status !== 'pending' || hasInviteMutationInFlight}
                        className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        {revokeInviteMutation.isPending && inviteActionId === invite.id ? m.revoking : m.revoke}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
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
