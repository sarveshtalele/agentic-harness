"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

/** Loads a run, streams its events, and follows it again after a retry or decision. */
export function useRunStream(runId: string, onFinished?: () => void) {
  const [run, setRun] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const lastSeq = useRef(0);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(async () => {
    const data = await api(`/runs/${runId}`);
    setRun(data);
    return data;
  }, [runId]);

  useEffect(() => {
    lastSeq.current = 0;
    setEvents([]);
    let source: EventSource | null = null;
    let cancelled = false;
    const connect = () => {
      source = new EventSource(`/api/runs/${runId}/events?after=${lastSeq.current}`);
      source.addEventListener("run", (e) => {
        const item = JSON.parse((e as MessageEvent).data);
        lastSeq.current = item.seq;
        setEvents((prior) => [...prior, item]);
      });
      source.addEventListener("end", async () => {
        source?.close();
        if (cancelled) return;
        const data = await load();
        if (data.status === "running") setTimeout(connect, 1000);
        else onFinished?.();
      });
      source.onerror = () => {
        source?.close();
        if (!cancelled) setTimeout(connect, 2000);
      };
    };
    load();
    connect();
    return () => {
      cancelled = true;
      source?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // live numbers while the run works: elapsed time every second, tokens every few seconds
  useEffect(() => {
    if (run?.status !== "running") return;
    const clock = setInterval(() => setNow(Date.now()), 1000);
    const poll = setInterval(load, 3000);
    return () => {
      clearInterval(clock);
      clearInterval(poll);
    };
  }, [run?.status, load]);

  const follow = async () => {
    await load();
    const source = new EventSource(`/api/runs/${runId}/events?after=${lastSeq.current}`);
    source.addEventListener("run", (e) => {
      const item = JSON.parse((e as MessageEvent).data);
      lastSeq.current = item.seq;
      setEvents((prior) => [...prior, item]);
    });
    source.addEventListener("end", async () => {
      source.close();
      const data = await load();
      if (data.status !== "running") onFinished?.();
    });
    source.onerror = () => source.close();
  };

  return { run, events, now, load, follow };
}
