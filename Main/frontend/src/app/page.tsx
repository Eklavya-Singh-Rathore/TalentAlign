"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAnalysis } from "../stores/analysis-store";
import { useUpload } from "../hooks/use-upload";
import { DashboardShell } from "../components/layout/dashboard-shell";
import { ResumeUploader } from "../components/upload/resume-uploader";
import { JdInput } from "../components/upload/jd-input";
import { ValidationBanner } from "../components/upload/validation-banner";
import { UploadHeroIllustration } from "../components/upload/upload-hero-illustration";
import { ScoreGauge } from "../components/dashboard/score-gauge";
import { ScoreCards } from "../components/dashboard/score-cards";
import { ComponentBreakdown } from "../components/dashboard/component-breakdown";
import { GapAnalysis } from "../components/dashboard/gap-analysis";
import { Recommendations } from "../components/dashboard/recommendations";
import { ReportExport } from "../components/dashboard/report-export";
import { CandidateAssessment } from "../components/dashboard/candidate-summary";
import { EmptyState } from "../components/ui/empty-state";
import { SkillTable } from "../components/tables/skill-table";
import { RadarFitChart } from "../components/charts/radar-fit-chart";
import { BarBreakdownChart } from "../components/charts/bar-breakdown-chart";
import { SkillMatchChart } from "../components/charts/skill-match-chart";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { 
  FileText, 
  Play, 
  BarChart4, 
  Layers, 
  Info, 
  CheckCircle, 
  ChevronDown, 
  ChevronUp, 
  ArrowUpRight 
} from "lucide-react";
import { formatScore } from "../lib/formatters";

