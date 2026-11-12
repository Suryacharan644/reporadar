"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Report } from "@/lib/types";
import { ErrorState, ReportSkeleton } from "./States";
import { ReportView } from "./ReportView";

type Props =
  | { mode: "live"; owner: string; name: string }
  | { mode: "shared"; id: string };

/** Loads a report (live analysis or a shared snapshot) and handles loading and error states. */
export function ReportLoader(props: Props) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  const key = props.mode === "live" ? `${props.owner}/${props.name}` : props.id;
  const mode = props.mode;
  const owner = props.mode === "live" ? props.owner : "";
  const name = props.mode === "live" ? props.name : "";
  const id = props.mode === "shared" ? props.id : "";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = mode === "live" ? await api.report(owner, name) : await api.sharedReport(id);
      setReport(data);
    } catch (err) {
      setReport(null);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [mode, owner, name, id]);

  useEffect(() => {
    load();
  }, [load, key, attempt]);

  if (loading) return <ReportSkeleton />;
  if (error) return <ErrorState error={error} onRetry={() => setAttempt((n) => n + 1)} title="Could not load this report" />;
  if (report) return <ReportView report={report} />;
  return null;
}
