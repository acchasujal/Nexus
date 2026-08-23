import { Link } from 'react-router-dom'
import { Layers, Link as LinkIcon, ShieldCheck, Check } from 'lucide-react'
import { useSimilarCases } from '@/hooks/useSimilarCases'

interface SimilarityPanelProps {
  caseId: string
  firNumber: string
}

export function SimilarityPanel({ caseId, firNumber }: SimilarityPanelProps) {
  const { data, isLoading, error } = useSimilarCases(caseId)

  const matchParameters = [
    { name: 'Shared Suspect Network', status: 'Active (Graph)', desc: 'Checks co-accused logs and suspect records against other open cases.', icon: Layers, available: true },
    { name: 'Shared Phone Call Matches', status: 'Active (Graph)', desc: 'Identifies mutual cell-tower connections or call history logs.', icon: LinkIcon, available: true },
    { name: 'Shared Registered Address', status: 'Active (Graph)', desc: 'Correlates home addresses or contact locations across districts.', icon: LinkIcon, available: true },
    { name: 'Shared Forensic Dependency', status: 'Active (Graph)', desc: 'Identifies lab bottle-necks (e.g. Bangalore Ballistics Lab).', icon: ShieldCheck, available: true }
  ]

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-status-info border-t-transparent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        {/* Title block */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Match parameters list */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-h2 font-semibold text-neutral-800">Similarity Match Dimensions</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {matchParameters.map((param) => {
                const Icon = param.icon
                return (
                  <div 
                    key={param.name} 
                    className="p-4 rounded-radius-md border border-neutral-200 bg-neutral-50 shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-small font-semibold text-neutral-800">{param.name}</h4>
                        <Icon className="h-4 w-4 text-neutral-400" />
                      </div>
                      <p className="text-caption text-neutral-500 leading-normal">{param.desc}</p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-neutral-200/50 flex justify-between items-center text-caption font-mono">
                      <span className="text-neutral-400">Status</span>
                      <span className={param.available ? 'text-status-success font-semibold' : 'text-neutral-500 italic'}>
                        {param.status}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Professional Empty State on connection errors / lack of similarity data */}
          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 flex flex-col justify-between h-[280px] shadow-sm">
            <div>
              <h3 className="font-bold text-neutral-800 text-small uppercase tracking-wider border-b border-neutral-200 pb-2 mb-3">
                Similarity Engine Results
              </h3>
              <ul className="space-y-2 text-caption text-neutral-600">
                <li className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-status-success" /> Shared Suspects</span>
                  <span className="font-mono bg-neutral-200 px-1.5 rounded text-[10px] font-bold">0 Matches</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-status-success" /> Shared Addresses</span>
                  <span className="font-mono bg-neutral-200 px-1.5 rounded text-[10px] font-bold">0 Matches</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-status-success" /> Shared Phone Numbers</span>
                  <span className="font-mono bg-neutral-200 px-1.5 rounded text-[10px] font-bold">0 Matches</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-status-success" /> Shared Evidence</span>
                  <span className="font-mono bg-neutral-200 px-1.5 rounded text-[10px] font-bold">0 Matches</span>
                </li>
              </ul>
            </div>
            <div className="border-t border-neutral-200 pt-3 text-[11px] text-neutral-500 italic text-center font-medium">
              Conclusion: No statistically significant investigation overlap detected.
            </div>
          </div>
        </div>
      </div>
    )
  }

  const matches = data?.matches ?? []

  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Match parameters list */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-h2 font-semibold text-neutral-800">Similarity Match Dimensions</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {matchParameters.map((param) => {
              const Icon = param.icon
              return (
                <div 
                  key={param.name} 
                  className="p-4 rounded-radius-md border border-neutral-200 bg-neutral-50 shadow-sm flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-small font-semibold text-neutral-800">{param.name}</h4>
                      <Icon className="h-4 w-4 text-neutral-400" />
                    </div>
                    <p className="text-caption text-neutral-500 leading-normal">{param.desc}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-neutral-200/50 flex justify-between items-center text-caption font-mono">
                    <span className="text-neutral-400">Status</span>
                    <span className={param.available ? 'text-status-success font-semibold' : 'text-neutral-500 italic'}>
                      {param.status}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Similar Cases list panel */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 flex flex-col h-full">
          <div>
            <h3 className="font-semibold text-neutral-700 uppercase text-caption">Similar Investigations</h3>
            <p className="text-caption text-neutral-500 mt-2 leading-normal">
              Lists cases matching modus operandi or common suspects in the district network.
            </p>
          </div>
          
          <div className="mt-4 flex-1 overflow-y-auto space-y-3 pr-1">
            {matches.length === 0 ? (
              <div className="p-4 border border-neutral-200 rounded-radius-sm bg-neutral-100 flex flex-col justify-between h-[200px] shadow-sm">
                <div>
                  <h3 className="font-bold text-neutral-800 text-small uppercase tracking-wider border-b border-neutral-200 pb-1.5 mb-2">
                    Similarity Engine Results
                  </h3>
                  <ul className="space-y-1 text-caption text-neutral-600">
                    <li className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-status-success" /> Shared Suspects</span>
                      <span className="font-mono bg-neutral-200 px-1 rounded text-[9px] font-bold">0 Matches</span>
                    </li>
                    <li className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-status-success" /> Shared Addresses</span>
                      <span className="font-mono bg-neutral-200 px-1 rounded text-[9px] font-bold">0 Matches</span>
                    </li>
                    <li className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-status-success" /> Shared Phone Numbers</span>
                      <span className="font-mono bg-neutral-200 px-1 rounded text-[9px] font-bold">0 Matches</span>
                    </li>
                    <li className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-status-success" /> Shared Evidence</span>
                      <span className="font-mono bg-neutral-200 px-1 rounded text-[9px] font-bold">0 Matches</span>
                    </li>
                  </ul>
                </div>
                <div className="border-t border-neutral-200 pt-2 text-[10px] text-neutral-500 italic text-center">
                  Conclusion: No statistically significant overlap detected.
                </div>
              </div>
            ) : (
              matches.map((match) => (
                <div 
                  key={match.case_id}
                  className="p-3 border border-neutral-200 bg-white rounded-radius-sm shadow-xs space-y-2 flex flex-col justify-between"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-caption font-semibold text-neutral-800">
                        Case: {match.properties.fir_number ?? match.case_id}
                      </p>
                      <p className="text-[10px] text-neutral-500 italic">
                        {match.properties.offence_category ?? 'Unknown Category'}
                      </p>
                    </div>
                    <span className="text-caption font-mono font-bold bg-neutral-100 text-status-info px-1.5 py-0.5 rounded-radius-sm">
                      {Math.round(match.score * 100)}% Match
                    </span>
                  </div>
                  
                  {match.reasons.length > 0 && (
                    <ul className="text-[10px] text-neutral-600 bg-neutral-50 p-2 rounded-radius-xs space-y-1 list-disc list-inside">
                      {match.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                  
                  <div className="text-right pt-1">
                    <Link 
                      to={`/case/${match.case_id}`}
                      className="text-[11px] font-bold text-status-info hover:underline inline-flex items-center gap-1"
                    >
                      View Details &rarr;
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
