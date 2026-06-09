import React from "react";

export const UploadHeroIllustration: React.FC = () => {
  return (
    <div className="w-full h-full flex items-center justify-center p-4">
      <svg
        viewBox="0 0 280 140"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full max-w-[240px] md:max-w-[280px] drop-shadow-sm select-none"
      >
        {/* Definition for gradients and markers */}
        <defs>
          <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4f7df3" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
          <linearGradient id="grayGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f8fafc" />
            <stop offset="100%" stopColor="#e2e8f0" />
          </linearGradient>
          <linearGradient id="engineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f1f5f9" />
            <stop offset="100%" stopColor="#cbd5e1" />
          </linearGradient>
          <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0f172a" floodOpacity="0.05" />
          </filter>
        </defs>

        {/* 1. Resume Document (Left Side) */}
        <g filter="url(#shadow)">
          <rect x="10" y="25" width="55" height="76" rx="6" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
          {/* Header Line */}
          <rect x="20" y="37" width="22" height="4" rx="2" fill="#4f7df3" fillOpacity="0.8" />
          {/* Text Lines */}
          <line x1="20" y1="49" x2="55" y2="49" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="20" y1="57" x2="48" y2="57" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="20" y1="65" x2="52" y2="65" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="20" y1="73" x2="42" y2="73" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
          {/* Profile Circle Accent */}
          <circle cx="48" cy="39" r="6" fill="#f1f5f9" stroke="#e2e8f0" strokeWidth="1" />
          <path d="M44 44C44 42.5 45.5 41.5 48 41.5C50.5 41.5 52 42.5 52 44" stroke="#94a3b8" strokeWidth="1" strokeLinecap="round" />
        </g>

        {/* Arrow 1: Resume -> Engine */}
        <path
          d="M75 63 C 90 63, 95 63, 110 63"
          stroke="#cbd5e1"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          strokeLinecap="round"
        />
        <path d="M106 59.5L111.5 63L106 66.5" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* 2. Intelligence Engine Hub (Center) */}
        <g filter="url(#shadow)">
          {/* Outer Ring */}
          <circle cx="140" cy="63" r="28" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
          {/* Inner Tint */}
          <circle cx="140" cy="63" r="22" fill="#f8fafc" stroke="#f1f5f9" strokeWidth="1" />
          
          {/* Rotating Gear Icon */}
          <g transform="translate(140, 63)">
            <circle cx="0" cy="0" r="10" stroke="url(#blueGrad)" strokeWidth="3.5" fill="none" />
            {/* Gear teeth */}
            {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
              <line
                key={i}
                x1="0"
                y1="-9"
                x2="0"
                y2="-13"
                stroke="url(#blueGrad)"
                strokeWidth="3.5"
                strokeLinecap="round"
                transform={`rotate(${angle})`}
              />
            ))}
            <circle cx="0" cy="0" r="4" fill="#ffffff" />
          </g>
        </g>

        {/* Arrow 2: Engine -> Career Insights */}
        <path
          d="M170 63 C 185 63, 190 63, 205 63"
          stroke="#cbd5e1"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          strokeLinecap="round"
        />
        <path d="M201 59.5L206.5 63L201 66.5" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* 3. Career Insights Dashboard (Right Side) */}
        <g filter="url(#shadow)">
          <rect x="215" y="25" width="55" height="76" rx="6" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
          {/* Metric Bar 1 */}
          <rect x="223" y="37" width="39" height="12" rx="3" fill="#f0f9ff" stroke="#e0f2fe" strokeWidth="1" />
          <rect x="227" y="41" width="24" height="4" rx="2" fill="#3b82f6" />
          
          {/* Metric Bar 2 */}
          <rect x="223" y="53" width="39" height="12" rx="3" fill="#f0fdf4" stroke="#dcfce7" strokeWidth="1" />
          <rect x="227" y="57" width="18" height="4" rx="2" fill="#22c55e" />

          {/* Metric Bar 3 */}
          <rect x="223" y="69" width="39" height="12" rx="3" fill="#faf5ff" stroke="#f3e8ff" strokeWidth="1" />
          <rect x="227" y="73" width="30" height="4" rx="2" fill="#a855f7" />

          {/* Small Sparkle/Checkmark of insight */}
          <circle cx="253" cy="43" r="2.5" fill="#3b82f6" />
          <circle cx="247" cy="59" r="2.5" fill="#22c55e" />
          <circle cx="251" cy="75" r="2.5" fill="#a855f7" />
        </g>
      </svg>
    </div>
  );
};
