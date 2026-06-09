import React, { useEffect, useState } from "react";
import { useAnalysis } from "../../stores/analysis-store";
import { checkHealth, HealthResponse } from "../../lib/api";
import { FileUp, ShieldCheck, AlertCircle, RefreshCw } from "lucide-react";
import { DOMAIN_LABELS } from "../../lib/constants";

export const Header: React.FC = () => {
  const { currentAnalysis, clearAnalysis, activeTab, isLoading } = useAnalysis();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<"ok" | "error" | "loading">("loading");

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
        setHealthStatus("ok");
      } catch (err) {
        setHealthStatus("error");
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000); // Check health every 15s
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    switch (activeTab) {
      case "upload":
        return "Upload Candidate Profile";
      case "dashboard":
        return "Match Analysis Overview";
      case "scoring":
        return "Component Alignment";
      case "gaps":
        return "Gap Analysis Matrix";
      case "recommendations":
        return "Improvement Recommendations";
      case "export":
        return "Report & Export Panel";
      default:
        return "TalentAlign";
    }
  };

  const getLlmBadgeLabel = () => {
    if (healthStatus !== "ok") {
      return healthStatus === "loading" ? "Checking API..." : "AI: SBERT";
    }
    const backend = health?.llm_backend?.toLowerCase();
    if (backend === "gemini") {
      return "AI: Gemini";
    }
    return "AI: SBERT";
  };

  const domainLabel = currentAnalysis
    ? DOMAIN_LABELS[currentAnalysis.domain_detected] || DOMAIN_LABELS["custom"]
    : null;

  const roleTitle = currentAnalysis?.role_title || currentAnalysis?.jd_extraction?.role_title;
  const showRole = roleTitle && roleTitle !== "not_specified";

  return (
    <header className="relative h-16 border-b border-slate-200 bg-white px-4 md:px-6 flex items-center justify-between text-slate-800 gap-4 min-w-0 w-full">
      {/* Shimmer progress bar at top when loading */}
      {isLoading && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-primary/10 overflow-hidden print-hide">
          <div className="h-full bg-primary w-1/3 animate-shimmer rounded-full" />
        </div>
      )}
      {/* Title / Current Context */}
      <div className="flex flex-col min-w-0 flex-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="md:hidden text-[9px] font-black text-primary uppercase tracking-wider bg-primary/10 px-1.5 py-0.5 rounded-md flex-shrink-0">TalentAlign</span>
          <h1 className="text-sm font-bold text-slate-900 tracking-tight truncate">{getPageTitle()}</h1>
        </div>
        {currentAnalysis && (
          <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400 font-medium min-w-0 w-full overflow-hidden">
            {showRole && (
              <>
                <span className="font-bold text-primary truncate max-w-[100px] sm:max-w-[200px] uppercase tracking-wider" title={roleTitle}>
                  {roleTitle}
                </span>
                <span>•</span>
              </>
            )}
            <span className="truncate">{domainLabel}</span>
            <span>•</span>
            <span className="text-slate-500 font-semibold uppercase tracking-wider truncate">
              {currentAnalysis.final_summary?.candidate_category || "General Profile"}
            </span>
          </div>
        )}
      </div>

      {/* Right Tools / Health Indicator */}
      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
        {/* API Health */}
        <div className="flex items-center gap-2 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200 text-[10px] font-semibold text-slate-500 whitespace-nowrap">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                healthStatus === "ok"
                  ? "bg-emerald-400"
                  : healthStatus === "error"
                  ? "bg-red-400"
                  : "bg-amber-400"
              }`}
            ></span>
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                healthStatus === "ok"
                  ? "bg-emerald-500"
                  : healthStatus === "error"
                  ? "bg-red-500"
                  : "bg-amber-500"
              }`}
            ></span>
          </span>
          <span className="uppercase tracking-wider">
            {getLlmBadgeLabel()}
          </span>
        </div>

        {/* Action button */}
        {currentAnalysis && activeTab !== "upload" && (
          <button
            onClick={clearAnalysis}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-primary hover:bg-primary/95 transition-colors text-white font-bold text-xs rounded-xl shadow-[0_4px_12px_rgba(79,125,243,0.15)] whitespace-nowrap"
          >
            <FileUp className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload New</span>
          </button>
        )}
      </div>
    </header>
  );
};
