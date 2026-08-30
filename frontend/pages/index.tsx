import Link from 'next/link'
import OceanCanvas from '../components/OceanCanvas'
import React from 'react'

function CompassMark() {
  return (
    <svg viewBox="0 0 72 72" aria-hidden="true" className="h-12 w-12 md:h-14 md:w-14">
      <circle cx="36" cy="36" r="27" fill="none" stroke="rgba(142, 214, 236, 0.9)" strokeWidth="1.1" />
      <circle cx="36" cy="36" r="22" fill="none" stroke="rgba(142, 214, 236, 0.6)" strokeWidth="0.8" strokeDasharray="1.5 7" />
      <circle cx="36" cy="36" r="31" fill="none" stroke="rgba(142, 214, 236, 0.4)" strokeWidth="0.7" />
      <g fill="none" stroke="rgba(145, 223, 244, 0.9)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M36 10v13M36 49v13M10 36h13M49 36h13" />
        <path d="M22 22l14 14M50 22L36 36M22 50l14-14M50 50L36 36" opacity="0.45" />
      </g>
      <g>
        <path d="M36 17l4.3 12.7L53 36l-12.7 6.3L36 55l-4.3-12.7L19 36l12.7-6.3L36 17z" fill="rgba(146, 215, 244, 0.9)" />
        <path d="M36 24l2.1 7.9L46 36l-7.9 4.1L36 48l-2.1-7.9L26 36l7.9-4.1L36 24z" fill="rgba(6, 31, 52, 0.9)" />
      </g>
      <circle cx="36" cy="36" r="2.7" fill="rgba(146, 215, 244, 0.95)" />
    </svg>
  )
}

