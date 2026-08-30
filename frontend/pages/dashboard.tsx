import React, { useState } from 'react'

type Phase4 = {
  status?: string
  sources?: Record<string, { state?: string; path?: string; message?: string }>
  reason?: string
}

type Suspect = {
  mmsi: string
  shipname?: string
  type?: string
  sog_knots?: number
  attribution_score?: number
  attribution_evidence?: Record<string, number>
  synthetic?: boolean
  source?: string
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

  return (
    <div className="min-h-screen bg-[#e9f7ff] text-slate-800">
      <header className="max-w-6xl mx-auto p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-gradient-to-br from-cyan-600 to-sky-600 flex items-center justify-center text-white font-semibold">M</div>
          <div>
            <div className="text-lg font-bold">MARTRACE</div>
            <div className="text-sm text-slate-600">Marine spill investigation & source attribution</div>
          </div>
        </div>
        <nav>
          <a href="/" className="text-sm text-slate-700 hover:underline">Home</a>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-1 bg-white rounded-lg shadow p-6">
          <h2 className="font-semibold mb-3">1. Incident / image intake</h2>
          <label className="block text-sm text-slate-600 mb-2">Choose image</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
          />

          <div className="mt-4 flex items-center gap-3">
            <button
              className="px-4 py-2 bg-sky-600 text-white rounded disabled:opacity-60"
              onClick={handleAnalyze}
              disabled={loading}
            >
              Analyze
            </button>
            {loading && <div className="text-sm text-slate-600">Processing... please wait</div>}
          </div>

          {error && <div className="mt-4 p-3 bg-red-50 text-red-700 rounded">{error}</div>}

          <div className="mt-6 text-sm text-slate-600">
            <strong>Notes:</strong>
            <ul className="list-disc ml-5 mt-2">
              <li>Uploads are sent to the analysis API.</li>
              <li>Respecting privacy: no local paths are exposed.</li>
            </ul>
          </div>
        </section>

        <section className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-2">2. Detection evidence</h3>
            {result?.proof_image_path ? (
              <img src={result.proof_image_path} alt="proof" className="w-full rounded border" />
            ) : (
              <div className="text-sm text-slate-500">No proof image available</div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-2">3. Environmental data</h3>
              <div className="text-sm text-slate-600">
                <div><strong>Phase 4 status:</strong> {result?.phase4?.status || 'Unknown'}</div>
                {result?.phase4?.reason && <div className="mt-2">{result.phase4.reason}</div>}
                {result?.phase4?.sources && (
                  <ul className="mt-2 ml-4 list-disc text-sm">
                    {Object.entries(result.phase4.sources).map(([k, v]: any) => (
                      <li key={k} className="break-words">{k}: {v.state} {v.message && `- ${v.message}`}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2">4. Backtracked origin zone</h3>
              {result?.origin_zone ? (
                <pre className="p-2 bg-slate-50 text-xs rounded overflow-auto max-h-48">{JSON.stringify(result.origin_zone, null, 2)}</pre>
              ) : (
                <div className="text-sm text-slate-500">Origin zone not available</div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-2">5. Trajectory</h3>
            {result?.trajectory?.visualization_path ? (
              <img src={result.trajectory.visualization_path} alt="trajectory" className="w-full rounded border" />
            ) : (
              <div className="text-sm text-slate-500">No trajectory visualization</div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-2">6. Vessel attribution / evidence</h3>
            {Array.isArray(result?.suspects) && result.suspects.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="text-left border-b"><th className="p-2">MMSI</th><th>Name</th><th>Type</th><th>Speed</th><th>Score</th><th>Source</th><th>Evidence</th></tr>
                  </thead>
                  <tbody>
                    {result.suspects.map((s: Suspect, i: number) => (
                      <tr key={s.mmsi || i} className="border-b align-top">
                        <td className="p-2 align-top">{s.mmsi}</td>
                        <td className="p-2 align-top break-words max-w-sm">{s.shipname || '—'}</td>
                        <td className="p-2 align-top">{s.type || '—'}</td>
                        <td className="p-2 align-top">{s.sog_knots ?? '—'}</td>
                        <td className="p-2 align-top">{s.attribution_score ?? '—'}</td>
                        <td className="p-2 align-top">{s.synthetic ? <span className="text-xs text-amber-700">Synthetic AIS</span> : (s.source || 'Live')}</td>
                        <td className="p-2 align-top"><pre className="text-xs max-w-md overflow-auto">{JSON.stringify(s.attribution_evidence || {}, null, 2)}</pre></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-sm text-slate-500">No suspects returned</div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
