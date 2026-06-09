import React from "react";
import { useAnalysis } from "../../stores/analysis-store";
import { COMPONENT_LABELS } from "../../lib/constants";
import { formatScore, formatFractionAsScore } from "../../lib/formatters";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { HelpCircle, Info } from "lucide-react";

interface ComponentBreakdownProps {
  breakdown?: Array<{
    component: string;
    weight: number;
    component_score: number;
    score_achieved: number;
    pct_contribution: number;
    active: boolean;
    reason?: string;
  }>;
  excluded?: Array<{
    component: string;
    reason: string;
  }>;
  loading?: boolean;
}

export const ComponentBreakdown: React.FC<ComponentBreakdownProps> = ({
  breakdown = [],
  excluded = [],
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
        {/* Component cards grid */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4 order-last lg:order-none">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="border border-slate-100 bg-white shadow-sm">
              <CardContent className="p-5 flex flex-col justify-between h-full pt-6">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="h-3.5 w-32 bg-slate-100 rounded animate-shimmer" />
                    <div className="h-5 w-20 bg-slate-100 rounded-lg animate-shimmer" />
                  </div>
                  <div className="h-8 w-16 bg-slate-100 rounded animate-shimmer mt-4" />
                </div>
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between">
                    <div className="h-3 w-20 bg-slate-50 rounded animate-shimmer" />
                    <div className="h-3 w-8 bg-slate-50 rounded animate-shimmer" />
                  </div>
                  <div className="w-full h-1.5 bg-slate-50 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-100 w-1/3 animate-shimmer rounded-full" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Matrix Explanatory Card */}
        <div className="space-y-4 h-full order-first lg:order-none">
          <Card className="border-slate-200 bg-white h-full flex flex-col justify-between shadow-sm">
            <CardHeader className="pb-3">
              <div className="h-4.5 w-40 bg-slate-200 rounded animate-shimmer" />
              <div className="h-3 w-60 bg-slate-100 rounded animate-shimmer mt-2" />
            </CardHeader>
            <CardContent className="space-y-4 flex-1 pb-6">
              <div className="h-3.5 w-full bg-slate-100 rounded animate-shimmer" />
              <div className="h-3.5 w-5/6 bg-slate-100 rounded animate-shimmer" />
              <div className="p-4 bg-slate-50/50 rounded-xl space-y-2.5">
                <div className="h-3 w-28 bg-slate-200 rounded animate-shimmer" />
                <div className="h-3 w-full bg-slate-100 rounded animate-shimmer" />
                <div className="h-3 w-full bg-slate-100 rounded animate-shimmer" />
              </div>
              <div className="h-10 w-full bg-slate-50/50 rounded-xl animate-shimmer" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }
  const getComponentLabel = (code: string) => {
    return COMPONENT_LABELS[code] || code;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 6 MW-ESE Component Cards Grid */}
      <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4 order-last lg:order-none">
        {breakdown.map((comp) => {
          const isExcluded = !comp.active;
          const scoreValue = comp.component_score;
          const progressPercent = Math.round(scoreValue * 100);

          return (
            <Card
              key={comp.component}
              className={`border transition-all duration-300 relative overflow-hidden ${
                isExcluded
                  ? "border-slate-100 bg-slate-50/50 opacity-60"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-md"
              }`}
            >
              {/* Top border color matching state */}
              {!isExcluded && (
                <div 
                  className="absolute top-0 left-0 right-0 h-1 bg-primary/20"
                  style={{ 
                    backgroundImage: `linear-gradient(to right, hsl(var(--primary)) ${progressPercent}%, transparent ${progressPercent}%)` 
                  }}
                />
              )}
              
              <CardContent className="p-5 flex flex-col justify-between h-full pt-6">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-slate-500 block tracking-tight uppercase">
                      {comp.component} · {getComponentLabel(comp.component)}
                    </span>
                    <Badge variant={isExcluded ? "secondary" : "primary"}>
                      {isExcluded ? "Excluded" : `Weight: ${Math.round(comp.weight * 100)}%`}
                    </Badge>
                  </div>

                  <div className="flex items-baseline gap-2 mt-3.5">
                    <span className="text-2xl font-black text-slate-900">
                      {isExcluded ? "--" : formatFractionAsScore(scoreValue)}
                    </span>
                    {!isExcluded && (
                      <span className="text-xs text-slate-400 font-bold uppercase">
                        (contrib: +{formatFractionAsScore(comp.score_achieved)})
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-4">
                  {isExcluded ? (
                    <div className="flex items-start gap-1.5 text-[10px] text-slate-500 bg-slate-50 px-2 py-1.5 rounded-lg border border-slate-100 leading-normal">
                      <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-400" />
                      <span>{comp.reason || "JD constraints deactivated this component."}</span>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        <span>Alignment Progress</span>
                        <span>{progressPercent}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all duration-[800ms] ease-[cubic-bezier(0.16,1,0.3,1)]"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Explanatory Weight Profile Card */}
      <div className="space-y-4 h-full order-first lg:order-none">
        <Card className="border-slate-200 bg-white h-full flex flex-col justify-between shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-primary" /> Scoring Engine Weight Matrix
            </CardTitle>
            <CardDescription className="text-xs">
              How the scoring components are computed and combined.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-slate-600 space-y-3.5 flex-1 pb-6">
            <p className="leading-relaxed font-semibold">
              We leverage an adaptive **Multi-Weighted Empirical Scoring Engine (MW-ESE)**. 
              The profile is dynamically resolved based on the JD domain.
            </p>

            <div className="bg-slate-50/50 p-3 rounded-xl border border-slate-100 space-y-2 text-[10px] leading-relaxed">
              <span className="font-bold text-slate-700 block mb-1 uppercase tracking-wider">Adaptive Redistribution Rules:</span>
              <div className="flex gap-2">
                <span className="text-primary font-black">•</span>
                <span>**Work Experience (S_we)** and **Academics (S_ac)** are auto-deactivated if the JD rules do not explicitly mandate them.</span>
              </div>
              <div className="flex gap-2">
                <span className="text-primary font-black">•</span>
                <span>**Achievements (S_ah)** auto-deactivates dynamically if both credentials and hackathons are empty, redistributing weight to active components.</span>
              </div>
            </div>

            {excluded.length > 0 ? (
              <div className="border border-primary/10 bg-primary/5 p-3 rounded-xl space-y-1.5">
                <span className="font-bold text-primary block text-[10px] tracking-wide uppercase">
                  Deactivated and Redistributed Components:
                </span>
                <div className="space-y-1 text-[10px]">
                  {excluded.map((item, idx) => (
                    <div key={idx} className="flex justify-between font-bold text-slate-700">
                      <span>{getComponentLabel(item.component)}</span>
                      <span className="text-primary">{item.reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="border border-slate-100 bg-slate-50/30 p-3 rounded-xl text-center text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                All 6 scoring dimensions are active for this candidate.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
