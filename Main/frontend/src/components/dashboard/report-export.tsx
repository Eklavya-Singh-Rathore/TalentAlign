"use client";

import React, { useRef } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  FileDown,
  Printer,
  FileJson,
  BarChart4,
  CheckCircle,
  TrendingUp,
  Lightbulb,
  Briefcase,
} from "lucide-react";
import { formatScore, formatExperience, cleanRecommendation } from "../../lib/formatters";
import { COMPONENT_LABELS } from "../../lib/constants";
import type { AnalysisPayload } from "../../lib/types";

interface ReportExportProps {
  analysis?: AnalysisPayload;
  loading?: boolean;
}

export const ReportExport: React.FC<ReportExportProps> = ({ analysis, loading = false }) => {
  const reportRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    window.print();
  };

  const handleExportJSON = () => {
    if (!analysis) return;
    const blob = new Blob([JSON.stringify(analysis, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `talentalign-report-${analysis.role_title || "analysis"}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getMatchLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "EXCELLENT":
        return "text-emerald-700 border-emerald-200 bg-emerald-50";
      case "GOOD":
        return "text-green-700 border-green-200 bg-green-50";
      case "MODERATE":
        return "text-amber-700 border-amber-200 bg-amber-50";
      case "BELOW AVERAGE":
        return "text-orange-700 border-orange-200 bg-orange-50";
      default:
        return "text-red-700 border-red-200 bg-red-50";
    }
  };

  if (loading || !analysis) {
    return (
      <div className="space-y-6 animate-fade-in">
        {/* Export Actions Bar Skeleton */}
        <Card className="border-slate-100 bg-slate-50/50 shadow-sm print-hide">
          <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1.5 flex-1">
              <div className="h-4.5 w-32 bg-slate-200 rounded animate-shimmer" />
              <div className="h-3 w-64 bg-slate-100 rounded animate-shimmer" />
            </div>
            <div className="flex gap-3 flex-shrink-0">
              <div className="h-9 w-24 bg-slate-100 rounded-lg animate-shimmer" />
              <div className="h-9 w-24 bg-slate-100 rounded-lg animate-shimmer" />
            </div>
          </CardContent>
        </Card>

        {/* Executive Summary Skeleton */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="h-4.5 w-32 bg-slate-200 rounded animate-shimmer" />
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-slate-50/50 border border-slate-100 rounded-2xl p-4 flex flex-col justify-between items-center text-center h-20">
                  <div className="h-3 w-16 bg-slate-100 rounded animate-shimmer" />
                  <div className="h-5 w-12 bg-slate-100 rounded animate-shimmer mt-2" />
                </div>
              ))}
            </div>
            <div className="bg-slate-50/30 border border-slate-100 rounded-2xl p-4 space-y-2">
              <div className="h-3 w-28 bg-slate-200 rounded animate-shimmer mb-1" />
              <div className="h-3 w-full bg-slate-100 rounded animate-shimmer" />
              <div className="h-3 w-5/6 bg-slate-100 rounded animate-shimmer" />
            </div>
          </CardContent>
        </Card>

        {/* Experience Intelligence Skeleton */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="h-4.5 w-40 bg-slate-200 rounded animate-shimmer" />
          </CardHeader>
          <CardContent className="p-5">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3 flex flex-col justify-between h-14">
                  <div className="h-3 w-16 bg-slate-100 rounded animate-shimmer" />
                  <div className="h-4.5 w-20 bg-slate-100 rounded animate-shimmer mt-1" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Component Breakdown Table Skeleton */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <div className="h-4.5 w-36 bg-slate-200 rounded animate-shimmer" />
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto w-full">
              <div className="divide-y divide-slate-100 min-w-[600px]">
                {/* Header */}
                <div className="grid grid-cols-5 gap-2 px-5 py-2.5 bg-slate-50/50">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-3.5 w-16 bg-slate-100 rounded animate-shimmer mx-auto first:ml-0" />
                  ))}
                </div>
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="grid grid-cols-5 gap-2 px-5 py-3 items-center">
                    <div className="h-4 w-24 bg-slate-100 rounded animate-shimmer" />
                    <div className="h-4 w-8 bg-slate-100 rounded animate-shimmer mx-auto" />
                    <div className="h-4 w-10 bg-slate-100 rounded animate-shimmer mx-auto" />
                    <div className="h-4 w-12 bg-slate-100 rounded animate-shimmer mx-auto" />
                    <div className="h-5 w-16 bg-slate-100 rounded animate-shimmer mx-auto" />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const recommendations = Array.isArray(analysis.recommendations)
    ? analysis.recommendations
    : Object.values(analysis.recommendations || {}).flat();

  return (
    <div className="space-y-6">
      {/* Export Actions Bar — hidden during print */}
      <Card className="border-primary/10 bg-primary/5 shadow-sm print-hide">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-md font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <FileDown className="w-5 h-5 text-primary" /> Report & Export
            </h3>
            <p className="text-xs text-slate-500 font-semibold">
              Full analysis report with all scoring metrics and recommendations.
            </p>
          </div>
          <div className="flex gap-3">
            <Button onClick={handlePrint} variant="outline" className="gap-2 text-xs">
              <Printer className="w-3.5 h-3.5" /> Print / PDF
            </Button>
            <Button onClick={handleExportJSON} variant="outline" className="gap-2 text-xs">
              <FileJson className="w-3.5 h-3.5" /> Export JSON
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Printable Report Content */}
      <div ref={reportRef} id="print-report" className="space-y-6 print-report">

        {/* Print-Only: Report Header */}
        <div className="print-only-header">
          <h1 className="text-xl font-black text-slate-900 tracking-tight">TalentAlign — Candidate Analysis Report</h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Generated {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
            {" · "}Weight Profile: {analysis.weight_profile_used} · Seniority: {analysis.seniority_level}
          </p>
        </div>

        {/* Section 1: Executive Summary */}
        <Card className="report-section border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BarChart4 className="w-4 h-4 text-primary" /> Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Score */}
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Match Score
                </span>
                <span className="text-2xl font-black text-primary block mt-1">
                  {formatScore(analysis.placement_score)}
                </span>
              </div>
              {/* Match Level */}
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Match Level
                </span>
                <span className={`text-xs font-bold block mt-2 border rounded-xl py-1 px-2 ${getMatchLevelColor(analysis.match_level)}`}>
                  {analysis.match_level}
                </span>
              </div>
              {/* Role */}
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Target Role
                </span>
                <span className="text-xs font-bold text-slate-800 block mt-2 capitalize truncate">
                  {analysis.role_title === "not_specified" ? "General" : analysis.role_title}
                </span>
              </div>
              {/* Domain */}
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Domain
                </span>
                <span className="text-xs font-bold text-slate-800 block mt-2 capitalize truncate">
                  {analysis.domain_detected?.replace(/_/g, " ") || "General"}
                </span>
              </div>
            </div>

            {/* Overall Assessment */}
            {analysis.final_summary?.overall_assessment && (
              <div className="bg-slate-50/30 border border-slate-100 rounded-2xl p-4">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2">
                  Overall Assessment
                </span>
                <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                  {analysis.final_summary.overall_assessment}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 2: Experience Intelligence */}
        <Card className="report-section border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-primary" /> Experience Intelligence
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Category
                </span>
                <span className="text-xs font-bold text-slate-800 mt-1 block capitalize">
                  {analysis.experience_intelligence?.candidate_category || "Unknown"}
                </span>
              </div>
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Total Experience
                </span>
                <span className="text-xs font-bold text-slate-800 mt-1 block">
                  {formatExperience(analysis.experience_intelligence?.total_experience_months)}
                </span>
              </div>
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Meets JD Requirement
                </span>
                <span className="mt-1 block">
                  {analysis.experience_intelligence?.experience_meets_jd_requirement ? (
                    <Badge variant="success">Yes</Badge>
                  ) : (
                    <Badge variant="danger">No</Badge>
                  )}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 3: Component Breakdown */}
        <Card className="report-section border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BarChart4 className="w-4 h-4 text-primary" /> Component Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto w-full">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50/50 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 print:border-slate-200">
                    <th className="px-5 py-2.5">Component</th>
                    <th className="px-5 py-2.5 text-center">Weight</th>
                    <th className="px-5 py-2.5 text-center">Score</th>
                    <th className="px-5 py-2.5 text-center">Contribution</th>
                    <th className="px-5 py-2.5 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 print:divide-slate-200 text-slate-700 font-semibold">
                  {analysis.component_breakdown?.map((comp, i) => (
                    <tr
                      key={i}
                      className={comp.active ? "" : "opacity-45"}
                    >
                      <td className="px-5 py-3 text-slate-900 font-bold">
                        {comp.component} · {COMPONENT_LABELS[comp.component] || comp.component}
                      </td>
                      <td className="px-5 py-3 text-center font-mono text-slate-500 font-bold">
                        {(comp.weight * 100).toFixed(0)}%
                      </td>
                      <td className="px-5 py-3 text-center text-slate-800 font-bold">
                        {comp.active ? comp.component_score.toFixed(2) : "--"}
                      </td>
                      <td className="px-5 py-3 text-center text-primary font-bold">
                        {comp.active ? `${comp.pct_contribution.toFixed(1)}%` : "--"}
                      </td>
                      <td className="px-5 py-3 text-center">
                        <div className="flex justify-center">
                          {comp.active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Excluded</Badge>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Section 4: Skills Analysis */}
        <Card className="report-section border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600" /> Skills Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  JD Skills
                </span>
                <span className="text-lg font-black text-slate-800 block mt-1">
                  {analysis.skills_analysis?.total_jd_skills || 0}
                </span>
              </div>
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Matched
                </span>
                <span className="text-lg font-black text-emerald-600 block mt-1">
                  {analysis.skills_analysis?.matched_count || 0}
                </span>
              </div>
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Coverage
                </span>
                <span className="text-lg font-black text-primary block mt-1">
                  {formatScore(analysis.skills_analysis?.skill_coverage_pct)}
                </span>
              </div>
              <div className="bg-slate-50/50 border border-slate-100 rounded-2xl p-3 text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                  Missing
                </span>
                <span className="text-lg font-black text-red-600 block mt-1">
                  {analysis.skills_analysis?.missing_skills?.length || 0}
                </span>
              </div>
            </div>

            {/* Missing Skills List */}
            {analysis.skills_analysis?.missing_skills && analysis.skills_analysis.missing_skills.length > 0 && (
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2">
                  Missing Skills
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {analysis.skills_analysis.missing_skills.filter(Boolean).map((skill, i) => (
                    <Badge key={i} variant="danger">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 5: Core Strengths */}
        {analysis.final_summary?.strengths && analysis.final_summary.strengths.length > 0 && (
          <Card className="report-section border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100">
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Core Strengths
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-100">
                {analysis.final_summary.strengths.map((str, i) => (
                  <div key={i} className="px-5 py-3.5 flex items-start gap-3">
                    <span className="h-5 w-5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">
                      ✓
                    </span>
                    <p className="text-xs text-slate-600 font-semibold leading-relaxed">
                      {str}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Section 6: Recommendations */}
        <Card className="report-section border-slate-200 bg-white shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-primary" /> Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {recommendations.length > 0 ? (
                recommendations.map((rec, i) => (
                  <div key={i} className="px-5 py-3.5 flex items-start gap-3">
                    <span className="h-5 w-5 rounded-md bg-primary/10 border border-primary/20 text-primary flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-xs text-slate-600 font-semibold leading-relaxed">
                      {typeof rec === "string" ? cleanRecommendation(rec) : JSON.stringify(rec)}
                    </p>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-slate-400 text-xs font-semibold">
                  <CheckCircle className="w-8 h-8 text-emerald-500/20 mx-auto mb-2" />
                  No specific recommendations generated.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Section 7: Score Improvement Simulations */}
        {analysis.improvement_suggestions && analysis.improvement_suggestions.length > 0 && (
          <Card className="report-section border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100">
              <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-650" /> Score Improvement Simulations
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto w-full">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50/50 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 print:border-slate-200">
                      <th className="px-5 py-2.5">Improvement</th>
                      <th className="px-5 py-2.5 text-center">Current</th>
                      <th className="px-5 py-2.5 text-center">Predicted</th>
                      <th className="px-5 py-2.5 text-center">Gain</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 print:divide-slate-200 text-slate-700 font-semibold">
                    {analysis.improvement_suggestions.map((sim, i) => (
                      <tr key={i}>
                        <td className="px-5 py-3 text-slate-900 font-bold capitalize">
                          {cleanRecommendation(sim.improvement)}
                        </td>
                        <td className="px-5 py-3 text-center font-mono text-slate-500 font-bold">
                          {Math.round(sim.current_score)}
                        </td>
                        <td className="px-5 py-3 text-center text-slate-800 font-bold">
                          {Math.round(sim.predicted_score)}
                        </td>
                        <td className="px-5 py-3 text-center text-emerald-650 font-bold">
                          +{sim.delta_gain.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Warnings (if any) */}
        {analysis.warnings && analysis.warnings.length > 0 && (
          <Card className="report-section border-amber-200 bg-amber-50">
            <CardHeader className="pb-3 border-b border-amber-100">
              <CardTitle className="text-sm font-bold text-amber-800 flex items-center gap-2">
                Analysis Warnings
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-amber-100">
                {analysis.warnings.map((warn, i) => (
                  <div key={i} className="px-5 py-3 text-xs text-amber-800 font-semibold">
                    {warn}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Report Footer */}
        <div className="text-center py-4 border-t border-slate-100 report-footer">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
            Generated by TalentAlign Platform · Weight Profile: {analysis.weight_profile_used} · Seniority: {analysis.seniority_level}
          </p>
        </div>
      </div>
    </div>
  );
};
