"use client";

import React, { useState } from "react";
import { useAnalysis } from "../../stores/analysis-store";
import { DashboardShell } from "../../components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Download, Printer, Copy, Check, FileJson, FileText, LayoutDashboard } from "lucide-react";
import { formatScore, formatFractionAsScore } from "../../lib/formatters";
import { COMPONENT_LABELS } from "../../lib/constants";

export default function ReportsPage() {
  const { currentAnalysis, setActiveTab } = useAnalysis();
  const [copied, setCopied] = useState(false);
  const [exportType, setExportType] = useState<"summary" | "json">("summary");

  if (!currentAnalysis) {
    return (
      <DashboardShell>
        <div className="flex flex-col items-center justify-center text-center p-12 h-[60vh]">
          <div className="bg-slate-900/50 p-4 rounded-full border border-slate-800 text-slate-600 mb-4">
            <FileText className="w-10 h-10" />
          </div>
          <h3 className="text-lg font-bold text-slate-300">No active scan loaded</h3>
          <p className="text-xs text-slate-500 mt-2 max-w-sm">
            Please run an alignment match first before generating a report summary.
          </p>
          <Button 
            className="mt-6" 
            onClick={() => setActiveTab("upload")}
          >
            Go to Upload
          </Button>
        </div>
      </DashboardShell>
    );
  }

  const handlePrint = () => {
    window.print();
  };

  const handleCopyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(currentAnalysis, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJSON = () => {
    const filename = `TalentAlign_${currentAnalysis.resume_extraction?.sections_present[0] || "Report"}_Score_${Math.round(currentAnalysis.placement_score)}.json`;
    const jsonStr = JSON.stringify(currentAnalysis, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const matchedSkills = currentAnalysis.skills_analysis?.match_details || [];
  const missingSkills = currentAnalysis.skills_analysis?.missing_skills || [];

  return (
    <DashboardShell>
      <div className="space-y-6 print:bg-white print:text-slate-900 print:p-0 print:space-y-4">
        {/* Actions bar (hidden in print) */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm print:hidden">
          <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-lg border border-slate-100">
            <button
              onClick={() => setExportType("summary")}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all uppercase ${
                exportType === "summary" 
                  ? "bg-white text-primary border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.02)]" 
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Summary Review
            </button>
            <button
              onClick={() => setExportType("json")}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all uppercase ${
                exportType === "json" 
                  ? "bg-white text-primary border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.02)]" 
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Raw JSON Data
            </button>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {exportType === "json" ? (
              <>
                <Button variant="outline" size="sm" onClick={handleCopyJSON} className="flex-1 sm:flex-none">
                  {copied ? <Check className="w-4 h-4 mr-1.5 text-emerald-600" /> : <Copy className="w-4 h-4 mr-1.5" />}
                  {copied ? "Copied" : "Copy Payload"}
                </Button>
                <Button size="sm" onClick={handleDownloadJSON} className="flex-1 sm:flex-none">
                  <Download className="w-4 h-4 mr-1.5" />
                  Download JSON
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={handlePrint} className="w-full sm:w-auto">
                <Printer className="w-4 h-4 mr-1.5" />
                Print PDF Report
              </Button>
            )}
          </div>
        </div>

        {/* Content Pane */}
        {exportType === "summary" ? (
          <div className="space-y-6 print:space-y-8">
            {/* Header section */}
            <div className="border border-slate-200 bg-white shadow-sm p-6 rounded-xl space-y-4 print:border-slate-300 print:bg-white print:p-0">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <h2 className="text-xl font-extrabold text-slate-900 print:text-slate-900">
                    TalentAlign Assessment Report
                  </h2>
                  <p className="text-xs text-slate-400">
                    Generated: {new Date().toLocaleDateString()} · Job Fit Analysis
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black text-primary print:text-indigo-600 block">
                    {formatScore(currentAnalysis.placement_score)}
                  </span>
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                    {currentAnalysis.match_level}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100 print:border-slate-200">
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block uppercase">Target Position</span>
                  <span className="text-xs font-bold text-slate-800 print:text-slate-900 capitalize">
                    {currentAnalysis.role_title === "not_specified" ? "Not Specified" : currentAnalysis.role_title}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block uppercase">Seniority Level</span>
                  <span className="text-xs font-bold text-slate-800 print:text-slate-900 capitalize">
                    {currentAnalysis.seniority_level.replace("_", " ")}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block uppercase">Profile Domain</span>
                  <span className="text-xs font-bold text-slate-800 print:text-slate-900">
                    {currentAnalysis.domain_detected.replace("_", " ").toUpperCase()}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block uppercase">Experience Found</span>
                  <span className="text-xs font-bold text-slate-800 print:text-slate-900">
                    {Math.round(currentAnalysis.experience_intelligence?.total_experience_months / 12 || 0)} Years
                  </span>
                </div>
              </div>
            </div>

            {/* Component scores & summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 print:grid-cols-1 print:gap-4">
              {/* Score matrix table */}
              <Card className="report-section border-slate-200 bg-white shadow-sm print:border-slate-300 print:bg-white">
                <CardHeader className="pb-3 border-b border-slate-100 print:border-slate-200">
                  <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-900 print:text-slate-900">
                    Alignment Score Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 text-slate-400 font-semibold uppercase border-b border-slate-100 print:border-slate-200 print:bg-slate-50">
                        <th className="px-4 py-2.5">Component</th>
                        <th className="px-4 py-2.5">Nominal Weight</th>
                        <th className="px-4 py-2.5 text-right">Score Achieved</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 print:divide-slate-200 text-slate-700 font-semibold">
                      {currentAnalysis.component_breakdown.map((comp) => (
                        <tr key={comp.component} className={comp.active ? "" : "opacity-45"}>
                          <td className="px-4 py-3 text-slate-900 print:text-slate-900 font-semibold">
                            {comp.component} · {COMPONENT_LABELS[comp.component] || comp.component}
                          </td>
                          <td className="px-4 py-3 text-slate-500 font-bold">{Math.round(comp.weight * 100)}%</td>
                          <td className="px-4 py-3 text-right text-primary print:text-indigo-600 font-bold">
                            {comp.active ? formatFractionAsScore(comp.component_score) : "Excluded"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              {/* Profile Assessment review */}
              <Card className="report-section border-slate-200 bg-white shadow-sm print:border-slate-300 print:bg-white">
                <CardHeader className="pb-3 border-b border-slate-100 print:border-slate-200">
                  <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-900 print:text-slate-900">
                    Profile Assessment
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-4">
                  <p className="text-xs text-slate-650 print:text-slate-700 leading-relaxed font-semibold italic">
                    {currentAnalysis.final_summary?.overall_assessment}
                  </p>
                  
                  <div className="space-y-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block">
                      Core Missing Skills
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {missingSkills.slice(0, 10).map((skill, idx) => (
                        <span 
                          key={idx} 
                          className="bg-red-500/10 text-red-650 border border-red-500/20 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider print:bg-red-50 print:text-red-700 print:border-red-200"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold text-slate-900">Analysis JSON Payload</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Direct structured schema containing all 29 top-level alignment attributes.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0">
              <pre className="text-[10px] font-mono leading-relaxed bg-slate-950 text-indigo-400 p-4 rounded-xl border border-slate-900 overflow-x-auto max-h-[500px] scrollbar-thin">
                <code>{JSON.stringify(currentAnalysis, null, 2)}</code>
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}
