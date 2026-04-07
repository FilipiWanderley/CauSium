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

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  const cost: number = point?.cost_usd ?? 0
  const events: ChangeEvent[] = point?.events ?? []

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-lg text-xs min-w-[180px]">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      <p className="text-gray-500 mb-2">
        Cost:{' '}
        <span className="font-bold text-gray-800">${cost.toLocaleString()}</span>
      </p>
      {events.length > 0 && (
        <div className="border-t border-gray-100 pt-2 space-y-1.5">
          <p className="text-gray-400 font-medium uppercase tracking-wide" style={{ fontSize: 10 }}>
            Events on this day
          </p>
          {events.map((ev) => (
            <div key={ev.id} className="flex items-start gap-1.5">
              <span
                className="mt-0.5 h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: EVENT_COLOR[ev.event_type] }}
              />
              <div>
                <span style={{ color: EVENT_COLOR[ev.event_type] }} className="font-medium">
                  {EVENT_LABEL[ev.event_type]}
                </span>
                <p className="text-gray-500 leading-tight">{ev.title}</p>
                {ev.cost_impact_usd != null && (
                  <p
                    className={
                      ev.cost_impact_usd > 0 ? 'text-red-500 font-semibold' : 'text-green-600 font-semibold'
                    }
                  >
                    {ev.cost_impact_usd > 0 ? '+' : ''}$
                    {Math.abs(ev.cost_impact_usd).toLocaleString(undefined, { maximumFractionDigits: 0 })}
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
      {/* Pulse ring */}
      <circle cx={cx} cy={cy} r={10} fill={color} fillOpacity={0.15} />
      {/* Solid dot */}
      <circle cx={cx} cy={cy} r={5} fill={color} stroke="#fff" strokeWidth={1.5} />
      {/* Count badge if > 1 */}
      {count > 1 && (
        <text x={cx + 7} y={cy - 7} fontSize={9} fill={color} fontWeight={700}>
          {count}
        </text>
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
}

const formatUSD = (v: number) =>
  v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`

export function CostTrendChart({ data, events = [], height = 220 }: Props) {
  // Group events by YYYY-MM-DD
  const eventsByDate: Record<string, ChangeEvent[]> = {}
  for (const ev of events) {
    const day = ev.occurred_at.slice(0, 10)
    if (!eventsByDate[day]) eventsByDate[day] = []
    eventsByDate[day].push(ev)
  }

  // Merge into trend data
  const formatted = data.map((d) => {
    const dateStr = (d.date as unknown as string).slice(0, 10)
    return {
      ...d,
      dateLabel: format(parseISO(dateStr), 'MMM d'),
      events: eventsByDate[dateStr] ?? [],
    }
  })

  const refEvents = formatted.filter((f) => f.events.length > 0)

  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={formatted} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={formatUSD}
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          {buildRefLines(refEvents)}
          <Area
            type="monotone"
            dataKey="cost_usd"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#costGradient)"
            dot={<EventDot />}
            activeDot={{ r: 5, fill: '#3b82f6' }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Legend */}
      {events.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
          {(Object.keys(EVENT_COLOR) as ChangeEventType[])
            .filter((t) => events.some((e) => e.event_type === t))
            .map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: EVENT_COLOR[t] }}
                />
                <span className="text-xs text-gray-500">{EVENT_LABEL[t]}</span>
              </div>
            ))}
        </div>
      )}
    </>
  )
}
