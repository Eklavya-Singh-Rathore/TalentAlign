import React, { useState } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { Menu, X } from "lucide-react";
import { useAnalysis } from "../../stores/analysis-store";

export const DashboardShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { isLoading, loadingStep } = useAnalysis();

  return (
    <div data-print-role="root" className="flex h-screen w-screen overflow-hidden bg-background font-sans text-foreground antialiased selection:bg-primary/20 selection:text-primary">
      {/* Desktop Sidebar (Hidden on mobile) */}
      <div data-print-role="sidebar" className="hidden md:flex md:flex-shrink-0 h-full">
        <Sidebar />
      </div>

      {/* Mobile Sidebar overlay */}
      {mobileMenuOpen && (
        <div data-print-role="mobile-overlay" className="fixed inset-0 z-40 flex md:hidden">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm animate-fade-in"
            onClick={() => setMobileMenuOpen(false)}
          ></div>
          
          {/* Menu Panel */}
          <div className="relative flex w-full max-w-xs flex-1 flex-col bg-white pt-5 pb-4 z-50 animate-slide-in">
            <div className="absolute top-0 right-0 -mr-12 pt-2">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="ml-1 flex h-10 w-10 items-center justify-center rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              >
                <span className="sr-only">Close sidebar</span>
                <X className="h-6 w-6 text-white" aria-hidden="true" />
              </button>
            </div>
            <div className="h-full" onClick={() => setMobileMenuOpen(false)}>
              <Sidebar />
            </div>
          </div>
        </div>
      )}

      {/* Main content body wrapper */}
      <div data-print-role="content-wrapper" className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Header containing page context and mobile toggle */}
        <div data-print-role="header-bar" className="flex items-center w-full min-w-0">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(true)}
            className="px-4 text-slate-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary md:hidden hover:text-slate-800 transition-colors"
          >
            <span className="sr-only">Open sidebar</span>
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
          
          <div className="flex-1 min-w-0">
            <Header />
          </div>
        </div>

        {/* Primary Page Canvas */}
        <main data-print-role="main-canvas" className="flex-1 overflow-y-auto bg-slate-50/40 p-6 md:p-8 relative min-w-0">
          {isLoading && (
            <div className="mb-5 bg-primary/5 border border-primary/10 rounded-2xl p-4 flex items-center justify-between gap-4 animate-fade-in print-hide">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 border-2 border-primary/25 border-t-primary rounded-full animate-spin flex-shrink-0"></div>
                <div>
                  <h4 className="text-xs font-extrabold text-slate-900 uppercase tracking-wider">Analyzing Candidate Alignment</h4>
                  <p className="text-primary text-[10px] font-bold mt-0.5 animate-pulse uppercase tracking-wide">{loadingStep}</p>
                </div>
              </div>
              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest hidden sm:inline">
                Empirical Scoring Engine Active
              </span>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
};
