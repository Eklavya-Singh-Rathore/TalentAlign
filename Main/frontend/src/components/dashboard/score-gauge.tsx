import React from "react";
import { MATCH_LEVEL_THEME } from "../../lib/constants";

interface ScoreGaugeProps {
  score?: number;
  matchLevel?: "EXCELLENT" | "GOOD" | "MODERATE" | "BELOW AVERAGE" | "POOR";
  loading?: boolean;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({ score = 0, matchLevel = "POOR", loading = false }) => {
  const theme = MATCH_LEVEL_THEME[matchLevel] || MATCH_LEVEL_THEME["POOR"];
  
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center w-full animate-fade-in">
        <div className="relative flex items-center justify-center">
          <div className="h-40 w-40 rounded-full border-[12px] border-slate-100 flex items-center justify-center relative overflow-hidden">
            <div className="absolute inset-0 animate-shimmer opacity-30" />
            <div className="flex flex-col items-center gap-1 bg-white p-4 rounded-full z-10 shadow-sm border border-slate-50">
              <div className="h-8 w-14 bg-slate-100 rounded animate-shimmer" />
              <div className="h-3 w-16 bg-slate-100 rounded animate-shimmer mt-0.5" />
            </div>
          </div>
        </div>

        {/* Match Level Indicator Badge Skeleton */}
        <div className="mt-6">
          <div className="h-7 w-28 bg-slate-100 rounded-full animate-shimmer" />
        </div>
      </div>
    );
  }
  
  // SVG properties
  const radius = 80;
  const stroke = 12;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6 text-center">
      <div className="relative flex items-center justify-center">
        {/* SVG gauge */}
        <svg height={radius * 2} width={radius * 2} className="transform -rotate-90">
          {/* Background track */}
          <circle
            stroke="rgba(0, 0, 0, 0.04)"
            fill="transparent"
            strokeWidth={stroke}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          {/* Progress circle */}
          <circle
            stroke={theme.color}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={circumference + " " + circumference}
            style={{ strokeDashoffset, transition: "stroke-dashoffset 1s ease-in-out" }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
        </svg>

        {/* Center reading */}
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-3xl md:text-4xl font-extrabold tracking-tighter text-slate-900 font-sans">
            {Math.round(score)}
          </span>
          <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mt-0.5">
            Out of 100
          </span>
        </div>
      </div>

      {/* Match Level Indicator Badge */}
      <div className="mt-6">
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold tracking-wider border uppercase shadow-sm ${theme.bg} ${theme.text} ${theme.border} ${theme.glow}`}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: theme.color }} />
          {theme.label}
        </span>
      </div>
    </div>
  );
};
