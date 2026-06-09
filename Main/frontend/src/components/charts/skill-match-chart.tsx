import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from "recharts";

interface SkillMatchChartProps {
  matchTypeCounts: Record<string, number>;
}

export const SkillMatchChart: React.FC<SkillMatchChartProps> = ({ matchTypeCounts }) => {
  const categories = [
    { key: "exact", label: "Exact Match", color: "#16a34a" },
    { key: "alias", label: "Alias Match", color: "#0d9488" },
    { key: "synonym", label: "Curated Synonym", color: "#2563eb" },
    { key: "semantic", label: "Semantic Embed", color: "#4f7df3" },
    { key: "partial", label: "Partial Token", color: "#eab308" },
    { key: "cluster", label: "Ontology Cluster", color: "#d946ef" },
  ];

  const data = categories.map((cat) => ({
    name: cat.label,
    Count: matchTypeCounts[cat.key] || 0,
    color: cat.color,
  })).filter(item => item.Count > 0 || true); // keep all for full scale visual

  return (
    <div className="w-full h-64 md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="radial"
          data={data}
          margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          barSize={12}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
          <XAxis 
            type="number"
            tick={{ fill: "#94a3b8", fontSize: 8 }}
            axisLine={{ stroke: "#e2e8f0" }}
            allowDecimals={false}
          />
          <YAxis 
            type="category"
            dataKey="name" 
            tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
            axisLine={{ stroke: "#e2e8f0" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(255, 255, 255, 0.95)",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              fontSize: "10px",
              color: "#0f172a",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
            }}
            cursor={{ fill: "rgba(79, 125, 243, 0.04)" }}
          />
          <Bar dataKey="Count" radius={[0, 4, 4, 0]} isAnimationActive={true} animationDuration={600} animationEasing="ease-out">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
