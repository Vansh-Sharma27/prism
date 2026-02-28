"use client";

import { Navbar } from "@/components/Navbar";
import { PageHeader } from "@/components/PageHeader";
import { Server, Wifi, Database, Bell, Shield, Cpu, ChevronDown } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <PageHeader
          title="System Configuration"
          subtitle="Manage connections, sensors, and system settings"
        />

        <div className="grid gap-4 lg:grid-cols-2">
          <ConfigCard
            icon={Server}
            title="MQTT Broker"
            description="Message queue connection settings"
            status="Connected"
            statusColor="var(--vacant)"
            details={[
              { label: "Host", value: "localhost:1883" },
              { label: "Protocol", value: "MQTT 3.1.1" },
              { label: "Keepalive", value: "60s" },
              { label: "QoS", value: "1" },
            ]}
          />
          <ConfigCard
            icon={Database}
            title="Database"
            description="PostgreSQL connection and health"
            status="Healthy"
            statusColor="var(--vacant)"
            details={[
              { label: "Host", value: "localhost:5432" },
              { label: "DB", value: "prism_db" },
              { label: "Pool Size", value: "10" },
              { label: "Latency", value: "2ms" },
            ]}
          />
          <ConfigCard
            icon={Wifi}
            title="Sensor Network"
            description="ESP32 nodes and connectivity"
            status="5/6 Online"
            statusColor="var(--warning)"
            details={[
              { label: "Nodes", value: "2 active" },
              { label: "Sensors", value: "6 total" },
              { label: "Offline", value: "1 (ESP32-03)" },
              { label: "Avg RSSI", value: "-47 dBm" },
            ]}
          />
          <ConfigCard
            icon={Cpu}
            title="Processing"
            description="Backend API and ML services"
            status="Running"
            statusColor="var(--vacant)"
            details={[
              { label: "API", value: "Flask 3.0" },
              { label: "Workers", value: "4 threads" },
              { label: "Uptime", value: "3d 14h" },
              { label: "Memory", value: "142 MB" },
            ]}
          />
          <ConfigCard
            icon={Bell}
            title="Alerts"
            description="Notification settings"
            status="Enabled"
            statusColor="var(--accent)"
            details={[
              { label: "Email", value: "Off" },
              { label: "Webhook", value: "Off" },
              { label: "Threshold", value: "90%" },
              { label: "Cooldown", value: "5 min" },
            ]}
          />
          <ConfigCard
            icon={Shield}
            title="Security"
            description="Authentication and access"
            status="Secured"
            statusColor="var(--vacant)"
            details={[
              { label: "Auth", value: "JWT" },
              { label: "SSL", value: "Enabled" },
              { label: "CORS", value: "Restricted" },
              { label: "Rate Limit", value: "100/min" },
            ]}
          />
        </div>
      </main>
    </div>
  );
}

function ConfigCard({
  icon: Icon,
  title,
  description,
  status,
  statusColor,
  details,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  description: string;
  status: string;
  statusColor: string;
  details: { label: string; value: string }[];
}) {
  const [expanded, setExpanded] = useState(false);
  const visibleDetails = expanded ? details : details.slice(0, 2);
  const detailsId = `config-details-${title.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] transition-all duration-200 hover:border-[var(--accent)]/50 group animate-scale-in">
      {/* Top accent */}
      <div className="h-1 transition-all group-hover:h-1.5" style={{ backgroundColor: statusColor }} />

      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center border border-[var(--border-default)] bg-[var(--bg-tertiary)] transition-all group-hover:border-[var(--accent)]/30 group-hover:bg-[var(--bg-elevated)]">
              <Icon size={20} className="text-[var(--accent)]" />
            </div>
            <div>
              <h3 className="font-bold uppercase tracking-wide text-[var(--text-primary)] font-display group-hover:text-[var(--accent)] transition-colors">
                {title}
              </h3>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">{description}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-sm"
              style={{ backgroundColor: statusColor }}
            />
            <span
              className="font-mono text-xs"
              style={{ color: statusColor }}
            >
              {status}
            </span>
          </div>
        </div>

        {/* Details - expandable */}
        <div id={detailsId} className="mt-4 grid grid-cols-2 gap-2">
          {visibleDetails.map((detail) => (
            <div
              key={detail.label}
              className="flex items-center justify-between px-3 py-2 bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] transition-all hover:border-[var(--border-default)]"
            >
              <span className="label-quiet">
                {detail.label}
              </span>
              <span className="font-mono text-xs text-[var(--text-secondary)]">
                {detail.value}
              </span>
            </div>
          ))}
        </div>

        {/* Expand toggle */}
        {details.length > 2 && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors cursor-pointer"
            aria-expanded={expanded}
            aria-controls={detailsId}
          >
            <span className="font-display uppercase tracking-wider text-[10px] font-semibold">
              {expanded ? "Less" : `${details.length - 2} more`}
            </span>
            <ChevronDown
              size={14}
              className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
            />
          </button>
        )}
      </div>
    </div>
  );
}
