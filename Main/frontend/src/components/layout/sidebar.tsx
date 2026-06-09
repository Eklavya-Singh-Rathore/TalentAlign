import React from "react";
import { motion } from "framer-motion";
import { useAnalysis } from "../../stores/analysis-store";
import { 
  FileSearch, 
  Upload, 
  LayoutDashboard, 
  Layers,
  Skull, 
  FolderGit2, 
  Compass, 
  Activity, 
  History, 
  Trash2,
  FileText,
  BadgeAlert,
  Lightbulb,
  FileDown
} from "lucide-react";
import { formatScore } from "../../lib/formatters";

export const Sidebar: React.FC = () => {
  const { 
    activeTab, 
    setActiveTab, 
    history, 
    loadFromHistory, 
    deleteHistoryItem,
    currentAnalysis,
    clearAnalysis,
    isLoading
  } = useAnalysis();

  const menuItems = [
    { id: "upload", label: "Upload & Match", icon: Upload, disabled: isLoading },
    { id: "dashboard", label: "Match Overview", icon: LayoutDashboard, disabled: false },
    { id: "scoring", label: "Component Alignment", icon: Layers, disabled: false },
    { id: "gaps", label: "Gap Analysis", icon: BadgeAlert, disabled: false },
    { id: "recommendations", label: "Recommendations", icon: Lightbulb, disabled: false },
    { id: "export", label: "Report & Export", icon: FileDown, disabled: false },
  ];

  return (
    <aside className="w-full md:w-56 lg:w-64 bg-white border-r border-slate-200 flex flex-col h-full overflow-hidden text-slate-600">
      {/* Brand Header */}
      <div 
        className={`h-16 flex items-center gap-3 px-6 border-b border-slate-100 ${isLoading ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-slate-50"} transition-all`}
        onClick={() => !isLoading && clearAnalysis()}
      >
        <div className="bg-primary p-2 rounded-xl text-white shadow-[0_4px_12px_rgba(79,125,243,0.15)]">
          <FileSearch className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-slate-900 tracking-tight block text-md leading-none mb-0.5">TalentAlign</span>
          <span className="text-[9px] text-primary font-bold uppercase tracking-wider block">Resume Intel V2</span>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        <span className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
          Navigation
        </span>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => !item.disabled && setActiveTab(item.id as any)}
              disabled={item.disabled}
              className={`relative w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold tracking-wide border transition-all duration-200 ${
                isActive
                  ? "border-primary/20 text-primary"
                  : item.disabled
                  ? "opacity-30 cursor-not-allowed text-slate-400 border-transparent"
                  : "hover:bg-slate-50 hover:text-slate-900 text-slate-500 border-transparent"
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTabBg"
                  className="absolute inset-0 bg-primary/10 rounded-xl -z-10"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <Icon className={`w-4 h-4 ${isActive ? "text-primary" : "text-slate-400"}`} />
              {item.label}
            </button>
          );
        })}

        {/* Saved Analysis History Section */}
        {history.length > 0 && (
          <div className="pt-8 space-y-2">
            <span className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
              <History className="w-3.5 h-3.5" /> Recent Matches
            </span>
            <div className="space-y-1.5 max-h-[280px] overflow-y-auto pr-1">
              {history.map((item) => {
                const isItemActive = currentAnalysis && currentAnalysis.placement_score === item.payload.placement_score && item.filename === currentAnalysis.resume_extraction?.sections_present[0]; // approximation
                return (
                  <div
                    key={item.id}
                    className="group flex items-center justify-between gap-1 w-full text-left rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all p-2 pl-3"
                  >
                    <button
                      onClick={() => loadFromHistory(item)}
                      className="flex-1 min-w-0"
                    >
                      <span className="text-xs font-semibold text-slate-700 block truncate group-hover:text-primary transition-colors">
                        {item.filename}
                      </span>
                      <span className="text-[10px] text-slate-400 block truncate font-medium">
                        {item.role === "not_specified" ? "Target Role" : item.role} · {formatScore(item.score)}
                      </span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteHistoryItem(item.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 p-1 rounded-lg hover:bg-slate-100 transition-all"
                      title="Delete entry"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50 text-center text-[9px] font-semibold tracking-wider text-slate-400 uppercase">
        &copy; 2026 TalentAlign Platform
      </div>
    </aside>
  );
};