export default function MainPage() {
  const { 
    currentAnalysis, 
    activeTab, 
    isLoading, 
    error,
    setActiveTab,
    history
  } = useAnalysis();

  const {
    file,
    jd,
    validationError,
    isDragging,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileChange,
    handleJdChange,
    triggerAnalysis,
    clearSelection,
  } = useUpload();

  const [activeChart, setActiveChart] = useState<"bar" | "radar">("bar");
  const [expandSkillsTable, setExpandSkillsTable] = useState(false);

  // Render Upload Workspace (Screen 1)
  const renderUploadView = () => (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Branded Product Showcase Hero */}
      <Card className="border-slate-200 bg-white shadow-sm overflow-hidden min-h-[280px] h-auto flex flex-col justify-between">
        {/* Product Branding */}
        <div className="text-center py-4 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-xl font-extrabold text-slate-900 tracking-[0.2em] font-sans leading-none">
            TALENTALIGN
          </h2>
          <p className="text-[9px] font-bold text-primary uppercase tracking-[0.15em] mt-1.5">
            AI-Powered Career Intelligence System
          </p>
        </div>

        {/* Hero Content (Two Columns) */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 items-center px-4 md:px-8 py-4 gap-8 overflow-hidden">
          {/* Left Column: SVG Illustration */}
          <div className="h-full flex items-center justify-center border-b md:border-b-0 md:border-r border-slate-100 pb-6 md:pb-0 md:pr-6">
            <UploadHeroIllustration />
          </div>

          {/* Right Column: Product Overview */}
          <div className="space-y-3 flex flex-col justify-center">
            <h3 className="text-xs font-bold text-slate-900 leading-snug">
              Analyze resume-job compatibility using advanced semantic intelligence.
            </h3>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              TalentAlign evaluates candidate-job compatibility using semantic matching, experience intelligence, project relevance, and domain-aware scoring to identify strengths, gaps, and improvement opportunities.
            </p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 pt-1">
              <div className="flex items-center gap-2 text-[9px] font-bold text-slate-600 uppercase tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                Skills Intel
              </div>
              <div className="flex items-center gap-2 text-[9px] font-bold text-slate-600 uppercase tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                Experience Intel
              </div>
              <div className="flex items-center gap-2 text-[9px] font-bold text-slate-600 uppercase tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                Project Intel
              </div>
              <div className="flex items-center gap-2 text-[9px] font-bold text-slate-600 uppercase tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                Scoring Engine
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 border border-slate-200/80 p-1.5 rounded-2xl">
        <Card className="border-transparent bg-transparent shadow-none p-4">
          <ResumeUploader
            file={file}
            onFileChange={handleFileChange}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            isDragging={isDragging}
            onClear={clearSelection}
            error={validationError || error}
          />
        </Card>
        
        <Card className="border-transparent bg-transparent shadow-none p-4">
          <JdInput 
            value={jd} 
            onChange={handleJdChange} 
            error={validationError} 
          />
        </Card>
      </div>

      {/* Upload action */}
      <div className="flex justify-center pt-2">
        <Button
          onClick={triggerAnalysis}
          loading={isLoading}
          variant="primary"
          size="lg"
          className="px-8 py-3.5 text-xs uppercase tracking-widest font-black rounded-xl shadow-sm hover:shadow-md transition-all duration-200 border-none"
        >
          <Play className="w-3.5 h-3.5 mr-2 fill-current" />
          Analyze Candidate Profile
        </Button>
      </div>
    </div>
  );

  // Render Dashboard Overview (Screen 2)
  const renderDashboardView = () => {
    if (isLoading) {
      return (
        <div className="space-y-6 animate-fade-in">
          {/* Top Headline Grid (Gauge, Charts, KPI Breakdown) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Gauge Widget */}
            <Card className="border-slate-200 bg-white flex flex-col justify-center items-center shadow-sm">
              <CardHeader className="text-center pb-0 w-full">
                <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Match Score
                </CardTitle>
              </CardHeader>
              <ScoreGauge loading={true} />
            </Card>

            {/* Analytics Chart Widget */}
            <Card className="lg:col-span-2 border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-2 border-b border-slate-100 flex flex-row justify-between items-center">
                <div>
                  <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    Component Analytics
                  </CardTitle>
                  <div className="h-3 w-44 bg-slate-100 rounded animate-shimmer mt-1" />
                </div>
                <div className="h-6 w-24 bg-slate-100 rounded-lg animate-shimmer" />
              </CardHeader>
              <CardContent className="p-4 pt-6 h-[232px] flex items-end justify-between gap-4 px-6 pb-2">
                {[...Array(6)].map((_, idx) => (
                  <div key={idx} className="flex flex-col items-center gap-2 w-full h-full justify-end">
                    <div 
                      className="w-full bg-slate-100 rounded-t animate-shimmer" 
                      style={{ height: `${20 + idx * 12}%` }}
                    />
                    <div className="h-3 w-8 bg-slate-50 rounded animate-shimmer mt-1" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* KPI Score Cards Skeleton */}
          <ScoreCards loading={true} />

          {/* Candidate Narrative Assessment Skeleton */}
          <CandidateAssessment loading={true} />
        </div>
      );
    }

    if (!currentAnalysis) {
      return (
        <EmptyState
          title="No Match Analysis Available"
          message="Run an analysis to view match insights."
          illustration="dashboard"
        />
      );
    }

    return (
      <div className="space-y-6">
        {/* Validation Warnings */}
        <ValidationBanner warnings={currentAnalysis.warnings} />

        {/* Top Headline Grid (Gauge, Charts, KPI Breakdown) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Gauge Widget */}
          <Card className="border-slate-200 bg-white flex flex-col justify-center items-center shadow-sm">
            <CardHeader className="text-center pb-0">
              <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                Match Score
              </CardTitle>
            </CardHeader>
            <ScoreGauge 
              score={currentAnalysis.placement_score} 
              matchLevel={currentAnalysis.match_level} 
            />
          </Card>

          {/* Analytics Chart Widget */}
          <Card className="lg:col-span-2 border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-2 border-b border-slate-100 flex flex-row justify-between items-center">
              <div>
                <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Component Analytics
                </CardTitle>
                <CardDescription className="text-[10px]">
                  Visual representation of the candidate match profile.
                </CardDescription>
              </div>

              {/* Chart selector chips */}
              <div className="flex bg-slate-100 px-1 py-1 rounded-lg border border-slate-200 text-[9px] font-bold uppercase">
                <button
                  onClick={() => setActiveChart("bar")}
                  className={`px-2 py-1 rounded ${activeChart === "bar" ? "bg-white text-primary border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.02)]" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Breakdown
                </button>
                <button
                  onClick={() => setActiveChart("radar")}
                  className={`px-2 py-1 rounded ${activeChart === "radar" ? "bg-white text-primary border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.02)]" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Coverage
                </button>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-6">
              {activeChart === "bar" && (
                <BarBreakdownChart breakdown={currentAnalysis.component_breakdown} />
              )}
              {activeChart === "radar" && (
                <RadarFitChart breakdown={currentAnalysis.component_breakdown} />
              )}
            </CardContent>
          </Card>
        </div>

        {/* KPI Score Cards */}
        <ScoreCards
          roleTitle={currentAnalysis.role_title}
          domainDetected={currentAnalysis.domain_detected}
          seniorityLevel={currentAnalysis.seniority_level}
          experienceMonths={currentAnalysis.experience_intelligence?.total_experience_months || 0}
          requiredYears={currentAnalysis.jd_extraction?.experience_years || 0}
          experienceMeetsJd={currentAnalysis.experience_intelligence?.experience_meets_jd_requirement || false}
          warningsCount={currentAnalysis.warnings?.length || 0}
        />

        {/* Candidate Narrative Assessment (LLM-only) */}
        {((currentAnalysis.debug?.llm_backend && currentAnalysis.debug?.llm_backend !== "none") || currentAnalysis.explainability?.llm_polishing_used) && (
          <CandidateAssessment analysis={currentAnalysis} />
        )}
      </div>
    );
  };

  // Render Component Alignment page (Screen 3)
  const renderScoringView = () => {
    if (isLoading) {
      return (
        <div className="space-y-6 animate-fade-in">
          <div>
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">
              Component Breakdown
            </h3>
            <ComponentBreakdown loading={true} />
          </div>

          {/* Matched Skills Details Card Loading Skeleton */}
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="space-y-1.5 flex-1">
                <div className="h-4 w-44 bg-slate-200 rounded animate-shimmer" />
                <div className="h-3 w-64 bg-slate-100 rounded animate-shimmer mt-2" />
              </div>
            </CardHeader>
          </Card>
        </div>
      );
    }

    if (!currentAnalysis) {
      return (
        <EmptyState
          title="No Component Alignment Details"
          message="Technical component scoring will be displayed once analysis is completed."
          illustration="scoring"
        />
      );
    }

    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">
            Component Breakdown
          </h3>
          <ComponentBreakdown
            breakdown={currentAnalysis.component_breakdown}
            excluded={currentAnalysis.excluded_components}
          />
        </div>

        {/* Matched Skills Details (Expandable) */}
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader 
            className="cursor-pointer hover:bg-slate-50/50 transition-all flex flex-row items-center justify-between"
            onClick={() => setExpandSkillsTable(!expandSkillsTable)}
          >
            <div>
              <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Matched Skills Alignment
              </CardTitle>
              <CardDescription className="text-xs">
                Comprehensive matched list of resume concepts vs requirements.
              </CardDescription>
            </div>
            {expandSkillsTable ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </CardHeader>
          {expandSkillsTable && (
            <CardContent className="pt-0">
              <SkillTable matchedSkills={currentAnalysis.skills_analysis?.match_details || []} />
            </CardContent>
          )}
        </Card>
      </div>
    );
  };

  // Render Gap Analysis View (Screen 3)
  const renderGapView = () => {
    if (isLoading) {
      return <GapAnalysis loading={true} />;
    }

    if (!currentAnalysis) {
      return (
        <EmptyState
          title="No Gap Analysis Available"
          message="Gap analysis will appear after scoring is complete."
          illustration="gaps"
        />
      );
    }

    return (
      <GapAnalysis
        rankedGaps={currentAnalysis.gap_analysis?.ranked_gaps || []}
        totalRecoverablePct={currentAnalysis.gap_analysis?.total_recoverable_pct || 0}
        missingSkills={currentAnalysis.skills_analysis?.missing_skills || []}
        certificationsPresent={currentAnalysis.resume_extraction?.certifications || []}
        emptySections={currentAnalysis.resume_extraction?.empty_sections || []}
      />
    );
  };

  // Render Recommendations View (Screen 4)
  const renderRecommendationsView = () => {
    if (isLoading) {
      return <Recommendations loading={true} />;
    }

    if (!currentAnalysis) {
      return (
        <EmptyState
          title="No Recommendations Generated"
          message="Recommendations will be generated after candidate evaluation."
          illustration="recommendations"
        />
      );
    }

    return (
      <Recommendations
        suggestions={currentAnalysis.improvement_suggestions || []}
        combinedImprovement={currentAnalysis.combined_improvement || {}}
        recommendations={currentAnalysis.recommendations || {}}
      />
    );
  };

  // Render Report & Export View (Screen 5)
  const renderExportView = () => {
    if (isLoading) {
      return <ReportExport loading={true} />;
    }

    if (!currentAnalysis) {
      return (
        <EmptyState
          title="No Exportable Report Available"
          message="Generate a report to view exportable results."
          illustration="export"
        />
      );
    }

    return (
      <ReportExport analysis={currentAnalysis} />
    );
  };

  return (
    <DashboardShell>
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
        >
          {activeTab === "upload" && renderUploadView()}
          {activeTab === "dashboard" && renderDashboardView()}
          {activeTab === "scoring" && renderScoringView()}
          {activeTab === "gaps" && renderGapView()}
          {activeTab === "recommendations" && renderRecommendationsView()}
          {activeTab === "export" && renderExportView()}
        </motion.div>
      </AnimatePresence>
    </DashboardShell>
  );
}
