"use client";

import React, { useEffect, useState } from "react";
import { DashboardShell } from "../../components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { checkHealth, HealthResponse } from "../../lib/api";
import { Settings, ShieldCheck, Database, HardDrive, Trash2, Cpu } from "lucide-react";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHealth();
  }, []);

  const handleClearHistory = () => {
    if (confirm("Are you sure you want to clear your local history of resume match scans?")) {
      localStorage.removeItem("talentalign_history");
      window.location.reload();
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-primary/10 p-2.5 rounded-xl text-primary border border-primary/20">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">System Settings</h2>
            <p className="text-xs text-slate-500 font-semibold">Configure alignment engines and clear cached database metrics.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Active Backend Engine Status */}
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary" /> Active Matching Engines
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Current runtime models loaded in the backend pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs font-semibold text-slate-600">
              {loading ? (
                <div className="animate-pulse h-12 bg-slate-50 rounded-lg"></div>
              ) : health ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b border-slate-100">
                    <span className="text-slate-400">Service Name</span>
                    <span className="text-slate-800">{health.service}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-100">
                    <span className="text-slate-400">Service Version</span>
                    <Badge variant="secondary">{health.version}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-100">
                    <span className="text-slate-400">Embedding Engine</span>
                    <Badge variant="primary">{health.embedding_backend.toUpperCase()}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-slate-400">LLM Validation Gate</span>
                    <Badge variant={health.llm_backend === "none" ? "secondary" : "success"}>
                      {health.llm_backend.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-red-50 border border-red-200 text-red-650 rounded-lg text-center font-bold">
                  Failed to fetch backend configuration details.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Local Storage & Cache */}
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-primary" /> Cache & Storage Management
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Manage locally cached files and scan history.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <p className="text-slate-500 leading-relaxed font-semibold">
                By default, candidate resumes and alignment score matrices are stored locally inside the browser's `localStorage` for rapid reloading.
              </p>
              
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-4">
                <div>
                  <span className="font-bold text-slate-900 block">Reset Profile History</span>
                  <span className="text-[10px] text-slate-400 font-semibold block mt-0.5">
                    Deletes all past match evaluations and clear the recent history cache.
                  </span>
                </div>
                
                <Button 
                  variant="danger" 
                  size="sm" 
                  onClick={handleClearHistory}
                  className="flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear Cache
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}
