"use client";

import { useEffect, useState } from "react";

interface Props {
  jobId: string;
  filename: string;
  initialStatus: string;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

function getWebSocketUrl(jobId: string): string {
  const url = new URL(API_URL);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";

  return `${protocol}//${url.host}/ws/${jobId}`;
}

const STATUS_STYLES: Record<string, string> = {
  queued:
    "border-[var(--border)] bg-[var(--surface)] text-[var(--muted-foreground)]",
  processing:
    "border-[var(--accent)] bg-[color-mix(in_oklab,var(--surface)_82%,var(--accent)_18%)] text-[var(--foreground)]",
  completed:
    "border-[var(--border)] bg-[color-mix(in_oklab,var(--surface)_88%,rgb(34_197_94)_12%)] text-[var(--foreground)]",
  failed:
    "border-[var(--border)] bg-[color-mix(in_oklab,var(--surface)_86%,rgb(239_68_68)_14%)] text-[var(--foreground)]",
};

export function JobCard({ jobId, filename, initialStatus }: Props) {
  const [status, setStatus] = useState(initialStatus);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(getWebSocketUrl(jobId));

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as { status?: string };
      if (data.status) {
        setStatus(data.status);
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      ws.close();
    };
  }, [jobId]);

  return (
    <article className="border border-[var(--border)] bg-[var(--surface)] p-8">
      <div className="mb-3 flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div className="min-w-0">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
            Job Module
          </p>
          <p className="truncate text-sm font-medium text-[var(--foreground)]">
            {filename}
          </p>
        </div>
        <span
          className={`shrink-0 border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] ${
            connected
              ? "border-[var(--accent)] text-[var(--accent)]"
              : "border-[var(--border)] text-[var(--muted-foreground)]"
          }`}
        >
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
            Status
          </p>
          <span
            className={`inline-block border px-2 py-1 font-mono text-xs uppercase tracking-[0.16em] ${
              STATUS_STYLES[status] ?? STATUS_STYLES.queued
            }`}
          >
            {status}
          </span>
        </div>

        <div className="min-w-0 text-right">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
            Job ID
          </p>
          <p className="truncate font-mono text-xs text-[var(--muted-foreground)]">
            {jobId}
          </p>
        </div>
      </div>
    </article>
  );
}
