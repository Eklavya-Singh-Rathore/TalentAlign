import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { CheckCircle2, AlertTriangle, Sparkles, ArrowRight } from "lucide-react";
import { AnalysisPayload } from "../../lib/types";

interface CandidateAssessmentProps {
  analysis?: AnalysisPayload;
  loading?: boolean;
}

export const CandidateAssessment: React.FC<CandidateAssessmentProps> = ({
  analysis,
  loading = false,
}) => {
  if (loading) {
    return (
      <Card className="border-slate-200 bg-white shadow-sm overflow-hidden animate-fade-in">
        <CardHeader className="pb-3 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="space-y-1.5 flex-1">
            <div className="h-4.5 w-36 bg-slate-200 rounded animate-shimmer" />
            <div className="h-3 w-64 bg-slate-100 rounded animate-shimmer mt-2" />
          </div>
          <div className="h-5 w-20 bg-slate-100 rounded-xl animate-shimmer flex-shrink-0" />
        </CardHeader>
        
        <CardContent className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-5">
              {/* Overall Evaluation */}
              <div className="space-y-1.5">
                <div className="h-3 w-28 bg-slate-200 rounded animate-shimmer" />
                <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl space-y-2">
                  <div className="h-3.5 w-full bg-slate-100 rounded animate-shimmer" />
                  <div className="h-3.5 w-5/6 bg-slate-100 rounded animate-shimmer" />
                  <div className="h-3.5 w-4/5 bg-slate-100 rounded animate-shimmer" />
                </div>
              </div>

              {/* Strengths & Gaps Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-3">
                  <div className="h-3.5 w-24 bg-slate-200 rounded animate-shimmer" />
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex gap-2">
                        <div className="h-3.5 w-3 bg-slate-100 rounded-full animate-shimmer flex-shrink-0 mt-0.5" />
                        <div className="h-3.5 w-full bg-slate-100 rounded animate-shimmer" />
                      </div>
                    ))}
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="h-3.5 w-24 bg-slate-200 rounded animate-shimmer" />
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex gap-2">
                        <div className="h-3.5 w-3 bg-slate-100 rounded-full animate-shimmer flex-shrink-0 mt-0.5" />
                        <div className="h-3.5 w-full bg-slate-100 rounded animate-shimmer" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-2 pt-5 border-t border-slate-100 lg:pt-0 lg:border-t-0 lg:border-l lg:border-slate-100 lg:pl-6">
              <div className="space-y-3">
                <div className="h-3 w-28 bg-slate-200 rounded animate-shimmer" />
                <div className="p-4 border border-slate-100 rounded-xl space-y-4 bg-slate-50/20">
                  <div className="flex items-center justify-between gap-2">
                    <div className="h-4 w-24 bg-slate-200 rounded animate-shimmer" />
                    <div className="h-4.5 w-16 bg-slate-100 rounded animate-shimmer" />
                  </div>
                  <div className="space-y-2">
                    <div className="h-3 w-full bg-slate-100 rounded animate-shimmer" />
                    <div className="h-3 w-5/6 bg-slate-100 rounded animate-shimmer" />
                    <div className="h-3 w-4/5 bg-slate-100 rounded animate-shimmer" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { final_summary, placement_score = 0, match_level = "POOR" } = analysis || {};

  // Retrieve LLM narrative fields
  const overallEvaluation = final_summary?.overall_assessment || `${match_level} fit alignment (${placement_score}%).`;
  const strengths = final_summary?.strengths || [];
  const improvementAreas = final_summary?.weaknesses || [];

  // Generate dynamic hiring recommendation based on score and match level
  const getHiringRecommendation = (score: number, level: string) => {
    const lvl = level.toUpperCase();
    if (score >= 85 || lvl === "EXCELLENT") {
      return {
        decision: "Strongly Recommend",
        colorClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
        badgeVariant: "success" as const,
        description: "Proceed to final technical interviews and team matching. The candidate displays top-tier semantic compatibility, comprehensive skill alignment, and strong evidence of role-relevant project execution."
      };
    } else if (score >= 70 || lvl === "GOOD") {
      return {
        decision: "Recommend",
        colorClass: "bg-indigo-50 text-indigo-800 border-indigo-200",
        badgeVariant: "primary" as const,
        description: "Proceed to technical screening. The candidate has solid fundamental alignment with minor skill gaps that can be easily addressed during onboarding or focused training."
      };
    } else if (score >= 50 || lvl === "MODERATE") {
      return {
        decision: "Recommend with Reservations",
        colorClass: "bg-amber-50 text-amber-800 border-amber-200",
        badgeVariant: "warning" as const,
        description: "Consider for introductory screening. The candidate meets basic requirements but has notable gaps in key experience or skill categories. Focused evaluation on missing skills is recommended."
      };
    } else {
      return {
        decision: "Hold / Do Not Proceed",
        colorClass: "bg-red-50 text-red-800 border-red-200",
        badgeVariant: "danger" as const,
        description: "Hold application. The candidate's technical profile shows substantial misalignment relative to the target role requirements. Review other profiles or consider secondary roles."
      };
    }
  };

  const recommendation = getHiringRecommendation(placement_score, match_level);

  return (
    <Card className="border-slate-200 bg-white shadow-sm overflow-hidden">
      <CardHeader className="pb-3 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" /> Candidate Assessment
          </CardTitle>
          <CardDescription className="text-xs">
            Deep semantic alignment analysis and fit recommendations powered by generative AI.
          </CardDescription>
        </div>
        <div className="flex items-center gap-1.5 self-start sm:self-center">
          <Badge variant="primary" className="text-[9px] uppercase tracking-wider font-extrabold px-2 py-0.5 bg-primary/10 text-primary border-primary/20">
            AI Enriched
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Evaluation, Strengths & Gaps (Col-span 2) */}
          <div className="lg:col-span-2 space-y-5">
            {/* Overall Evaluation */}
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Overall Evaluation
              </h4>
              <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl text-slate-700 text-xs leading-relaxed font-medium">
                {overallEvaluation}
              </div>
            </div>

            {/* Strengths & Gaps Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {/* Strengths */}
              <div className="space-y-2">
                <span className="font-bold text-emerald-700 block tracking-wider uppercase text-[9px] flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Core Strengths
                </span>
                {strengths.length > 0 ? (
                  <ul className="space-y-1.5 pl-0.5">
                    {strengths.map((s, i) => (
                      <li key={i} className="flex gap-2 text-slate-600 text-xs font-medium leading-relaxed">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-400 italic">No explicit strengths compiled.</p>
                )}
              </div>

              {/* Gaps */}
              <div className="space-y-2">
                <span className="font-bold text-amber-700 block tracking-wider uppercase text-[9px] flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" /> Highlighted Gaps
                </span>
                {improvementAreas.length > 0 ? (
                  <ul className="space-y-1.5 pl-0.5">
                    {improvementAreas.map((w, i) => (
                      <li key={i} className="flex gap-2 text-slate-600 text-xs font-medium leading-relaxed">
                        <span className="text-amber-500 font-bold">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-400 italic">No explicit gaps compiled.</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2 pt-5 border-t border-slate-100 lg:pt-0 lg:border-t-0 lg:border-l lg:border-slate-100 lg:pl-6">
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Hiring Recommendation
              </h4>
              
              <div className={`p-4 border rounded-xl space-y-3 ${recommendation.colorClass}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-black text-xs uppercase tracking-wide">
                    {recommendation.decision}
                  </span>
                  <Badge variant={recommendation.badgeVariant} className="text-[9px] font-extrabold uppercase px-1.5">
                    {placement_score}% Match
                  </Badge>
                </div>
                <p className="text-slate-600 text-[11px] leading-relaxed font-medium">
                  {recommendation.description}
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
