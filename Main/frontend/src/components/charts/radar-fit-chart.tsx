import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip
} from "recharts";
import { COMPONENT_LABELS } from "../../lib/constants";

interface RadarFitChartProps {
  breakdown: Array<{
    component: string;
    weight: number;
    component_score: number;
    score_achieved: number;
    active: boolean;
  }>;
}

export const RadarFitChart: React.FC<RadarFitChartProps> = ({ breakdown }) => {
  // Normalize data for Radar
  const data = breakdown.map((item) => ({
    subject: COMPONENT_LABELS[item.component] || item.component,
    score: item.active ? Math.round(item.component_score * 100) : 0,
    weight: Math.round(item.weight * 100),
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 border border-slate-200 p-2.5 rounded-xl shadow-md text-[10px]">
          <p className="font-bold text-slate-800 mb-1">{payload[0].payload.subject}</p>
          <p className="text-primary font-bold">Alignment Score: {payload[0].value}%</p>
          <p className="text-slate-400 font-semibold">Component Weight: {payload[1].value}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64 md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis 
            dataKey="subject" 
            tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
          />
          <PolarRadiusAxis 
            angle={30} 
            domain={[0, 100]} 
            tick={{ fill: "#94a3b8", fontSize: 8 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#4f7df3"
            fill="#4f7df3"
            fillOpacity={0.15}
            isAnimationActive={true}
            animationDuration={600}
            animationEasing="ease-out"
          />
          <Radar
            name="Weight"
            dataKey="weight"
            stroke="#64748b"
            fill="#64748b"
            fillOpacity={0.03}
            isAnimationActive={true}
            animationDuration={600}
            animationEasing="ease-out"
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
