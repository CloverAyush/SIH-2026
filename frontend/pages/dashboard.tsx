import React, { useState } from 'react'

type Phase4 = {
  status?: string
  sources?: Record<string, { state?: string; path?: string; message?: string }>
  reason?: string
  requested_hours?: number
  simulated_hours?: number
}

type Suspect = {
  mmsi: string
  shipname?: string
  type?: string
  sog_knots?: number
  attribution_score?: number
  investigative_compatibility_score?: number
  risk?: string
  confidence?: string
  attribution_evidence?: Record<string, any>
  evidence_breakdown?: Record<string, any>
  human_reasons?: string[]
  reasons?: string[]
  synthetic?: boolean
  source?: string
}

const fmtStatus = (status?: string) => {
  if (!status) return 'PENDING'
  return status.toUpperCase()
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any | null>(null)

  async function handleAnalyze() {
    setError(null)
    if (!file) {
      setError('Please choose an image file to upload')
      return
    }
    setLoading(true)
    try {
      const form = new FormData()
      form.append('file', file, file.name)
      const res = await fetch('http://127.0.0.1:8000/api/analyze', {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Server error: ${res.status} ${text}`)
      }
      const payload = await res.json()
      setResult(payload)
    } catch (err: any) {
      setError(err?.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  const sceneName = file?.name || result?.image_name || 'No scene selected'
  const acquisitionTime = result?.acquisition_time || result?.origin_zone?.target_time || 'Not available'
  const detectionStatus = result?.status || 'PENDING'
  const noOilStatuses = ['no_oil_detected', 'no_oil_contours']
  const oilDetected = detectionStatus && ![...noOilStatuses, 'phase4_failed', 'no_origin_zone'].includes(detectionStatus)
  const showNoOilState = !!result && noOilStatuses.includes(detectionStatus)
  const phase4: Phase4 = result?.phase4 || {}
  const suspects = Array.isArray(result?.suspects) ? result.suspects : []
  const spillArea = result?.geojson?.features?.[0]?.geometry?.coordinates?.[0] || null
  const originZone = result?.origin_zone || null

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/10 text-base font-bold text-cyan-300">
              M
            </div>
            <div>
              <div className="text-xl font-semibold tracking-[0.18em] text-slate-200">MARTRACE</div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Oil Spill Investigation &amp; Maritime Intelligence</div>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.9)]" />
            System online
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between border-b border-slate-800 pb-5">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Operational overview</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-50">Investigation dashboard</h1>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm text-slate-300">
            {fmtStatus(phase4.status || detectionStatus)} status
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <aside className="col-span-4 space-y-6">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/30">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-100">Scene / input</h2>
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-300">
                  Intake
                </span>
              </div>

              <div className="space-y-4">
                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-400">Scene</span>
                  <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/70 px-3 py-3 text-sm text-slate-200">
                    {sceneName}
                  </div>
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-400">Analysis state</span>
                  <div className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-slate-200">
                    {loading ? 'Processing image' : result ? 'Completed' : 'Awaiting analysis'}
                  </div>
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Acquired</div>
                    <div className="mt-2 text-sm text-slate-200">{acquisitionTime}</div>
                  </div>
                  <div className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Data source</div>
                    <div className="mt-2 text-sm text-slate-200">Satellite / AIS</div>
                  </div>
                </div>

                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                  className="block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 file:mr-3 file:rounded file:border-0 file:bg-cyan-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white"
                />

                <button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="w-full rounded-xl bg-cyan-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Processing...' : 'Run investigation'}
                </button>

                {error && (
                  <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                    {error}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-100">Phase 4 / backtracking</h2>
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-300">
                  Drift model
                </span>
              </div>
              <div className="space-y-3 text-sm text-slate-300">
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Status</div>
                  <div className="mt-2 text-base font-medium text-slate-100">{fmtStatus(phase4.status || detectionStatus)}</div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Requested duration</div>
                  <div className="mt-2 text-base font-medium text-slate-100">{phase4.requested_hours ?? '48'} hrs</div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Actual sim duration</div>
                  <div className="mt-2 text-base font-medium text-slate-100">{phase4.simulated_hours ?? '—'} hrs</div>
                </div>
              </div>
            </section>
          </aside>

          <section className="col-span-8 space-y-6">
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-100">Detection panel</h2>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] ${oilDetected ? 'border border-amber-500/40 bg-amber-500/10 text-amber-200' : 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-200'}`}>
                    {oilDetected ? 'Oil detected' : 'No oil detected'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
                    <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Confidence</div>
                    <div className="mt-3 text-2xl font-semibold text-cyan-300">
                      {(() => {
                        const raw = String(result?.confidence || '').toUpperCase()
                        if (!raw) return 'N/A'
                        return raw === 'HIGH' || raw === 'MEDIUM' || raw === 'LOW' ? raw : 'N/A'
                      })()}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
                    <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Status</div>
                    <div className="mt-3 text-lg font-semibold text-slate-100">{fmtStatus(phase4.status || detectionStatus)}</div>
                  </div>
                </div>

                <div className="mt-5 overflow-hidden rounded-xl border border-slate-700 bg-slate-950">
                  {!result ? (
                    <div className="flex h-[28rem] items-center justify-center text-sm text-slate-400">Detection evidence will appear here</div>
                  ) : showNoOilState ? (
                    <div className="flex h-[28rem] flex-col items-center justify-center gap-3 bg-slate-950 px-6 text-center">
                      <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-emerald-200">No oil detected</div>
                      <div className="text-lg font-semibold text-slate-100">No oil signature was identified in this scene.</div>
                      <div className="max-w-md text-sm text-slate-400">The detection pipeline completed without a valid spill contour, so no spill evidence is being displayed.</div>
                    </div>
                  ) : result?.proof_image_path ? (
                    <img src={result.proof_image_path} alt="Detection proof image" className="h-[28rem] w-full object-contain bg-slate-950" />
                  ) : (
                    <div className="flex h-[28rem] items-center justify-center text-sm text-slate-400">Detection evidence will appear here</div>
                  )}
                </div>
              </div>

              <div className="col-span-4 space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                  <h3 className="text-lg font-semibold text-slate-100">System health</h3>
                  <div className="mt-4 space-y-3 text-sm text-slate-300">
                    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2">
                      <span>Weather data</span>
                      <span className="text-emerald-300">Stable</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2">
                      <span>Currents</span>
                      <span className="text-emerald-300">Ready</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2">
                      <span>Phase 4</span>
                      <span className={phase4.status === 'COMPLETED' ? 'text-emerald-300' : phase4.status === 'PARTIAL' ? 'text-amber-300' : 'text-slate-300'}>
                        {phase4.status || 'PENDING'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                  <h3 className="text-lg font-semibold text-slate-100">Operational status</h3>
                  <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-slate-300">
                    {result?.phase4?.reason || 'Awaiting analysis results.'}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-6 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-100">Origin zone detection</h2>
                  <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-cyan-200">Backtracking</span>
                </div>

                <div className="space-y-3 text-sm text-slate-300">
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                    <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Detected zone</div>
                    <div className="mt-2 text-base font-medium text-slate-100">
                      {originZone ? `${originZone.min_lat?.toFixed?.(3) ?? originZone.min_lat ?? '—'} / ${originZone.max_lat?.toFixed?.(3) ?? originZone.max_lat ?? '—'} LAT · ${originZone.min_lon?.toFixed?.(3) ?? originZone.min_lon ?? '—'} / ${originZone.max_lon?.toFixed?.(3) ?? originZone.max_lon ?? '—'} LON` : 'No origin zone detected yet'}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                    <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Target time</div>
                    <div className="mt-2 text-base font-medium text-slate-100">{originZone?.target_time || 'N/A'}</div>
                  </div>
                </div>
              </div>

              <div className="col-span-6 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-100">Environmental model</h2>
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-emerald-200">Ready</span>
                </div>

                <div className="space-y-3 text-sm text-slate-300">
                  <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 px-3 py-3">
                    <span>Phase 4 status</span>
                    <span className="font-medium text-slate-100">{fmtStatus(phase4.status)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 px-3 py-3">
                    <span>Requested hours</span>
                    <span className="font-medium text-slate-100">{phase4.requested_hours ?? '48'}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 px-3 py-3">
                    <span>Simulated hours</span>
                    <span className="font-medium text-slate-100">{phase4.simulated_hours ?? '—'}</span>
                  </div>
                  {phase4.sources && (
                    <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Data source status</div>
                      <div className="mt-2 space-y-2">
                        {Object.entries(phase4.sources).map(([key, value]: any) => (
                          <div key={key} className="flex items-center justify-between gap-3 text-xs text-slate-300">
                            <span className="capitalize">{key}</span>
                            <span className={value.state === 'CACHED' || value.state === 'LIVE' ? 'text-emerald-300' : 'text-amber-300'}>{value.state || 'UNKNOWN'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-100">Trajectory / vessel attribution</h2>
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-amber-200">Top suspects</span>
              </div>

              {result?.trajectory?.visualization_path ? (
                <div className="mb-5 overflow-hidden rounded-xl border border-slate-700 bg-slate-950">
                  <img src={result.trajectory.visualization_path} alt="Trajectory map" className="h-[30rem] w-full object-contain bg-slate-950" />
                </div>
              ) : (
                <div className="mb-5 flex h-[30rem] items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950 px-4 text-center text-sm text-slate-400">
                  Trajectory visualization will appear after analysis.
                </div>
              )}

              {suspects.length > 0 ? (
                <div className="space-y-4">
                  {suspects.map((suspect: Suspect, idx: number) => {
                    const reasons = suspect.reasons || suspect.human_reasons || []
                    const evidence = suspect.evidence_breakdown || suspect.attribution_evidence || {}
                    const score = suspect.investigative_compatibility_score ?? suspect.attribution_score ?? 0
                    const risk = suspect.risk || 'LOW'
                    const confidence = suspect.confidence || 'LOW'

                    return (
                      <div key={suspect.mmsi || idx} className="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <div className="text-lg font-semibold text-slate-100">{suspect.shipname || 'Unnamed vessel'}</div>
                            <div className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">{suspect.type || 'Unknown type'} • MMSI {suspect.mmsi}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-xs font-medium text-cyan-200">Score {score}</span>
                            <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-200">{risk}</span>
                            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-200">{confidence}</span>
                          </div>
                        </div>

                        <div className="grid gap-4 md:grid-cols-3">
                          <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Ship data</div>
                            <div className="mt-2 space-y-1 text-sm text-slate-300">
                              <div>SOG: {suspect.sog_knots ?? '—'} kn</div>
                              <div>Source: {suspect.source || 'synthetic'}</div>
                              <div>Track points: {Array.isArray(suspect.track) ? suspect.track.length : 0}</div>
                            </div>
                          </div>

                          <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Evidence</div>
                            <div className="mt-2 space-y-1 text-sm text-slate-300">
                              <div>Spatial: {evidence?.spatiotemporal?.score ?? evidence?.spatial ?? '—'}</div>
                              <div>Trajectory: {evidence?.trajectory?.score ?? '—'}</div>
                              <div>Behavioral: {evidence?.behavioral?.score ?? '—'}</div>
                            </div>
                          </div>

                          <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Why flagged</div>
                            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-300">
                              {reasons.length > 0 ? reasons.slice(0, 3).map((reason, reasonIdx) => <li key={reasonIdx}>{reason}</li>) : <li>No reason recorded.</li>}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950 px-4 py-10 text-center text-sm text-slate-400">
                  No vessel candidates returned.
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
