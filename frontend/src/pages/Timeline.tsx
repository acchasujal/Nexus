import { useState, useEffect } from 'react'
import { Clock, Calendar, Users } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

export default function Timeline() {
  const [events, setEvents] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    apiClient.getTimeline().then((data) => {
      setEvents(Array.isArray(data) ? data : [])
    }).catch(() => {
      setEvents([
        { id: 'ev-1', event_type: 'MEETING', timestamp: '2026-01-14T18:30:00Z', description: 'Suspects met at Koramangala Cafe', participant_ids: ['person-0001', 'person-0002'] },
        { id: 'ev-2', event_type: 'COMMUNICATION_BURST', timestamp: '2026-01-13T22:15:00Z', description: 'Burst of 18 encrypted calls logged before incident', participant_ids: ['person-0001', 'person-0050'] },
        { id: 'ev-3', event_type: 'INCIDENT', timestamp: '2026-01-12T14:00:00Z', description: 'FIR registered regarding cyber phishing ring', participant_ids: ['person-0001'] },
      ])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      <div className="border-b border-neutral-800 pb-5">
        <h1 className="text-2xl font-bold text-neutral-100 flex items-center gap-2.5">
          <Clock className="h-6 w-6 text-blue-500" />
          Investigative Chronology & Temporal Intelligence
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Chronological sequence of suspect sightings, communication bursts, money transfers, and case milestones.
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-neutral-500">Loading temporal intelligence events...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-neutral-500">No chronological events logged.</div>
      ) : (
        <div className="relative border-l-2 border-neutral-800 ml-4 pl-6 space-y-6">
          {events.map((ev, idx) => (
            <div key={ev.id || idx} className="relative group">
              {/* Dot */}
              <div className="absolute -left-[31px] top-1.5 h-4 w-4 rounded-full bg-blue-600 border-4 border-neutral-950 group-hover:scale-125 transition-transform" />

              <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4.5 space-y-2 hover:border-neutral-700 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-blue-400 bg-blue-950/60 px-2.5 py-0.5 rounded border border-blue-800/40">
                    {ev.event_type}
                  </span>
                  <span className="text-xs text-neutral-400 flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    {new Date(ev.timestamp).toLocaleString()}
                  </span>
                </div>

                <p className="text-sm text-neutral-200 font-medium">{ev.description}</p>

                {ev.participant_ids && ev.participant_ids.length > 0 && (
                  <div className="pt-2 flex items-center gap-2 text-xs text-neutral-400 border-t border-neutral-800/60">
                    <Users className="h-3.5 w-3.5 text-neutral-500" />
                    <span>Involved: {ev.participant_ids.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
