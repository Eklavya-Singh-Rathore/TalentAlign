import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Lightbulb, TrendingUp, Play, CheckCircle2, Award, FileSpreadsheet, FolderGit } from "lucide-react";
import { cleanRecommendation, formatLabel } from "../../lib/formatters";

interface SimulationItem {
  rank: number;
  improvement: string;
  current_score: number;
  predicted_score: number;
  delta_gain: number;
}

interface RecommendationsProps {
  suggestions?: SimulationItem[];
  combinedImprovement?: {
    current_score?: number;
    new_score?: number;
    delta?: number;
    applied_improvements?: string[];
  };
  recommendations?: Record<string, string[]> | string[] | null | undefined;
  loading?: boolean;
}

// Normalize: backend may return a flat string[] or a Record<string, string[]>
function normalizeRecommendations(raw: Record<string, string[]> | string[] | null | undefined): Record<string, string[]> {
  if (!raw) return { general: [] };
  if (Array.isArray(raw)) {
    return raw.length > 0 ? { general: raw } : { general: [] };
  }
  // It's already an object — but values could be strings instead of arrays (edge case)
  const normalized: Record<string, string[]> = {};
  for (const [key, val] of Object.entries(raw)) {
    if (Array.isArray(val)) {
      normalized[key] = val;
    } else if (typeof val === "string") {
      normalized[key] = [val];
    } else {
      normalized[key] = [];
    }
  }
  return Object.keys(normalized).length > 0 ? normalized : { general: [] };
}

