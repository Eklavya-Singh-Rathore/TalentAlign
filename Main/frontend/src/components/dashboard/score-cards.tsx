import React from "react";
import { 
  UserCheck, 
  Layers, 
  Briefcase, 
  CheckCircle2, 
  CalendarDays,
  FileBadge
} from "lucide-react";
import { formatExperience } from "../../lib/formatters";
import { DOMAIN_LABELS } from "../../lib/constants";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";

interface ScoreCardsProps {
  roleTitle?: string;
  domainDetected?: string;
  seniorityLevel?: string;
  experienceMonths?: number;
  requiredYears?: number;
  experienceMeetsJd?: boolean;
  warningsCount?: number;
  loading?: boolean;
}

export const ScoreCards: React.FC<ScoreCardsProps> = ({
  roleTitle = "",
  domainDetected = "custom",
  seniorityLevel = "mid_level",
  experienceMonths = 0,
  requiredYears = 0,
  experienceMeetsJd = false,
  warningsCount = 0,
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border border-slate-200/80 bg-slate-50/20">
            <CardContent className="p-5 flex flex-col justify-between h-full">
              <div className="flex items-start justify-between">
                <div className="h-3.5 w-24 bg-slate-100 rounded animate-shimmer" />
                <div className="h-8 w-8 bg-slate-100 rounded-xl animate-shimmer flex-shrink-0" />
              </div>
              <div className="mt-6 space-y-2">
                <div className="h-5.5 w-3/4 bg-slate-100 rounded animate-shimmer" />
                <div className="h-3.5 w-1/2 bg-slate-100 rounded animate-shimmer mt-1" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }
  const cards = [
    {
      title: "Job Role",
      value: roleTitle === "not_specified" ? "Not Specified" : roleTitle,
      icon: UserCheck,
      color: "text-indigo-600",
      bg: "bg-indigo-50/50",
      border: "border-indigo-100",
      extra: <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Confidence: High</span>
    },
    {
      title: "Dominant Profile Domain",
      value: DOMAIN_LABELS[domainDetected] || DOMAIN_LABELS["custom"],
      icon: Layers,
      color: "text-emerald-600",
      bg: "bg-emerald-50/50",
      border: "border-emerald-100",
      extra: <span className="text-[10px] text-emerald-600 font-extrabold uppercase tracking-wider">Weighted Alignment Active</span>
    },
    {
      title: "Seniority Classification",
      value: seniorityLevel.replace("_", " "),
      icon: Briefcase,
      color: "text-purple-600",
      bg: "bg-purple-50/50",
      border: "border-purple-100",
      extra: <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Parsed Career Level</span>
    },
    {
      title: "Experience Validation",
      value: formatExperience(experienceMonths),
      icon: CalendarDays,
      color: experienceMeetsJd || requiredYears === 0 ? "text-teal-600" : "text-amber-600",
      bg: experienceMeetsJd || requiredYears === 0 ? "bg-teal-50/50" : "bg-amber-50/50",
      border: experienceMeetsJd || requiredYears === 0 ? "border-teal-100" : "border-amber-100",
      extra: (
        <div className="flex items-center gap-1.5 mt-1">
          <Badge variant={experienceMeetsJd || requiredYears === 0 ? "success" : "warning"}>
            {experienceMeetsJd || requiredYears === 0 ? "Meets Requirement" : "Below Target"}
          </Badge>
          {requiredYears > 0 && (
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
              JD: {requiredYears} yr{requiredYears > 1 ? "s" : ""}
            </span>
          )}
        </div>
      )
    }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <Card key={i} className={`border ${card.border} ${card.bg}`}>
            <CardContent className="p-5 flex flex-col justify-between h-full">
              <div className="flex items-start justify-between">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">{card.title}</p>
                <div className={`p-2 rounded-xl bg-white border border-slate-200/60 shadow-[0_2px_8px_rgba(0,0,0,0.02)] ${card.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4">
                <span className="text-md md:text-lg font-black text-slate-900 block capitalize truncate">
                  {card.value}
                </span>
                <div className="mt-1.5">{card.extra}</div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
