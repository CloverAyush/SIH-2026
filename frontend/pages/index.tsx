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

export default function Home() {
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
    <main className="container font-sans">
      <h1 className="text-2xl font-bold mb-4">Oil Spill Demo - Minimal Frontend</h1>

      <section className="mb-4">
        <label className="block mb-2">Choose image</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
        />
      </section>

      <div className="flex items-center gap-2 mb-6">
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-60"
          onClick={handleAnalyze}
          disabled={loading}
        >
          Analyze
        </button>
        {loading && <div>Processing... please wait (this may take a while)</div>}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-800">Error: {error}</div>
      )}

      {result && (
        <section>
          <h2 className="text-xl font-semibold mb-2">Result: {result.status}</h2>

          <div className="mb-4">
            <strong>Phase 4 status:</strong> {result.phase4?.status}
            {result.phase4?.reason && <div>{result.phase4.reason}</div>}
            {result.phase4?.sources && (
              <div className="mt-2">
                <strong>Sources:</strong>
                <ul className="ml-4">
                  {Object.entries(result.phase4.sources).map(([k, v]: any) => (
                    <li key={k}>{k}: {v.state} - {v.message} {v.path && (<a className="text-blue-600 ml-2" href={v.path} target="_blank" rel="noreferrer">artifact</a>)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="mb-4">
            <strong>Proof image:</strong>
            <div>
              {result.proof_image_path ? (
                <img src={result.proof_image_path} alt="proof" className="max-w-full mt-2 border" />
              ) : (
                <div>No proof image available</div>
              )}
            </div>
          </div>

          <div className="mb-4">
            <strong>Origin zone:</strong>
            <pre className="p-2 bg-gray-100">{JSON.stringify(result.origin_zone, null, 2)}</pre>
          </div>

          <div className="mb-4">
            <strong>Trajectory visualization:</strong>
            <div>
              {result.trajectory?.visualization_path ? (
                <img src={result.trajectory.visualization_path} alt="trajectory" className="max-w-full mt-2 border" />
              ) : (
                <div>No trajectory visualization</div>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold">Ranked suspects</h3>
            {Array.isArray(result.suspects) && result.suspects.length > 0 ? (
              <table className="w-full mt-2 border-collapse">
                <thead>
                  <tr className="text-left border-b"><th>MMSI</th><th>Name</th><th>Type</th><th>SOG</th><th>Score</th><th>Synthetic</th><th>Evidence</th></tr>
                </thead>
                <tbody>
                  {result.suspects.map((s: Suspect, i: number) => (
                    <tr key={s.mmsi || i} className="border-b">
                      <td className="py-2">{s.mmsi}</td>
                      <td>{s.shipname}</td>
                      <td>{s.type}</td>
                      <td>{s.sog_knots}</td>
                      <td>{s.attribution_score}</td>
                      <td>{s.synthetic ? <span className="text-sm text-red-600">Synthetic</span> : 'Live'}</td>
                      <td>
                        <pre className="text-xs">{JSON.stringify(s.attribution_evidence || {}, null, 2)}</pre>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div>No suspects returned</div>
            )}
          </div>

        </section>
      )}
    </main>
  )
}
