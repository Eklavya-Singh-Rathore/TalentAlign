import React, { useRef } from "react";
import { UploadCloud, FileText, X, AlertTriangle } from "lucide-react";
import { useUpload } from "../../hooks/use-upload";

interface ResumeUploaderProps {
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  isDragging: boolean;
  onClear: () => void;
  error?: string | null;
}

export const ResumeUploader: React.FC<ResumeUploaderProps> = ({
  file,
  onFileChange,
  onDrop,
  onDragOver,
  onDragLeave,
  isDragging,
  onClear,
  error,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="flex flex-col space-y-2">
      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Candidate Resume</label>
      
      {!file ? (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`h-48 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-4 text-center cursor-pointer transition-all duration-300 ${
            isDragging
              ? "border-primary bg-primary/5 text-slate-900 shadow-sm"
              : "border-slate-200 bg-white hover:bg-slate-50/50 text-slate-400 hover:border-slate-300 hover:shadow-sm"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={onFileChange}
            accept=".pdf,.docx"
            className="hidden"
          />
          <svg width="60" height="50" viewBox="0 0 60 50" fill="none" xmlns="http://www.w3.org/2000/svg" className="mb-3 select-none">
            {/* Sheet outline */}
            <rect x="18" y="4" width="24" height="34" rx="3" fill="#ffffff" stroke={isDragging ? "#3b82f6" : "#cbd5e1"} strokeWidth="1.5" />
            <line x1="23" y1="12" x2="37" y2="12" stroke={isDragging ? "#93c5fd" : "#e2e8f0"} strokeWidth="2" strokeLinecap="round" />
            <line x1="23" y1="18" x2="33" y2="18" stroke={isDragging ? "#93c5fd" : "#e2e8f0"} strokeWidth="2" strokeLinecap="round" />
            <line x1="23" y1="24" x2="35" y2="24" stroke={isDragging ? "#93c5fd" : "#e2e8f0"} strokeWidth="2" strokeLinecap="round" />
            
            {/* Cloud banner background */}
            <path d="M10 38 C 10 34, 14 32, 20 32 C 23 27, 30 26, 35 29 C 40 28, 45 30, 48 34 C 51 36, 52 39, 50 42 C 49 44, 10 44, 10 38 Z" fill={isDragging ? "#eff6ff" : "#f8fafc"} stroke={isDragging ? "#93c5fd" : "#cbd5e1"} strokeWidth="1" />
            
            {/* Arrow upwards */}
            <path d="M30 42 L30 32 M26 36 L30 32 L34 36" stroke={isDragging ? "#3b82f6" : "#4f7df3"} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="text-xs font-bold text-slate-800 max-w-[210px] leading-normal">
            Upload a resume and provide a job description to begin analysis.
          </p>
          <p className="text-[10px] text-slate-400 font-semibold mt-1">
            Drag & drop files or <span className="text-primary hover:underline">browse</span>
          </p>
          <p className="text-[9px] text-slate-400 font-semibold mt-0.5">Supports PDF and DOCX (Max 10MB)</p>
        </div>
      ) : (
        <div className="h-48 flex items-center justify-center">
          <div className="w-full border border-slate-200 bg-white rounded-xl p-3.5 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3.5 min-w-0">
              <div className="bg-primary/5 text-primary p-2 rounded-xl border border-primary/10 flex-shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <span className="text-xs font-bold text-slate-800 block truncate" title={file.name}>
                  {file.name}
                </span>
                <span className="text-[10px] text-slate-400 font-semibold block mt-0.5">
                  {formatFileSize(file.size)}
                </span>
              </div>
            </div>
            <button
              onClick={onClear}
              className="text-slate-400 hover:text-red-500 p-1.5 rounded-lg hover:bg-slate-50 transition-all"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 border border-red-200/60 rounded-xl p-3 mt-1 font-semibold">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
