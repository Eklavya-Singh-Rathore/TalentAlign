import React from "react";
import { FileText, Sparkles } from "lucide-react";
import { SAMPLE_JD } from "../../lib/constants";

interface JdInputProps {
  value: string;
  onChange: (text: string) => void;
  error?: string | null;
}

export const JdInput: React.FC<JdInputProps> = ({ value, onChange, error }) => {
  const charCount = value.length;
  const wordCount = value.trim() === "" ? 0 : value.trim().split(/\s+/).length;

  const handleLoadSample = (e: React.MouseEvent) => {
    e.preventDefault();
    onChange(SAMPLE_JD);
  };

  return (
    <div className="flex flex-col space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Job Description (JD)</label>
        <button
          onClick={handleLoadSample}
          className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors font-bold uppercase tracking-wider text-[10px]"
          title="Auto-fill with sample SaaS description"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Load Sample JD
        </button>
      </div>

      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste requirements, expectations, tech stacks, experience bounds here..."
          className={`w-full h-48 bg-white border rounded-xl p-4 text-xs font-sans focus:outline-none transition-all duration-300 ${
            error
              ? "border-red-200 focus:border-red-500 focus:ring-1 focus:ring-red-500/10"
              : "border-slate-200 focus:border-primary focus:ring-1 focus:ring-primary/10 hover:border-slate-300 shadow-sm"
          } text-slate-800 placeholder-slate-400`}
        />
        
        {/* Count indicators */}
        <div className="absolute bottom-3 right-4 flex items-center gap-3 text-[10px] font-bold text-slate-400 bg-slate-50/90 px-2.5 py-1 rounded-lg border border-slate-100 backdrop-blur-sm">
          <span>{wordCount} Words</span>
          <span className="text-slate-300 font-normal">|</span>
          <span>{charCount} Chars</span>
        </div>
      </div>
    </div>
  );
};
