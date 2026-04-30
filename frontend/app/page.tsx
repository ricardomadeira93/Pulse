"use client";

import { useState } from "react";

import { JobCard } from "./components/JobCard";

interface Job {
  id: string;
  filename: string;
  status: string;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filename, setFilename] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitJob() {
    if (!filename.trim()) {
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
      });

      if (!res.ok) {
        throw new Error(`Job submission failed with status ${res.status}`);
      }

      const job = (await res.json()) as Job;
      setJobs((prev) => [job, ...prev]);
      setFilename("");
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--background)] px-5 py-8 text-[var(--foreground)] sm:px-8 sm:py-10">
      <div className="mx-auto max-w-5xl">
        <section className="border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4 sm:px-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
              Pulse / Job Interface
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl">
                <h1 className="text-2xl font-medium tracking-[-0.03em] sm:text-4xl">
                  Structured job intake with live processing state.
                </h1>
              </div>
              <div className="shrink-0 border border-[var(--border)] px-4 py-4">
                <p className="font-mono uppercase tracking-[0.2em] text-[var(--muted-foreground)]">
                  Session State
                </p>
                <p className="mt-1 font-mono text-xs uppercase tracking-[0.16em] text-[var(--foreground)]">
                  {loading ? "Submitting" : "Idle"}
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-0 lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
            <div className="border-b border-[var(--border)] p-5 lg:border-b-0 lg:border-r lg:p-6">
              <p className="mb-3 font-mono uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                Submit Job
              </p>
              <p className="mb-5 max-w-xl text-sm leading-6 text-[var(--muted-foreground)]">
                Create a processing job by submitting a filename. Each accepted
                request is persisted by the backend and exposed as a live status
                module below.
              </p>

              <div className="flex flex-col gap-3 sm:flex-row">
                <label className="min-w-0 flex-1">
                  <span className="mb-2 block font-mono uppercase tracking-[0.2em] text-[var(--muted-foreground)]">
                    Filename
                  </span>
                  <input
                    className="w-full border border-[var(--border)] bg-[var(--background)] px-3 py-3 text-sm text-[var(--foreground)] outline-none transition-colors placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)]"
                    placeholder="filename.pdf"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        submitJob();
                      }
                    }}
                  />
                </label>

                <div className="sm:self-end">
                  <button
                    onClick={submitJob}
                    className="w-full border border-[var(--accent)] bg-[var(--accent)] px-3 py-3 font-mono text-xs uppercase tracking-[0.18em] text-black hover:scale-105  hover:transition hover:duration-300 transition-opacity disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                    disabled={loading}
                  >
                    {loading ? "Submitting..." : "Submit"}
                  </button>
                </div>
              </div>
            </div>

            <aside className="p-5 lg:p-6">
              <p className="mb-3 font-mono uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                System Notes
              </p>
              <div className="space-y-3 text-sm leading-6 text-[var(--muted-foreground)]">
                <p>
                  Requests are sent to the backend API, stored as job records,
                  and updated asynchronously through WebSocket-connected job
                  modules.
                </p>
                <p className="border border-[var(--border)] px-3 py-3 font-mono text-xs leading-5">
                  Queue states: queued / processing / completed / failed
                </p>
              </div>
            </aside>
          </div>
        </section>

        <section className="mt-6 border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4 sm:px-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="mb-2 font-mono uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                  Active Jobs
                </p>
                <h2 className="text-lg font-medium tracking-[-0.02em]">
                  Live processing modules
                </h2>
              </div>
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
                {jobs.length} total
              </p>
            </div>
          </div>

          <div className="p-5 sm:p-6">
            {jobs.length === 0 ? (
              <div className="border border-dashed border-[var(--border)] px-4 py-8 text-center">
                <p className="font-mono uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
                  No active jobs
                </p>
                <p className="mt-3 text-sm text-[var(--muted-foreground)]">
                  Submit a filename to create the first tracked job.
                </p>
              </div>
            ) : (
              <div className="grid gap-3">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    jobId={job.id}
                    filename={job.filename}
                    initialStatus={job.status}
                  />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
