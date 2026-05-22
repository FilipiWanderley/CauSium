import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from 'recharts'
import type { CostTrend, ChangeEvent, ChangeEventType } from '../../types'
import { format, parseISO } from 'date-fns'
import { formatCurrency, getCurrencyLocale } from '../../utils/currency'

// ── Event type styling ────────────────────────────────────────────────────────

const EVENT_COLOR: Record<ChangeEventType, string> = {
  incident: '#ef4444',
  cost_anomaly: '#f97316',
  deploy: '#3b82f6',
  config_change: '#8b5cf6',
  scaling: '#06b6d4',
  policy_change: '#6b7280',
}

const EVENT_LABEL: Record<ChangeEventType, string> = {
  incident: 'Incident',
  cost_anomaly: 'Cost Anomaly',
  deploy: 'Deploy',
  config_change: 'Config Change',
  scaling: 'Scaling',
  policy_change: 'Policy Change',
}

// Priority order for picking the "dominant" event color on a day
const EVENT_PRIORITY: ChangeEventType[] = [
  'incident',
  'cost_anomaly',
  'scaling',
  'deploy',
  'config_change',
  'policy_change',
]

function dominantType(events: ChangeEvent[]): ChangeEventType {
  for (const t of EVENT_PRIORITY) {
    if (events.some((e) => e.event_type === t)) return t
  }
  return events[0].event_type
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

const formatMoney = (value: number, currency: string) =>
  formatCurrency(value, currency, { maximumFractionDigits: value >= 100 ? 0 : 2 })

const formatAxisValue = (value: number, currency: string) => {
  return new Intl.NumberFormat(getCurrencyLocale(currency), {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  const cost: number = point?.cost_usd ?? 0
  const events: ChangeEvent[] = point?.events ?? []
  const currency: string = point?.currency ?? 'USD'
  const previousCost: number | null = typeof point?.previous_cost_usd === 'number' ? point.previous_cost_usd : null
  const delta = previousCost == null ? null : cost - previousCost
  const deltaPct = previousCost == null || previousCost === 0 ? null : (delta! / previousCost) * 100

  return (
    <div className="min-w-[240px] rounded-xl border border-slate-200 bg-white/95 p-4 shadow-xl backdrop-blur-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Cost trend</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{point?.dateFullLabel ?? point?.dateLabel}</p>
        </div>
        {events.length > 0 && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-600">
            {events.length} event{events.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2.5">
        <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Daily cost</div>
        <div className="mt-1 text-xl font-semibold text-slate-900">{formatMoney(cost, currency)}</div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-slate-100 px-3 py-2">
          <div className="text-slate-400">Prior point</div>
          <div className="mt-1 font-semibold text-slate-700">
            {previousCost == null ? '—' : formatMoney(previousCost, currency)}
          </div>
        </div>
        <div className="rounded-lg border border-slate-100 px-3 py-2">
          <div className="text-slate-400">Delta</div>
          <div className={delta == null ? 'mt-1 font-semibold text-slate-700' : delta >= 0 ? 'mt-1 font-semibold text-rose-600' : 'mt-1 font-semibold text-emerald-600'}>
            {delta == null
              ? '—'
              : `${delta > 0 ? '+' : ''}${formatMoney(delta, currency)}${deltaPct == null ? '' : ` · ${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%`}`}
          </div>
        </div>
      </div>

      {events.length > 0 && (
        <div className="mt-3 border-t border-slate-100 pt-3 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Events on this day
          </p>
          {events.map((ev) => (
            <div key={ev.id} className="flex items-start gap-2">
              <span
                className="mt-1 h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: EVENT_COLOR[ev.event_type] }}
              />
              <div>
                <span style={{ color: EVENT_COLOR[ev.event_type] }} className="text-[11px] font-semibold">
                  {EVENT_LABEL[ev.event_type]}
                </span>
                <p className="text-xs leading-tight text-slate-600">{ev.title}</p>
                {ev.cost_impact_usd != null && (
                  <p
                    className={
                      ev.cost_impact_usd > 0 ? 'text-xs font-semibold text-rose-600' : 'text-xs font-semibold text-emerald-600'
                    }
                  >
                    {ev.cost_impact_usd > 0 ? '+' : ''}
                    {formatMoney(ev.cost_impact_usd, currency)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Custom dot — renders on days with events ──────────────────────────────────

function EventDot(props: any) {
  const { cx, cy, payload } = props
  const events: ChangeEvent[] = payload?.events ?? []
  if (!events.length) return null

  const color = EVENT_COLOR[dominantType(events)]
  const count = events.length

  return (
    <g>
      <circle cx={cx} cy={cy} r={11} fill={color} fillOpacity={0.08} />
      <circle cx={cx} cy={cy} r={7} fill="#fff" fillOpacity={0.95} />
      <circle cx={cx} cy={cy} r={4.5} fill={color} stroke="#fff" strokeWidth={1.5} />
      {count > 1 && (
        <g transform={`translate(${cx + 7}, ${cy - 10})`}>
          <circle r={7} fill="#111827" />
          <text textAnchor="middle" dominantBaseline="central" fontSize={8} fill="#fff" fontWeight={700}>
            {count}
          </text>
        </g>
      )}
    </g>
  )
}

// ── Reference lines for events with high cost impact ─────────────────────────

interface RefEvent {
  dateLabel: string
  events: ChangeEvent[]
}

function buildRefLines(refEvents: RefEvent[]) {
  return refEvents
    .filter((r) => r.events.some((e) => e.event_type === 'incident' || e.event_type === 'cost_anomaly'))
    .map((r) => {
      const dominant = dominantType(r.events)
      return (
        <ReferenceLine
          key={r.dateLabel}
          x={r.dateLabel}
          stroke={EVENT_COLOR[dominant]}
          strokeDasharray="4 3"
          strokeWidth={1.5}
          strokeOpacity={0.6}
        />
      )
    })
}

// ── Props & main component ────────────────────────────────────────────────────

interface Props {
  data: CostTrend[]
  events?: ChangeEvent[]
  height?: number
  currency?: string
}

export function CostTrendChart({ data, events = [], height = 248, currency = 'USD' }: Props) {
  // Group events by YYYY-MM-DD
  const eventsByDate: Record<string, ChangeEvent[]> = {}
  for (const ev of events) {
    const day = ev.occurred_at.slice(0, 10)
    if (!eventsByDate[day]) eventsByDate[day] = []
    eventsByDate[day].push(ev)
  }

  // Merge into trend data
  const formatted = data.map((d, index) => {
    const dateStr = (d.date as unknown as string).slice(0, 10)
    return {
      ...d,
      dateLabel: format(parseISO(dateStr), 'MMM d'),
      dateFullLabel: format(parseISO(dateStr), 'MMM d, yyyy'),
      previous_cost_usd: index > 0 ? data[index - 1].cost_usd : null,
      currency,
      events: eventsByDate[dateStr] ?? [],
    }
  })

  const refEvents = formatted.filter((f) => f.events.length > 0)
  const averageCost =
    formatted.length > 0
      ? formatted.reduce((sum, point) => sum + (point.cost_usd ?? 0), 0) / formatted.length
      : 0
  const latestPoint = formatted[formatted.length - 1]
  const firstPoint = formatted[0]
  const periodDelta = latestPoint && firstPoint ? latestPoint.cost_usd - firstPoint.cost_usd : 0
  const periodDeltaPct =
    latestPoint && firstPoint && firstPoint.cost_usd !== 0
      ? (periodDelta / firstPoint.cost_usd) * 100
      : null

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={formatted} margin={{ top: 14, right: 8, left: -10, bottom: 6 }}>
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity={0.26} />
              <stop offset="55%" stopColor="#3b82f6" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="#e5e7eb" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            minTickGap={24}
            tickMargin={10}
          />
          <YAxis
            tickFormatter={(value) => formatAxisValue(value, currency)}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            width={72}
            tickMargin={10}
          />
          <Tooltip content={<CustomTooltip />} />
          {averageCost > 0 && (
            <ReferenceLine
              y={averageCost}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />
          )}
          {buildRefLines(refEvents)}
          <Area
            type="monotone"
            dataKey="cost_usd"
            stroke="#2563eb"
            strokeWidth={2.5}
            fill="url(#costGradient)"
            dot={<EventDot />}
            activeDot={{ r: 6, fill: '#2563eb', stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-xs">
        {latestPoint && (
          <span className="font-medium text-slate-700">
            Latest: <span className="text-slate-900">{formatMoney(latestPoint.cost_usd, currency)}</span>
          </span>
        )}
        {formatted.length > 0 && (
          <span className="text-slate-500">
            Average: <span className="font-medium text-slate-700">{formatMoney(averageCost, currency)}</span>
          </span>
        )}
        {latestPoint && firstPoint && (
          <span className={periodDelta >= 0 ? 'text-rose-600' : 'text-emerald-600'}>
            Period delta: {periodDelta > 0 ? '+' : ''}
            {formatMoney(periodDelta, currency)}
            {periodDeltaPct == null ? '' : ` · ${periodDeltaPct > 0 ? '+' : ''}${periodDeltaPct.toFixed(1)}%`}
          </span>
        )}
      </div>

      {events.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1.5 border-t border-slate-100 pt-3">
          {(Object.keys(EVENT_COLOR) as ChangeEventType[])
            .filter((t) => events.some((e) => e.event_type === t))
            .map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: EVENT_COLOR[t] }}
                />
                <span className="text-[11px] text-slate-500">{EVENT_LABEL[t]}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
