"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { SectionHeader } from "@/components/PageHeader";

interface OccupancyDataPoint {
  time: string;
  occupancy: number;
}

interface ZoneUtilization {
  name: string;
  utilization: number;
  vacant: number;
}

interface HourHeatmapData {
  hour: number;
  avgOccupancy: number;
}

interface AnalyticsChartsProps {
  hourlyOccupancy?: OccupancyDataPoint[];
  zoneUtilization?: ZoneUtilization[];
  peakHours?: HourHeatmapData[];
}

const CHART_COLORS = {
  accent: "var(--accent)",
  occupied: "var(--occupied)",
  vacant: "var(--vacant)",
  muted: "var(--text-muted)",
  grid: "var(--border-subtle)",
  background: "var(--bg-tertiary)",
};

function getHeatmapColor(value: number): string {
  if (value >= 80) return "var(--occupied)";
  if (value >= 60) return "var(--warning)";
  if (value >= 40) return "var(--accent)";
  return "var(--vacant)";
}

function formatHour(hour: number): string {
  if (hour === 0) return "12AM";
  if (hour === 12) return "12PM";
  return hour > 12 ? `${hour - 12}PM` : `${hour}AM`;
}

export function OccupancyTrendChart({ data }: { data: OccupancyDataPoint[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-sm text-[var(--text-muted)]">
        No occupancy trend data available
      </div>
    );
  }

  return (
    <section aria-label="Occupancy trend chart">
      <SectionHeader title="Occupancy Trend" subtitle="Last 24 hours" />
      <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
              tickLine={false}
              axisLine={{ stroke: CHART_COLORS.grid }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
              tickLine={false}
              axisLine={{ stroke: CHART_COLORS.grid }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--bg-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: 0,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--text-primary)", fontWeight: 600 }}
              itemStyle={{ color: "var(--accent)" }}
              formatter={(value) => [`${Number(value).toFixed(1)}%`, "Occupancy"]}
            />
            <Line
              type="monotone"
              dataKey="occupancy"
              stroke={CHART_COLORS.accent}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: CHART_COLORS.accent }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function ZoneUtilizationChart({ data }: { data: ZoneUtilization[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-sm text-[var(--text-muted)]">
        No zone utilization data available
      </div>
    );
  }

  return (
    <section aria-label="Zone utilization chart">
      <SectionHeader title="Zone Utilization" subtitle="Current state" />
      <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} layout="vertical" margin={{ top: 10, right: 10, left: 60, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
              tickLine={false}
              axisLine={{ stroke: CHART_COLORS.grid }}
              tickFormatter={(value) => `${value}%`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
              tickLine={false}
              axisLine={{ stroke: CHART_COLORS.grid }}
              width={55}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--bg-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: 0,
                fontSize: 12,
              }}
              formatter={(value, name) => [
                `${Number(value).toFixed(1)}%`,
                name === "utilization" ? "Occupied" : "Vacant",
              ]}
            />
            <Bar dataKey="utilization" stackId="a" fill={CHART_COLORS.occupied} radius={[0, 2, 2, 0]} />
            <Bar dataKey="vacant" stackId="a" fill={CHART_COLORS.vacant} radius={[0, 2, 2, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function PeakHoursHeatmap({ data }: { data: HourHeatmapData[] }) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) {
      // Deterministic mock data based on typical campus parking patterns
      const typicalPattern: Record<number, number> = {
        0: 15, 1: 12, 2: 10, 3: 10, 4: 12, 5: 18,
        6: 35, 7: 55, 8: 78, 9: 85, 10: 82, 11: 70,
        12: 65, 13: 72, 14: 75, 15: 80, 16: 85, 17: 78,
        18: 55, 19: 40, 20: 30, 21: 25, 22: 20, 23: 18,
      };
      return Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        avgOccupancy: typicalPattern[i] ?? 50,
      }));
    }
    return data;
  }, [data]);

  return (
    <section aria-label="Peak hours heatmap">
      <SectionHeader title="Peak Hours" subtitle="Average occupancy by hour" />
      <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
        <div className="grid grid-cols-12 gap-1" role="img" aria-label="Hourly occupancy heatmap">
          {chartData.slice(6, 22).map((item) => (
            <div
              key={item.hour}
              className="flex flex-col items-center"
              title={`${formatHour(item.hour)}: ${item.avgOccupancy.toFixed(0)}% avg`}
            >
              <div
                className="mb-1 h-8 w-full border border-[var(--border-subtle)]"
                style={{ backgroundColor: getHeatmapColor(item.avgOccupancy) }}
              />
              <span className="text-[10px] text-[var(--text-muted)]">{formatHour(item.hour)}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-center gap-4 text-xs text-[var(--text-muted)]">
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 border border-[var(--border-subtle)]" style={{ backgroundColor: "var(--vacant)" }} />
            <span>&lt;40%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 border border-[var(--border-subtle)]" style={{ backgroundColor: "var(--accent)" }} />
            <span>40-60%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 border border-[var(--border-subtle)]" style={{ backgroundColor: "var(--warning)" }} />
            <span>60-80%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 border border-[var(--border-subtle)]" style={{ backgroundColor: "var(--occupied)" }} />
            <span>&gt;80%</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function AnalyticsCharts({ hourlyOccupancy, zoneUtilization, peakHours }: AnalyticsChartsProps) {
  const mockHourlyData = useMemo<OccupancyDataPoint[]>(
    () =>
      hourlyOccupancy ||
      Array.from({ length: 24 }, (_, i) => ({
        time: `${String(i).padStart(2, "0")}:00`,
        // Deterministic pattern: morning peak, lunch dip, afternoon peak
        occupancy: 30 + Math.sin(i * 0.5) * 25 + (i % 3) * 3,
      })),
    [hourlyOccupancy]
  );

  const mockZoneData = useMemo<ZoneUtilization[]>(
    () =>
      zoneUtilization || [
        { name: "Zone A1", utilization: 75, vacant: 25 },
        { name: "Zone A2", utilization: 45, vacant: 55 },
        { name: "East Wing", utilization: 90, vacant: 10 },
        { name: "West Wing", utilization: 30, vacant: 70 },
      ],
    [zoneUtilization]
  );

  return (
    <div className="mb-8 space-y-6">
      <OccupancyTrendChart data={mockHourlyData} />
      <div className="grid gap-6 lg:grid-cols-2">
        <ZoneUtilizationChart data={mockZoneData} />
        <PeakHoursHeatmap data={peakHours || []} />
      </div>
    </div>
  );
}
