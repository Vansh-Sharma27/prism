"use client";

import { useState } from "react";
import { SectionHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import {
  fetchLotPrediction,
  fetchLotRecommendation,
  type LotPredictionData,
  type LotRecommendationData,
  type PredictionZone,
  type RecommendationZone,
} from "@/lib/api";
import { BrainCircuit, Clock3, MapPinned, Route, Sparkles } from "lucide-react";

const DAY_OPTIONS = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
];

const DEFAULT_DESTINATIONS = ["Library", "Admin Block", "Cafeteria", "Innovation Lab", "Seminar Hall"];

const LOT_DESTINATIONS: Record<string, string[]> = {
  "lot-a": ["Library", "Admin Block", "Cafeteria"],
  "lot-b": ["Innovation Lab", "Seminar Hall", "Cafeteria"],
};

function trendStyles(trend: PredictionZone["trend"] | RecommendationZone["trend"]) {
  if (trend === "filling") {
    return {
      label: "Filling",
      textClass: "text-[var(--occupied)]",
      borderClass: "border-[var(--occupied)]/30",
      backgroundClass: "bg-[var(--occupied)]/10",
    };
  }
  if (trend === "clearing") {
    return {
      label: "Clearing",
      textClass: "text-[var(--vacant)]",
      borderClass: "border-[var(--vacant)]/30",
      backgroundClass: "bg-[var(--vacant)]/10",
    };
  }
  return {
    label: "Stable",
    textClass: "text-[var(--accent)]",
    borderClass: "border-[var(--accent)]/30",
    backgroundClass: "bg-[var(--accent)]/10",
  };
}

function formatDayLabel(day: string): string {
  return day.length > 0 ? `${day[0].toUpperCase()}${day.slice(1)}` : day;
}

function meterWidth(value: number): string {
  return `${Math.max(0, Math.min(100, value))}%`;
}

function InsightError({ message }: { message: string }) {
  return (
    <div className="border border-[var(--occupied)]/30 bg-[var(--occupied)]/10 px-3 py-2 text-sm text-[var(--occupied)]">
      {message}
    </div>
  );
}

function InsightCard({
  icon: Icon,
  eyebrow,
  title,
  description,
  children,
}: {
  icon: typeof BrainCircuit;
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-[var(--border-default)] bg-[var(--bg-secondary)]" aria-label={title}>
      <div className="border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center border border-[var(--border-default)] bg-[var(--bg-secondary)] text-[var(--accent)]">
            <Icon size={18} />
          </div>
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
              {eyebrow}
            </p>
            <h3 className="font-display text-lg font-bold uppercase tracking-wider text-[var(--text-primary)]">
              {title}
            </h3>
          </div>
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{description}</p>
      </div>
      <div className="space-y-4 px-4 py-4">{children}</div>
    </section>
  );
}

