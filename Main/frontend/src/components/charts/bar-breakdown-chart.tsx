import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import { COMPONENT_LABELS } from "../../lib/constants";

interface BarBreakdownChartProps {
  breakdown: Array<{
    component: string;
    weight: number;
    component_score: number;
    score_achieved: number;
    active: boolean;
  }>;
}

export const BarBreakdownChart: React.FC<BarBreakdownChartProps> = ({ breakdown }) => {
  const data = breakdown.map((item) => ({
    name: item.component,
    fullName: COMPONENT_LABELS[item.component] || item.component,
    "Nominal Weight %": Math.round(item.weight * 100),
    "Achieved Score Contribution %": item.active ? Math.round(item.score_achieved * 100) : 0,
  }));

  return (
    <div className="w-full h-64 md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          barSize={16}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="name" 
            tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
            axisLine={{ stroke: "#e2e8f0" }}
          />
          <YAxis 
            tick={{ fill: "#94a3b8", fontSize: 8 }}
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
          <Legend 
            wrapperStyle={{ fontSize: 9, fontWeight: 600, paddingTop: 10 }}
            iconSize={8}
          />
          <Bar dataKey="Nominal Weight %" fill="#64748b" radius={[4, 4, 0, 0]} opacity={0.35} isAnimationActive={true} animationDuration={600} animationEasing="ease-out" />
          <Bar dataKey="Achieved Score Contribution %" fill="#4f7df3" radius={[4, 4, 0, 0]} isAnimationActive={true} animationDuration={600} animationEasing="ease-out" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
