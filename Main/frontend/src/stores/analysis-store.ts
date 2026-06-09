import React, { createContext, useContext, useState, useEffect } from "react";
import { AnalysisPayload } from "../lib/types";
import { analyzeResumeJD } from "../lib/api";

export interface HistoryItem {
  id: string;
  date: string;
  filename: string;
  role: string;
  score: number;
  payload: AnalysisPayload;
}

export type ActiveTabType = "upload" | "dashboard" | "scoring" | "gaps" | "recommendations" | "export";

export interface AnalysisState {
  currentAnalysis: AnalysisPayload | null;
  isLoading: boolean;
  loadingStep: string;
  error: string | null;
  resumeFile: File | null;
  jdText: string;
  activeTab: ActiveTabType;
  history: HistoryItem[];
  setResumeFile: (file: File | null) => void;
  setJdText: (text: string) => void;
  setActiveTab: (tab: ActiveTabType) => void;
  runAnalysis: (file: File, jd: string) => Promise<void>;
  loadFromHistory: (item: HistoryItem) => void;
  clearAnalysis: () => void;
  deleteHistoryItem: (id: string) => void;
}

const AnalysisContext = createContext<AnalysisState | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisPayload | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStep, setLoadingStep] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [resumeFile, setResumeFileState] = useState<File | null>(null);
  const [jdText, setJdTextState] = useState<string>("");
  const [activeTab, setActiveTab] = useState<ActiveTabType>("upload");
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("talentalign_history");
      if (stored) {
        setHistory(JSON.parse(stored));
      }
    } catch (err) {
      console.error("Failed to load history from localStorage:", err);
    }
  }, []);

  const setResumeFile = (file: File | null) => {
    setResumeFileState(file);
    if (!file && !currentAnalysis) {
      setError(null);
    }
  };

  const setJdText = (text: string) => {
    setJdTextState(text);
  };

  const clearAnalysis = () => {
    setCurrentAnalysis(null);
    setResumeFileState(null);
    setJdTextState("");
    setError(null);
    setActiveTab("upload");
  };

  const deleteHistoryItem = (id: string) => {
    const target = history.find((h) => h.id === id);
    const updated = history.filter((item) => item.id !== id);
    setHistory(updated);
    localStorage.setItem("talentalign_history", JSON.stringify(updated));
    if (target && currentAnalysis === target.payload) {
      clearAnalysis();
    }
  };

  const runAnalysis = async (file: File, jd: string) => {
    setIsLoading(true);
    setError(null);
    setResumeFileState(file);
    setJdTextState(jd);
    setActiveTab("dashboard");

    const steps = [
      "Normalizing resume text...",
      "Filtering job description boilerplate...",
      "Extracting skills and credentials...",
      "Performing semantic alignment checks...",
      "Computing score components...",
      "Assembling results payload...",
    ];

    let stepIndex = 0;
    setLoadingStep(steps[stepIndex]);

    const stepInterval = setInterval(() => {
      if (stepIndex < steps.length - 1) {
        stepIndex++;
        setLoadingStep(steps[stepIndex]);
      }
    }, 1200);

    try {
      const result = await analyzeResumeJD(file, jd);

      clearInterval(stepInterval);
      setCurrentAnalysis(result);
      setActiveTab("dashboard");

      // Save to local history
      const historyItem: HistoryItem = {
        id: Math.random().toString(36).substring(2, 9),
        date: new Date().toLocaleString(),
        filename: file.name,
        role: result.role_title || result.jd_extraction?.role_title || "not_specified",
        score: result.placement_score,
        payload: result,
      };

      const newHistory = [historyItem, ...history.slice(0, 19)]; // Keep max 20 items
      setHistory(newHistory);
      localStorage.setItem("talentalign_history", JSON.stringify(newHistory));
    } catch (err: any) {
      clearInterval(stepInterval);
      setError(err?.message || "An unexpected error occurred during analysis.");
      setActiveTab("upload");
    } finally {
      setIsLoading(false);
      setLoadingStep("");
    }
  };

  const loadFromHistory = (item: HistoryItem) => {
    setCurrentAnalysis(item.payload);
    setJdTextState(item.payload.jd_extraction?.required_skills.join(", ") || "");
    setError(null);
    setActiveTab("dashboard");
  };

  return React.createElement(
    AnalysisContext.Provider,
    {
      value: {
        currentAnalysis,
        isLoading,
        loadingStep,
        error,
        resumeFile,
        jdText,
        activeTab,
        history,
        setResumeFile,
        setJdText,
        setActiveTab,
        runAnalysis,
        loadFromHistory,
        clearAnalysis,
        deleteHistoryItem,
      },
    },
    children
  );
};

export const useAnalysis = () => {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error("useAnalysis must be used within an AnalysisProvider");
  }
  return context;
};
