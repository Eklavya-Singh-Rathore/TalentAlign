import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { AlertCircle, HelpCircle, ArrowUpRight, TrendingUp, CheckCircle, Ban } from "lucide-react";

interface GapItem {
  gap_item: string;
  component: string;
  impact_pct: number;
  severity: "high" | "medium" | "low";
}

interface GapAnalysisProps {
  rankedGaps?: GapItem[];
  totalRecoverablePct?: number;
  missingSkills?: string[];
  certificationsPresent?: string[];
  emptySections?: string[];
  loading?: boolean;
}

export const GapAnalysis: React.FC<GapAnalysisProps> = ({
  rankedGaps = [],
  totalRecoverablePct = 0,
  missingSkills = [],
  certificationsPresent = [],
  emptySections = [],
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        {/* Recovery Potential Header Card Skeleton */}
        <Card className="border-slate-200 bg-slate-50/50 shadow-sm">
          <CardContent className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="h-5 w-48 bg-slate-200 rounded animate-shimmer" />
              <div className="h-3.5 w-3/4 bg-slate-100 rounded animate-shimmer" />
            </div>
            <div className="bg-slate-100/80 border border-slate-200 px-5 py-3 rounded-2xl h-16 w-[140px] flex flex-col justify-center items-center animate-shimmer shadow-[0_2px_8px_rgba(0,0,0,0.01)] flex-shrink-0">
              <div className="h-6 w-12 bg-slate-200 rounded animate-shimmer mx-auto" />
            </div>
          </CardContent>
        </Card>

        {/* Grid of Gap Categories Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Missing Core Skills Skeleton */}
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100">
              <div className="flex justify-between items-center">
                <div className="h-4.5 w-32 bg-slate-200 rounded animate-shimmer" />
                <div className="h-5 w-20 bg-slate-100 rounded animate-shimmer" />
              </div>
              <div className="h-3 w-4/5 bg-slate-100 rounded animate-shimmer mt-2" />
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-100">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="px-5 py-3.5 flex items-center justify-between gap-4">
                    <div className="h-4 w-24 bg-slate-100 rounded animate-shimmer" />
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="h-5 w-20 bg-slate-100 rounded animate-shimmer" />
                      <div className="h-4 w-8 bg-slate-100 rounded animate-shimmer" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Experience Gaps Skeleton */}
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100">
              <div className="flex justify-between items-center">
                <div className="h-4.5 w-28 bg-slate-200 rounded animate-shimmer" />
                <div className="h-5 w-20 bg-slate-100 rounded animate-shimmer" />
              </div>
              <div className="h-3 w-4/5 bg-slate-100 rounded animate-shimmer mt-2" />
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-100">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="px-5 py-3.5 flex items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1">
                      <div className="h-4 w-36 bg-slate-100 rounded animate-shimmer" />
                      <div className="h-3 w-48 bg-slate-50 rounded animate-shimmer" />
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="h-5 w-24 bg-slate-100 rounded animate-shimmer" />
                      <div className="h-4 w-8 bg-slate-100 rounded animate-shimmer" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }
  // Categorize gaps
  const getGapsByComponent = (componentPrefix: string) => {
    return rankedGaps.filter((g) => g.component.startsWith(componentPrefix));
  };

  const skillGaps = rankedGaps.filter(
    (g) => g.component === "S_sk" || (g.gap_item && missingSkills.includes(g.gap_item))
  );
  
  const experienceGaps = rankedGaps.filter(
    (g) => g.component === "S_we" || g.component === "S_in"
  );
  
  const certificationGaps = rankedGaps.filter(
    (g) => g.component === "S_ah" && g.gap_item && g.gap_item.toLowerCase().includes("cert")
  );

  const otherGaps = rankedGaps.filter(
    (g) => 
      !skillGaps.includes(g) && 
      !experienceGaps.includes(g) && 
      !certificationGaps.includes(g)
  );

  const getSeverityVariant = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "high":
        return "danger";
      case "medium":
        return "warning";
      default:
        return "secondary";
    }
  };

  return (
    <div className="space-y-6">
      {/* Recovery Potential Header Card */}
      <Card className="border-primary/10 bg-primary/5 shadow-sm">
        <CardContent className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-md font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" /> Recoverable Match Potential
            </h3>
            <p className="text-xs text-slate-500 font-semibold max-w-xl">
              By acquiring or addressing the highlighted gap areas below, the scoring simulation projects a total potential uplift to your placement alignment score.
            </p>
          </div>
          <div className="bg-primary/10 border border-primary/20 px-5 py-3 rounded-2xl text-center self-stretch sm:self-auto flex flex-col justify-center min-w-[140px] shadow-[0_2px_8px_rgba(79,125,243,0.05)]">
            <span className="text-2xl font-black text-primary">
              +{Math.round(totalRecoverablePct)}%
            </span>
            <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mt-0.5">
              Potential Uplift
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Grid of Gap Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category 1: Missing Core Skills */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="flex justify-between items-center">
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Ban className="w-4 h-4 text-red-500" /> Missing Core Skills
              </CardTitle>
              <Badge variant="danger">{missingSkills.length} Skills Gaps</Badge>
            </div>
            <CardDescription className="text-[10px]">
              Skills identified in the Job Description requirements that were not found in the resume parsing layer.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[350px] overflow-y-auto divide-y divide-slate-100">
              {missingSkills.length > 0 ? (
                missingSkills.filter(Boolean).map((skill, i) => {
                  // Find associated impact if in rankedGaps
                  const gapMatch = rankedGaps.find(
                    (g) => g.gap_item && skill && g.gap_item.toLowerCase() === skill.toLowerCase()
                  );
                  const impact = gapMatch ? gapMatch.impact_pct : 1.5; // default estimation
                  const severity = gapMatch ? gapMatch.severity : "medium";

                  return (
                    <div key={i} className="px-5 py-3.5 flex items-center justify-between gap-4 flex-wrap hover:bg-slate-50/50 transition-colors">
                      <span className="text-xs font-semibold text-slate-800 capitalize min-w-0 truncate" title={skill}>{skill}</span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge variant={getSeverityVariant(severity)}>
                          {severity} Impact
                        </Badge>
                        <span className="text-xs font-black text-primary">
                          +{impact.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-6 text-center text-slate-400 text-xs font-semibold">
                  <CheckCircle className="w-8 h-8 text-emerald-500/20 mx-auto mb-2" />
                  No missing skills detected! High core skill coverage.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Category 2: Experience Depth & Sections */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="flex justify-between items-center">
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-500" /> Experience Gaps
              </CardTitle>
              <Badge variant="warning">{emptySections.length + experienceGaps.length} Areas</Badge>
            </div>
            <CardDescription className="text-[10px]">
              Missing resume sections or duration shortcomings compared against the target profile seniority constraints.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[350px] overflow-y-auto divide-y divide-slate-100">
              {/* Empty Sections */}
              {emptySections.map((sect, i) => (
                <div key={`sect-${i}`} className="px-5 py-3.5 flex items-center justify-between gap-4 flex-wrap hover:bg-slate-50/50 transition-colors">
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-semibold text-slate-800 capitalize truncate">
                      Missing {sect.replace("_", " ")} Block
                    </span>
                    <span className="text-[10px] text-slate-400 font-semibold mt-0.5 truncate">
                      Empty section detected in resume parsing.
                    </span>
                  </div>
                  <Badge variant="warning" className="flex-shrink-0">Structure Gap</Badge>
                </div>
              ))}

              {/* Experience Gaps */}
              {experienceGaps.map((gap, i) => (
                <div key={`exp-${i}`} className="px-5 py-3.5 flex items-center justify-between gap-4 flex-wrap hover:bg-slate-50/50 transition-colors">
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-semibold text-slate-800 capitalize truncate" title={gap.gap_item.replace("_", " ")}>
                      {gap.gap_item.replace("_", " ")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-semibold mt-0.5 truncate">
                      Component score: S_we/S_in below maximum weight.
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant={getSeverityVariant(gap.severity)}>
                      {gap.severity} Severity
                    </Badge>
                    <span className="text-xs font-black text-primary">
                      +{Math.round(gap.impact_pct)}%
                    </span>
                  </div>
                </div>
              ))}

              {emptySections.length === 0 && experienceGaps.length === 0 && (
                <div className="p-6 text-center text-slate-400 text-xs font-semibold">
                  <CheckCircle className="w-8 h-8 text-emerald-500/20 mx-auto mb-2" />
                  All experience requirements and parsing sections are fully populated.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