function ForecastRow({ zone }: { zone: PredictionZone }) {
  const trend = trendStyles(zone.trend);

  return (
    <article className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h4 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {zone.name}
          </h4>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            {zone.totalSlots} slots tracked in this zone
          </p>
        </div>
        <div className={`border px-2 py-1 text-[11px] font-display font-semibold uppercase tracking-wider ${trend.textClass} ${trend.borderClass} ${trend.backgroundClass}`}>
          {trend.label}
        </div>
      </div>

      <div className="space-y-2">
        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-[var(--text-muted)]">
            <span>Current</span>
            <span className="font-mono text-[var(--text-primary)]">{zone.currentOccupancyPct.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-[var(--bg-primary)]">
            <div className="h-full bg-[var(--accent-dim)]" style={{ width: meterWidth(zone.currentOccupancyPct) }} />
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-[var(--text-muted)]">
            <span>Predicted</span>
            <span className="font-mono text-[var(--accent)]">{zone.predictedOccupancyPct.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-[var(--bg-primary)]">
            <div className="h-full bg-[var(--accent)]" style={{ width: meterWidth(zone.predictedOccupancyPct) }} />
          </div>
        </div>
      </div>
    </article>
  );
}

function RecommendationRow({
  zone,
  rankLabel,
}: {
  zone: RecommendationZone;
  rankLabel: string;
}) {
  const trend = trendStyles(zone.trend);
  const scoreWidth = Math.max(18, 100 - Math.min(zone.score, 100));

  return (
    <article className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="font-display text-[11px] font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
            {rankLabel}
          </p>
          <h4 className="mt-1 font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {zone.name}
          </h4>
        </div>
        <div className={`border px-2 py-1 text-[11px] font-display font-semibold uppercase tracking-wider ${trend.textClass} ${trend.borderClass} ${trend.backgroundClass}`}>
          {trend.label}
        </div>
      </div>

      <dl className="grid grid-cols-3 gap-2 text-sm">
        <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-2">
          <dt className="label-quiet">Walk</dt>
          <dd className="mt-1 font-mono text-[var(--text-primary)]">{zone.estimatedWalkMinutes} min</dd>
        </div>
        <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-2">
          <dt className="label-quiet">Load</dt>
          <dd className="mt-1 font-mono text-[var(--accent)]">{zone.predictedOccupancyPct.toFixed(1)}%</dd>
        </div>
        <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-2">
          <dt className="label-quiet">Score</dt>
          <dd className="mt-1 font-mono text-[var(--text-primary)]">{zone.score.toFixed(2)}</dd>
        </div>
      </dl>

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>Route efficiency</span>
          <span className="font-mono text-[var(--accent)]">{zone.score.toFixed(2)}</span>
        </div>
        <div className="h-2 bg-[var(--bg-primary)]">
          <div className="h-full bg-[var(--accent)]" style={{ width: `${scoreWidth}%` }} />
        </div>
      </div>
    </article>
  );
}

interface LotInsightsPanelProps {
  lotId: string;
  lotName: string;
}

export function LotInsightsPanel({ lotId, lotName }: LotInsightsPanelProps) {
  const [day, setDay] = useState("wednesday");
  const [time, setTime] = useState("10:00");
  const [destination, setDestination] = useState(
    (LOT_DESTINATIONS[lotId] || DEFAULT_DESTINATIONS)[0]
  );
  const [prediction, setPrediction] = useState<LotPredictionData | null>(null);
  const [recommendation, setRecommendation] = useState<LotRecommendationData | null>(null);
  const [predictionError, setPredictionError] = useState("");
  const [recommendationError, setRecommendationError] = useState("");
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [recommendationLoading, setRecommendationLoading] = useState(false);

  const destinationOptions = LOT_DESTINATIONS[lotId] || DEFAULT_DESTINATIONS;

  async function handlePrediction() {
    setPredictionLoading(true);
    setPredictionError("");

    try {
      const response = await fetchLotPrediction(lotId, day, time);
      setPrediction(response);
    } catch (error) {
      setPredictionError(error instanceof Error ? error.message : "Unable to load prediction.");
    } finally {
      setPredictionLoading(false);
    }
  }

  async function handleRecommendation() {
    const normalizedDestination = destination.trim();
    if (!normalizedDestination) {
      setRecommendationError("Select a destination before requesting a recommendation.");
      return;
    }

    setRecommendationLoading(true);
    setRecommendationError("");

    try {
      const response = await fetchLotRecommendation(lotId, normalizedDestination, day, time);
      setRecommendation(response);
    } catch (error) {
      setRecommendationError(error instanceof Error ? error.message : "Unable to load recommendation.");
    } finally {
      setRecommendationLoading(false);
    }
  }

  return (
    <section className="mb-8" aria-label="Lot intelligence">
      <SectionHeader title="Lot Intelligence" subtitle="Forecast + Routing" />

      <div className="grid gap-5 xl:grid-cols-2">
        <InsightCard
          icon={BrainCircuit}
          eyebrow="Day 9"
          title="Predicted Zone Load"
          description="Run the mock forecasting model against the current lot state to estimate near-term occupancy pressure by zone."
        >
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <label className="block">
              <span className="mb-1 block text-xs font-display font-semibold uppercase tracking-[0.28em] text-[var(--text-muted)]">
                Forecast Day
              </span>
              <select
                aria-label="Forecast Day"
                value={day}
                onChange={(event) => setDay(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
              >
                {DAY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-xs font-display font-semibold uppercase tracking-[0.28em] text-[var(--text-muted)]">
                Forecast Time
              </span>
              <input
                aria-label="Forecast Time"
                type="time"
                value={time}
                onChange={(event) => setTime(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
              />
            </label>

            <div className="flex items-end">
              <button
                type="button"
                onClick={handlePrediction}
                disabled={predictionLoading}
                className="w-full border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-sm font-display font-semibold uppercase tracking-wider text-[var(--bg-primary)] transition-colors hover:bg-[var(--accent-dim)] disabled:cursor-not-allowed disabled:border-[var(--border-default)] disabled:bg-[var(--bg-tertiary)] disabled:text-[var(--text-muted)]"
              >
                {predictionLoading ? "Running..." : "Run Prediction"}
              </button>
            </div>
          </div>

          {predictionError ? <InsightError message={predictionError} /> : null}

          <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-3">
            <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-muted)]">
              <span className="inline-flex items-center gap-2">
                <Sparkles size={14} className="text-[var(--accent)]" />
                {prediction?.model.status === "mock" ? "Mock model" : "Forecast model"}
              </span>
              <span className="inline-flex items-center gap-2">
                <Clock3 size={14} className="text-[var(--accent)]" />
                {formatDayLabel(prediction?.predictedFor.day || day)} at {prediction?.predictedFor.time || time}
              </span>
              <span className="inline-flex items-center gap-2">
                <MapPinned size={14} className="text-[var(--accent)]" />
                {prediction?.lotName || lotName}
              </span>
            </div>
          </div>

          {prediction ? (
            <div className="space-y-3">
              {prediction.zones.map((zone) => (
                <ForecastRow key={zone.zoneId} zone={zone} />
              ))}
              <p className="text-xs text-[var(--text-muted)]">{prediction.model.note}</p>
            </div>
          ) : (
            <EmptyState
              variant="no-results"
              title="No Forecast Yet"
              description="Choose a day and time, then run the prediction model to compare projected zone load."
            />
          )}
        </InsightCard>

        <InsightCard
          icon={Route}
          eyebrow="Day 9"
          title="Best Parking Recommendation"
          description="Rank the most useful zone for a destination using projected occupancy and estimated walking distance."
        >
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <label className="block">
              <span className="mb-1 block text-xs font-display font-semibold uppercase tracking-[0.28em] text-[var(--text-muted)]">
                Destination
              </span>
              <select
                aria-label="Destination"
                value={destination}
                onChange={(event) => setDestination(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
              >
                {destinationOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-end">
              <button
                type="button"
                onClick={handleRecommendation}
                disabled={recommendationLoading}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2 text-sm font-display font-semibold uppercase tracking-wider text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:cursor-not-allowed disabled:text-[var(--text-muted)]"
              >
                {recommendationLoading ? "Calculating..." : "Recommend Zone"}
              </button>
            </div>
          </div>

          {recommendationError ? <InsightError message={recommendationError} /> : null}

          {recommendation ? (
            <div className="space-y-4">
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-3">
                <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-muted)]">
                  <span className="inline-flex items-center gap-2">
                    <MapPinned size={14} className="text-[var(--accent)]" />
                    Destination: {recommendation.destination}
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <Clock3 size={14} className="text-[var(--accent)]" />
                    {formatDayLabel(recommendation.predictedFor.day)} at {recommendation.predictedFor.time}
                  </span>
                </div>
              </div>

              {recommendation.recommendedZone ? (
                <RecommendationRow zone={recommendation.recommendedZone} rankLabel="Primary Route" />
              ) : (
                <EmptyState
                  variant="error"
                  title="No Recommendation Found"
                  description="The recommendation engine did not return a matching zone for this request."
                />
              )}

              {recommendation.alternatives.length > 0 ? (
                <div className="space-y-3">
                  <p className="font-display text-xs font-semibold uppercase tracking-[0.28em] text-[var(--text-muted)]">
                    Alternatives
                  </p>
                  {recommendation.alternatives.map((zone, index) => (
                    <RecommendationRow
                      key={`${zone.zoneId}-${zone.name}`}
                      zone={zone}
                      rankLabel={`Option ${index + 2}`}
                    />
                  ))}
                </div>
              ) : null}

              <p className="text-xs text-[var(--text-muted)]">{recommendation.engine.note}</p>
            </div>
          ) : (
            <EmptyState
              variant="no-results"
              title="Recommendation Ready"
              description="Pick a destination and run the routing helper to surface the most efficient parking zone."
            />
          )}
        </InsightCard>
      </div>
    </section>
  );
}