export const Recommendations: React.FC<RecommendationsProps> = ({
  suggestions = [],
  combinedImprovement = {},
  recommendations: rawRecommendations = {},
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        {/* Simulation Engine Panel Skeleton */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3">
            <div className="h-4.5 w-48 bg-slate-200 rounded animate-shimmer" />
            <div className="h-3 w-64 bg-slate-100 rounded animate-shimmer mt-2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {[...Array(4)].map((_, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between gap-4 p-3.5 bg-slate-50/40 border border-slate-100 rounded-xl"
                >
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <div className="h-6 w-6 rounded-lg bg-slate-100 animate-shimmer flex-shrink-0 mt-0.5" />
                    <div className="min-w-0 space-y-1.5 flex-1">
                      <div className="h-3.5 w-1/3 bg-slate-100 rounded animate-shimmer" />
                      <div className="h-3 w-1/2 bg-slate-50 rounded animate-shimmer" />
                    </div>
                  </div>
                  <div className="h-6 w-16 bg-slate-100 rounded-lg animate-shimmer flex-shrink-0" />
                </div>
              ))}
            </div>

            {/* Combined Impact Simulation Skeleton */}
            <div className="border border-slate-100 bg-slate-50/50 p-4 rounded-xl space-y-3">
              <div className="h-3.5 w-48 bg-slate-200 rounded animate-shimmer" />
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white border border-slate-100 p-3 rounded-lg">
                <div className="space-y-1.5">
                  <div className="h-3 w-32 bg-slate-100 rounded animate-shimmer" />
                  <div className="h-3 w-56 bg-slate-50 rounded animate-shimmer" />
                </div>
                <div className="h-6 w-24 bg-slate-100 rounded animate-shimmer flex-shrink-0 self-end sm:self-auto" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actionable Category Guides Skeleton */}
        <Card className="border-slate-200 bg-white flex flex-col shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="h-4.5 w-36 bg-slate-200 rounded animate-shimmer" />
            <div className="h-3 w-64 bg-slate-100 rounded animate-shimmer mt-2" />
          </CardHeader>
          <CardContent className="p-0 flex flex-col">
            {/* Horizontal Tabs List Skeleton */}
            <div className="flex border-b border-slate-100 bg-slate-50/50 px-2 py-1.5 gap-2 overflow-x-auto">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-7 w-20 bg-slate-100 rounded-lg animate-shimmer flex-shrink-0" />
              ))}
            </div>

            {/* List Skeleton */}
            <div className="p-4 space-y-2.5">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex gap-2.5 bg-slate-50/50 p-3 rounded-lg border border-slate-100/80">
                  <div className="w-4 h-4 bg-slate-100 rounded-full animate-shimmer flex-shrink-0 mt-0.5" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-3 w-full bg-slate-100 rounded animate-shimmer" />
                    <div className="h-3 w-4/5 bg-slate-100 rounded animate-shimmer" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const recommendations = normalizeRecommendations(rawRecommendations);
  const [selectedCategory, setSelectedCategory] = useState<string>(
    Object.keys(recommendations)[0] || "general"
  );

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case "projects":
        return FolderGit;
      case "achievements":
      case "certifications":
        return Award;
      case "academics":
        return FileSpreadsheet;
      default:
        return Lightbulb;
    }
  };  return (
    <div className="space-y-6">
      {/* Simulation Engine Panel */}
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" /> What-If Alignment Simulations
          </CardTitle>
          <CardDescription className="text-xs">
            Simulated predictions of score increases when specific skills or experiences are added.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {suggestions && suggestions.length > 0 ? (
            <div className="space-y-3">
              {suggestions.slice(0, 5).map((s) => (
                <div
                  key={s.rank}
                  className="flex items-center justify-between gap-4 flex-wrap p-3.5 bg-slate-50/40 border border-slate-100 rounded-xl hover:border-slate-200 hover:bg-slate-50 transition-all group"
                >
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <span className="h-6 w-6 rounded-lg bg-primary/10 border border-primary/20 text-primary flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5 group-hover:bg-primary group-hover:text-white transition-all shadow-[0_2px_6px_rgba(79,125,243,0.05)]">
                      {s.rank}
                    </span>
                    <div className="min-w-0">
                      <span className="text-xs font-semibold text-slate-800 block capitalize truncate leading-normal" title={s.improvement}>
                        {cleanRecommendation(s.improvement)}
                      </span>
                      <span className="text-[10px] text-slate-400 font-semibold block mt-0.5 truncate">
                        Simulated score delta: from {Math.round(s.current_score)} to {Math.round(s.predicted_score)}
                      </span>
                    </div>
                  </div>
                  
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2.5 py-1 rounded-lg flex-shrink-0 shadow-[0_2px_8px_rgba(22,163,74,0.02)] self-end sm:self-center">
                    +{s.delta_gain.toFixed(1)} Pts
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center p-8 text-slate-400 text-xs font-semibold">
              No simulations available.
            </div>
          )}

          {/* Combined Impact Simulation */}
          {combinedImprovement && combinedImprovement.delta !== undefined && (
            <div className="border border-primary/10 bg-primary/5 p-4 rounded-xl space-y-3 shadow-[0_2px_8px_rgba(79,125,243,0.02)]">
              <span className="font-bold text-primary text-xs block uppercase tracking-wider">
                Top-3 Combined Uplift Simulation:
              </span>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white/60 p-3 rounded-lg border border-slate-100">
                <div className="space-y-0.5">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    Target Score Potential
                  </span>
                  <span className="text-xs text-slate-600 font-semibold">
                    Simulate applying the top 3 recommendations in parallel.
                  </span>
                </div>
                <div className="flex items-baseline gap-1.5 self-end sm:self-auto">
                  <span className="text-slate-400 text-xs line-through font-semibold">
                    {Math.round(combinedImprovement.current_score || 0)}
                  </span>
                  <span className="text-slate-500 text-md font-bold">&rarr;</span>
                  <span className="text-emerald-600 text-lg font-black">
                    {Math.round(combinedImprovement.new_score || 0)}%
                  </span>
                  <span className="text-xs font-bold text-emerald-600 ml-1">
                    (+{Math.round(combinedImprovement.delta)}%)
                  </span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actionable Category Guides */}
      <Card className="border-slate-200 bg-white flex flex-col shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-100">
          <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary" /> Actionable Guidelines
          </CardTitle>
          <CardDescription className="text-xs">
            Concrete structural updates grouped by section blocks.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 flex flex-col">
          {/* Horizontal Tabs List */}
          <div className="flex border-b border-slate-100 overflow-x-auto bg-slate-50/50 px-2 py-1.5 scrollbar-thin">
            {Object.keys(recommendations).map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-lg border border-transparent whitespace-nowrap transition-colors ${
                    isSelected
                      ? "bg-white border-slate-200 text-primary shadow-[0_2px_6px_rgba(0,0,0,0.02)]"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {formatLabel(cat)}
                </button>
              );
            })}
          </div>

          {/* List */}
          <div className="p-4 overflow-y-auto max-h-[350px] space-y-2.5">
            {recommendations[selectedCategory] && recommendations[selectedCategory].length > 0 ? (
              recommendations[selectedCategory].map((rec, i) => {
                const CategoryIcon = getCategoryIcon(selectedCategory);
                return (
                  <div key={i} className="flex gap-2.5 bg-slate-50/50 p-3 rounded-lg border border-slate-100/80">
                    <CategoryIcon className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    <p className="text-[11px] leading-relaxed text-slate-600 font-semibold">
                      {cleanRecommendation(rec)}
                    </p>
                  </div>
                );
              })
            ) : (
              <div className="flex flex-col items-center justify-center text-center text-slate-400 text-xs py-8">
                <CheckCircle2 className="w-8 h-8 text-emerald-500/20 mb-2 animate-pulse" />
                No urgent improvements needed for this section.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
