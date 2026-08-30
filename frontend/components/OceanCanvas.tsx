import React from 'react'

type OceanCanvasProps = {
  className?: string
}

export default function OceanCanvas({
  className = '',
}: OceanCanvasProps) {
  return (
    <div
      className={className}
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        background: '#0a3a66',
      }}
    >
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
          display: 'block',
        }}
      >
        <source src="/ocean.mp4" type="video/mp4" />
      </video>

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(8, 48, 78, 0.18) 0%, rgba(5, 35, 60, 0.28) 100%)',
        }}
      />
    </div>
  )
}