function FeatureIcon({ type }: { type: 'detect' | 'reconstruct' | 'attribute' | 'evidence' }) {
  const common = 'h-10 w-10 text-cyan-200/95'

  if (type === 'detect') {
    return (
      <svg viewBox="0 0 64 64" className={common} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="32" cy="32" r="20" />
        <circle cx="32" cy="32" r="6" />
        <path d="M32 9v8M32 47v8M9 32h8M47 32h8" opacity="0.85" />
      </svg>
    )
  }

  if (type === 'reconstruct') {
    return (
      <svg viewBox="0 0 64 64" className={common} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14 42l14-18 12 12 16-22" />
        <path d="M12 48h40" opacity="0.8" />
        <path d="M18 18h8M16 24h10" opacity="0.8" />
      </svg>
    )
  }

  if (type === 'attribute') {
    return (
      <svg viewBox="0 0 64 64" className={common} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14 44h36v8H14z" opacity="0.8" />
        <path d="M18 44V24l14-14 14 14v20" />
        <path d="M18 30h8M38 30h8M26 23h12" opacity="0.8" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 64 64" className={common} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 18h40v26H12z" opacity="0.8" />
      <path d="M18 12h28v12H18z" opacity="0.85" />
      <path d="M22 25h20M22 31h20M22 37h12" />
    </svg>
  )
}

export default function Home() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[#082b47] text-sky-50">
      <OceanCanvas />
      <div className="absolute inset-0 bg-[rgba(2,18,30,0.18)]" />

      <div className="relative z-10 min-h-screen flex flex-col px-6 md:px-10 xl:px-16 pt-5 pb-4">
        <header className="mx-auto flex w-full max-w-[1500px] items-center justify-between gap-6">
          <div className="flex items-center gap-4 text-[#daf3ff]">
            <CompassMark />
            <div className="text-left leading-none">
              <div className="martrace-wordmark text-[1.15rem] md:text-[1.5rem] tracking-[0.28em] text-sky-100">MARTRACE</div>
              <div className="mt-2 hidden text-[0.52rem] font-medium uppercase tracking-[0.28em] text-sky-100/75 md:block">
                Marine spill investigation &amp; source attribution
              </div>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-[0.68rem] font-medium uppercase tracking-[0.28em] text-sky-100/90 md:flex">
            {['INVESTIGATE', 'ANALYZE', 'ATTRIBUTE', 'EVIDENCE'].map((item) => (
              <div key={item} className="flex items-center gap-2 whitespace-nowrap">
                <div className="flex h-5 w-5 items-center justify-center rounded-full border border-sky-200/70 text-[0.55rem] text-sky-100/80">
                  {item[0]}
                </div>
                <span>{item}</span>
              </div>
            ))}
          </nav>
        </header>

        <main className="flex flex-1 items-center justify-center">
          <div className="mx-auto flex max-w-[1200px] flex-col items-center pt-8 text-center">
            <div className="mb-5 flex items-center justify-center">
              <div className="flex h-[132px] w-[132px] items-center justify-center rounded-full border border-sky-200/60 bg-sky-100/5 shadow-[0_0_0_1px_rgba(163,225,255,0.08)]">
                <CompassMark />
              </div>
            </div>

            <h1 className="martrace-wordmark text-[5rem] leading-[0.86] tracking-[-0.11em] text-[#dfeef8] sm:text-[6.2rem] md:text-[9rem] lg:text-[11rem]">
              MARTRACE
            </h1>

            <div className="mt-4 h-px w-[18rem] bg-cyan-200/60 md:w-[28rem]" />

            <p className="mt-7 text-[0.9rem] font-medium uppercase tracking-[0.38em] text-sky-100/90 md:text-[1.1rem]">
              Marine spill investigation &amp; source attribution
            </p>

            <div className="mt-7 text-[1.2rem] font-light italic text-sky-100/85 md:text-[1.8rem]">
              <p>Advanced detection. Intelligent backtracking.</p>
              <p className="mt-1">Actionable attribution for a cleaner ocean.</p>
            </div>

            <div className="mt-9 w-full max-w-[520px]">
              <Link href="/dashboard" className="group block">
                <span className="flex items-center justify-center gap-4 rounded-xl border border-cyan-200/40 bg-[rgba(27,60,92,0.7)] px-7 py-5 text-[0.82rem] font-semibold uppercase tracking-[0.28em] text-sky-50 shadow-[0_14px_32px_rgba(3,14,26,0.38)] transition-colors duration-200 hover:bg-[rgba(19,46,71,0.8)] focus:outline-none">
                  <svg viewBox="0 0 72 72" className="h-6 w-6 text-cyan-200" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M18 36h28" />
                    <path d="M36 18l18 18-18 18" />
                    <path d="M14 18c4 0 7 3 7 7s-3 7-7 7-7-3-7-7 3-7 7-7z" opacity="0.5" />
                  </svg>
                  <span>Enter Dashboard</span>
                  <svg viewBox="0 0 24 24" className="h-4 w-4 text-cyan-200 transition-transform duration-200 group-hover:translate-x-1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12h14" />
                    <path d="M13 5l7 7-7 7" />
                  </svg>
                </span>
              </Link>
            </div>
          </div>
        </main>

        <div className="mx-auto w-full max-w-[1260px] pb-6 pt-3">
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { title: 'DETECT', text: 'Detect oil spills using satellite and AI models.', type: 'detect' },
              { title: 'RECONSTRUCT', text: 'Backtrack spill drift using ocean currents and winds.', type: 'reconstruct' },
              { title: 'ATTRIBUTE', text: 'Search AIS data to identify potential sources.', type: 'attribute' },
              { title: 'EVIDENCE', text: 'Review ranked suspects with evidence and confidence.', type: 'evidence' },
            ].map((item) => (
              <div key={item.title} className="flex items-center gap-4 border-t border-cyan-100/15 pt-4 text-left text-sky-50/90">
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-cyan-200/45 bg-white/5 text-cyan-100/90">
                  <FeatureIcon type={item.type as 'detect' | 'reconstruct' | 'attribute' | 'evidence'} />
                </div>
                <div>
                  <div className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-sky-100/95">{item.title}</div>
                  <div className="mt-1 max-w-[18rem] text-[0.78rem] leading-relaxed text-sky-100/80">{item.text}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 flex items-center justify-center gap-3 text-[0.72rem] font-semibold uppercase tracking-[0.35em] text-sky-100/85">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-cyan-200/70 text-[0.55rem]">✦</span>
            <span>Built for marine investigators</span>
          </div>
        </div>
      </div>
    </div>
  )
}
