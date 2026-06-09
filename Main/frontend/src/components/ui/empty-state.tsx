import React from "react";
import { cn } from "../../lib/utils";
import { Card, CardContent } from "./card";
import { Button } from "./button";
import { useAnalysis } from "../../stores/analysis-store";
import { 
  LayoutDashboard, 
  Layers, 
  BadgeAlert, 
  Lightbulb, 
  FileDown, 
  ArrowRight 
} from "lucide-react";

interface EmptyStateProps {
  title: string;
  message: string;
  illustration: "dashboard" | "scoring" | "gaps" | "recommendations" | "export";
  className?: string;
}

const DashboardIllustration = () => (
  <svg width="180" height="130" viewBox="0 0 180 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="select-none mx-auto">
    <defs>
      <linearGradient id="dbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#60a5fa" />
        <stop offset="100%" stopColor="#3b82f6" />
      </linearGradient>
    </defs>
    <rect x="15" y="10" width="150" height="110" rx="12" fill="#ffffff" stroke="#f1f5f9" strokeWidth="1.5" />
    <rect x="15" y="10" width="150" height="110" rx="12" fill="#f8fafc" fillOpacity="0.5" />
    
    {/* Circular gauge */}
    <circle cx="55" cy="65" r="28" fill="#ffffff" stroke="#f1f5f9" strokeWidth="1.5" />
    <circle cx="55" cy="65" r="22" stroke="url(#dbGrad)" strokeWidth="4.5" strokeDasharray="95 40" strokeLinecap="round" />
    <circle cx="55" cy="65" r="14" fill="#f8fafc" />
    
    {/* Content lines */}
    <rect x="100" y="32" width="50" height="8" rx="4" fill="#e2e8f0" />
    <rect x="100" y="48" width="32" height="6" rx="3" fill="#cbd5e1" fillOpacity="0.6" />
    
    <rect x="100" y="68" width="50" height="20" rx="6" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
    <rect x="108" y="75" width="22" height="6" rx="3" fill="#22c55e" fillOpacity="0.8" />
    <circle cx="140" cy="78" r="2.5" fill="#22c55e" />
    
    <path d="M125 105 L155 105" stroke="#e2e8f0" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

const ScoringIllustration = () => (
  <svg width="180" height="130" viewBox="0 0 180 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="select-none mx-auto">
    <defs>
      <linearGradient id="plateGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#93c5fd" />
        <stop offset="100%" stopColor="#3b82f6" />
      </linearGradient>
    </defs>
    {/* Top layer plate */}
    <path d="M90 15 L150 40 L90 65 L30 40 Z" fill="#ffffff" stroke="url(#plateGrad)" strokeWidth="1.5" />
    <path d="M90 20 L140 40 L90 60 L40 40 Z" fill="#eff6ff" fillOpacity="0.7" />
    <line x1="90" y1="28" x2="122" y2="41" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" />
    <line x1="90" y1="36" x2="110" y2="44" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" />
    
    {/* Connecting dashed line */}
    <line x1="90" y1="65" x2="90" y2="90" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="3 3" />
    
    {/* Bottom layer plate */}
    <path d="M90 55 L150 80 L90 105 L30 80 Z" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
    <path d="M90 60 L140 80 L90 100 L40 80 Z" fill="#f8fafc" fillOpacity="0.8" />
    <line x1="90" y1="68" x2="122" y2="81" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

const GapsIllustration = () => (
  <svg width="180" height="130" viewBox="0 0 180 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="select-none mx-auto">
    <rect x="35" y="15" width="110" height="100" rx="10" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
    <rect x="35" y="15" width="110" height="100" rx="10" fill="#f8fafc" fillOpacity="0.4" />
    {/* Clipboard top clip */}
    <rect x="75" y="8" width="30" height="14" rx="4" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
    
    {/* Checklist lines */}
    <circle cx="55" cy="45" r="5" fill="#fef08a" stroke="#eab308" strokeWidth="1" />
    <line x1="70" y1="45" x2="120" y2="45" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
    
    <circle cx="55" cy="65" r="5" fill="#fee2e2" stroke="#ef4444" strokeWidth="1" />
    <line x1="70" y1="65" x2="110" y2="65" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
    
    <circle cx="55" cy="85" r="5" fill="#dcfce7" stroke="#22c55e" strokeWidth="1" />
    <line x1="70" y1="85" x2="125" y2="85" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
    
    {/* Search/Warning Accent */}
    <circle cx="130" cy="95" r="16" fill="#fee2e2" stroke="#fca5a5" strokeWidth="1.2" />
    <path d="M130 90 L130 96" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="130" cy="101" r="1.25" fill="#ef4444" />
  </svg>
);

const RecommendationsIllustration = () => (
  <svg width="180" height="130" viewBox="0 0 180 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="select-none mx-auto">
    <defs>
      <linearGradient id="bulbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#bae6fd" />
        <stop offset="100%" stopColor="#7dd3fc" />
      </linearGradient>
    </defs>
    {/* Background Circles */}
    <circle cx="90" cy="60" r="42" fill="#f0f9ff" stroke="#e0f2fe" strokeWidth="1" />
    <circle cx="90" cy="60" r="32" fill="#e0f2fe" fillOpacity="0.4" />
    
    {/* Lightbulb outline */}
    <path d="M90 33C77.9543 33 68 42.9543 68 55C68 61.8721 71.1872 68.0687 76.2042 72.1218C79.4705 74.7207 81.2961 78.7053 81.3 82.75H98.7C98.7039 78.7053 100.53 74.7207 103.796 72.1218C108.813 68.0687 112 61.8721 112 55C112 42.9543 102.046 33 90 33Z" fill="#ffffff" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M78 50 C82 45, 98 45, 102 50" stroke="url(#bulbGrad)" strokeWidth="4" strokeLinecap="round" />
    
    <rect x="82.5" y="82.75" width="15" height="7.25" rx="1.5" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1.5" />
    <path d="M85 90H95C95 92.5 94 94 90 94C86 94 85 92.5 85 90Z" fill="#94a3b8" />
    
    {/* Sparkles */}
    <path d="M90 16 L90 22" stroke="#eab308" strokeWidth="2.5" strokeLinecap="round" />
    <path d="M54 55 L60 55" stroke="#eab308" strokeWidth="2.5" strokeLinecap="round" />
    <path d="M120 55 L126 55" stroke="#eab308" strokeWidth="2.5" strokeLinecap="round" />
    <path d="M65 31 L70 36" stroke="#eab308" strokeWidth="2" strokeLinecap="round" />
    <path d="M115 31 L110 36" stroke="#eab308" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const ExportIllustration = () => (
  <svg width="180" height="130" viewBox="0 0 180 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="select-none mx-auto">
    {/* Document Folder */}
    <path d="M25 40C25 34.4772 29.4772 30 35 30H70L82 42H145C150.523 42 155 46.4772 155 52V100C155 105.523 150.523 110 145 110H35C29.4772 110 25 105.523 25 100V40Z" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.5" />
    <path d="M25 48 H155" stroke="#e2e8f0" strokeWidth="1" />
    
    {/* Inner Document */}
    <g transform="translate(62, 18)">
      <rect x="0" y="0" width="55" height="70" rx="4" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.5" />
      <line x1="10" y1="18" x2="45" y2="18" stroke="#4f7df3" strokeWidth="2" strokeLinecap="round" />
      <line x1="10" y1="28" x2="35" y2="28" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="10" y1="38" x2="40" y2="38" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="10" y1="48" x2="30" y2="48" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />
    </g>
    
    {/* Download Overlay Badge */}
    <circle cx="132" cy="82" r="16" fill="#dcfce7" stroke="#4ade80" strokeWidth="1.2" />
    <path d="M132 75 L132 87 M127 82 L132 87 L137 82" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M125 91 H139" stroke="#16a34a" strokeWidth="2" />
  </svg>
);

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  illustration,
  className,
}) => {
  const { setActiveTab } = useAnalysis();

  const renderIllustration = () => {
    switch (illustration) {
      case "dashboard":
        return <DashboardIllustration />;
      case "scoring":
        return <ScoringIllustration />;
      case "gaps":
        return <GapsIllustration />;
      case "recommendations":
        return <RecommendationsIllustration />;
      case "export":
        return <ExportIllustration />;
      default:
        return null;
    }
  };

  const getNavigationIcon = () => {
    switch (illustration) {
      case "dashboard":
        return LayoutDashboard;
      case "scoring":
        return Layers;
      case "gaps":
        return BadgeAlert;
      case "recommendations":
        return Lightbulb;
      case "export":
        return FileDown;
      default:
        return LayoutDashboard;
    }
  };

  const Icon = getNavigationIcon();

  return (
    <Card className={cn("border border-slate-200/80 bg-white shadow-sm max-w-xl mx-auto my-8 overflow-hidden animate-fade-in", className)}>
      <CardContent className="p-8 text-center flex flex-col items-center justify-center space-y-6">
        {/* Decorative Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full text-[9px] font-bold text-slate-400 uppercase tracking-widest">
          <Icon className="w-3.5 h-3.5 text-slate-400" /> Page Preview State
        </div>

        {/* Custom Illustration */}
        <div className="w-full flex justify-center py-2">
          {renderIllustration()}
        </div>

        {/* Title & Message */}
        <div className="space-y-2 max-w-sm">
          <h3 className="text-sm font-extrabold text-slate-900 tracking-tight leading-none">
            {title}
          </h3>
          <p className="text-xs text-slate-500 font-semibold leading-relaxed">
            {message}
          </p>
        </div>

        {/* Quick action button */}
        <div className="pt-2">
          <Button
            onClick={() => setActiveTab("upload")}
            variant="outline"
            size="sm"
            className="text-xs gap-1.5 font-bold uppercase tracking-wider rounded-xl border-slate-200 text-slate-700 bg-slate-50 hover:bg-slate-100/80 transition-all hover:border-slate-300"
          >
            Go to Upload Workspace <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
