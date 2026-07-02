"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";

interface JobDataStatus { latest_date?: string; stocks?: number; count?: number }
interface JobScheduleRow { id: string; description: string; schedule: string }
interface JobStatus { data_status?: Record<string, JobDataStatus | null>; jobs?: JobScheduleRow[] }

export function AdminControlPanel() {
  const t = useTranslations("settings");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const res = await apiFetch<JobStatus>("/admin/jobs/status");
      setJobStatus(res);
    } catch {}
  }, []);

  // Mount fetch of job/data status.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { loadStatus(); }, [loadStatus]);

  const triggerJob = async (jobId: string) => {
    setRunning(jobId);
    try {
      await apiFetch(`/admin/jobs/${jobId}`, { method: "POST" });
      // Poll status multiple times to catch completion
      setTimeout(loadStatus, 5000);
      setTimeout(loadStatus, 15000);
      setTimeout(loadStatus, 30000);
    } catch {}
    finally { setTimeout(() => setRunning(null), 3000); }
  };

  const JOBS = [
    { id: "daily-ingest", label: t("admin_job_ingest"), desc: t("admin_job_ingest_desc") },
    { id: "daily-scoring", label: t("admin_job_scoring"), desc: t("admin_job_scoring_desc") },
    { id: "alert-check", label: t("admin_job_alerts"), desc: t("admin_job_alerts_desc") },
    { id: "weekly-themes", label: t("admin_job_themes"), desc: t("admin_job_themes_desc") },
    { id: "weekly-summaries", label: t("admin_job_summaries"), desc: t("admin_job_summaries_desc") },
    { id: "extract-supply-chain", label: t("admin_job_supply_chain"), desc: t("admin_job_supply_chain_desc") },
    { id: "scrape-profiles", label: t("admin_job_profiles"), desc: t("admin_job_profiles_desc") },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-2">{t("admin_title")}</h2>
      <p className="text-xs text-muted mb-6">{t("admin_subtitle")}</p>

      {/* Data Status */}
      {jobStatus?.data_status && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold mb-3">{t("admin_data_status")}</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(jobStatus.data_status).map(([key, val]) => (
              <div key={key} className="card-atmospheric p-3">
                <div className="text-[10px] text-muted uppercase">{key.replace(/_/g, " ")}</div>
                {val && val.latest_date ? (
                  <>
                    <div className="text-xs font-mono mt-1 text-up">{val.latest_date}</div>
                    {val.stocks && <div className="text-[10px] text-muted">{val.stocks} stocks</div>}
                    {val.count !== undefined && <div className="text-[10px] text-muted">{val.count} records</div>}
                  </>
                ) : (
                  <div className="mt-1 space-y-1">
                    <div className="h-3 w-20 bg-raised rounded animate-pulse" />
                    <div className="h-2 w-14 bg-raised/50 rounded animate-pulse" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Job Triggers */}
      <h3 className="text-sm font-semibold mb-3">{t("admin_manual_triggers")}</h3>
      <div className="space-y-2">
        {JOBS.map((job) => (
          <div key={job.id} className="flex items-center justify-between card-atmospheric p-3">
            <div>
              <div className="text-xs font-medium">{job.label}</div>
              <div className="text-[10px] text-muted">{job.desc}</div>
            </div>
            <button
              onClick={() => triggerJob(job.id)}
              disabled={running === job.id}
              className="px-3 py-1.5 text-[10px] font-medium bg-signal/15 text-signal border border-signal/30 rounded-lg hover:bg-signal/25 transition-colors disabled:opacity-50"
            >
              {running === job.id ? "⏳" : "▶"} {t("admin_run")}
            </button>
          </div>
        ))}
      </div>

      {/* Schedule Info */}
      {jobStatus?.jobs && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold mb-3">{t("admin_schedule")}</h3>
          <div className="space-y-1">
            {jobStatus.jobs.map((j) => (
              <div key={j.id} className="flex items-center justify-between text-xs py-1.5 border-b border-border/20">
                <span className="text-muted">{j.description}</span>
                <span className="font-mono text-[10px]">{j.schedule}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
