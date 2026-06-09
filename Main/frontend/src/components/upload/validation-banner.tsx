import React from "react";
import { AlertTriangle, Info, X } from "lucide-react";

interface ValidationBannerProps {
  warnings?: string[];
  onDismiss?: () => void;
}

export const ValidationBanner: React.FC<ValidationBannerProps> = ({ warnings, onDismiss }) => {
  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200/80 text-amber-900 rounded-2xl p-4 flex gap-3 shadow-sm">
      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800">Analysis Boundary Warnings</h4>
        <ul className="list-disc pl-4 space-y-1 text-xs text-amber-700 font-semibold">
          {warnings.map((warn, index) => (
            <li key={index}>{warn}</li>
          ))}
        </ul>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-amber-500 hover:text-amber-700 p-1 rounded-lg hover:bg-amber-100 h-fit self-start transition-all"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
