import React from "react";
import { useAnalysis, HistoryItem } from "../../stores/analysis-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Trash2, Play, ExternalLink, Calendar } from "lucide-react";
import { formatScore } from "../../lib/formatters";
import { MATCH_LEVEL_THEME } from "../../lib/constants";

export const AnalysisHistoryTable: React.FC = () => {
  const { history, loadFromHistory, deleteHistoryItem } = useAnalysis();

  const getMatchLevelVariant = (level: string) => {
    switch (level) {
      case "EXCELLENT":
      case "GOOD":
        return "success";
      case "MODERATE":
        return "warning";
      default:
        return "danger";
    }
  };

  if (history.length === 0) {
    return (
      <div className="text-center py-12 border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
        <Calendar className="w-8 h-8 text-slate-400 mx-auto mb-3" />
        <h3 className="text-sm font-bold text-slate-700">No match history</h3>
        <p className="text-xs text-slate-500 mt-1">Uploaded resume matches will show up here.</p>
      </div>
    );
  }

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
              <th className="px-5 py-3">Scan Date</th>
              <th className="px-5 py-3">Resume Filename</th>
              <th className="px-5 py-3">Job Role</th>
              <th className="px-5 py-3">Placement Fit</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-600 font-medium">
            {history.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/75 transition-colors">
                <td className="px-5 py-3.5 whitespace-nowrap text-slate-500">
                  {item.date}
                </td>
                <td className="px-5 py-3.5 truncate max-w-[200px] font-semibold text-slate-800">
                  {item.filename}
                </td>
                <td className="px-5 py-3.5 capitalize truncate max-w-[150px] text-slate-700">
                  {item.role === "not_specified" ? "Target Role" : item.role}
                </td>
                <td className="px-5 py-3.5">
                  <Badge variant={getMatchLevelVariant(item.payload.match_level)}>
                    {item.payload.match_level} ({Math.round(item.score)}%)
                  </Badge>
                </td>
                <td className="px-5 py-3.5 text-right space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => loadFromHistory(item)}
                    className="h-7 px-2.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5 mr-1" /> Load
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteHistoryItem(item.id)}
                    className="h-7 w-7 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
