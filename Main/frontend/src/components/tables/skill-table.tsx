import React, { useState } from "react";
import { Badge } from "../ui/badge";
import { Search, Compass, CheckCircle2 } from "lucide-react";
import { MATCH_LEVEL_THEME } from "../../lib/constants";

interface MatchedSkill {
  resume_phrase: string;
  jd_phrase: string;
  similarity: number;
  match_score: number;
  match_type: string;
}

interface SkillTableProps {
  matchedSkills: MatchedSkill[];
}

export const SkillTable: React.FC<SkillTableProps> = ({ matchedSkills }) => {
  const [filterQuery, setFilterQuery] = useState("");

  const filtered = matchedSkills.filter(
    (skill) =>
      skill.resume_phrase.toLowerCase().includes(filterQuery.toLowerCase()) ||
      skill.jd_phrase.toLowerCase().includes(filterQuery.toLowerCase()) ||
      skill.match_type.toLowerCase().includes(filterQuery.toLowerCase())
  );

  const getMatchTypeVariant = (type: string) => {
    switch (type.toLowerCase()) {
      case "exact":
      case "alias":
        return "success";
      case "synonym":
      case "semantic":
        return "primary";
      default:
        return "secondary";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-xl px-3.5 py-1.5 max-w-sm shadow-sm focus-within:ring-2 focus-within:ring-primary/20 transition-all">
        <Search className="w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={filterQuery}
          onChange={(e) => setFilterQuery(e.target.value)}
          placeholder="Filter matched skills..."
          className="bg-transparent text-xs text-slate-700 outline-none w-full placeholder-slate-400 font-medium"
        />
      </div>

      <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="px-5 py-3">Resume Phrase</th>
                <th className="px-5 py-3">JD Match Requirement</th>
                <th className="px-5 py-3">Layer Method</th>
                <th className="px-5 py-3 text-right">Match Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-600 font-medium">
              {filtered.length > 0 ? (
                filtered.map((skill, index) => (
                  <tr key={index} className="hover:bg-slate-50/75 transition-colors">
                    <td className="px-5 py-3.5 capitalize font-semibold text-slate-800">
                      {skill.resume_phrase}
                    </td>
                    <td className="px-5 py-3.5 capitalize text-slate-500">
                      {skill.jd_phrase}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={getMatchTypeVariant(skill.match_type)}>
                        {skill.match_type}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 text-right font-bold text-indigo-600">
                      {skill.match_score ? `${Math.round(skill.match_score * 100)}%` : "100%"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-slate-400 font-medium">
                    No matched skills found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
