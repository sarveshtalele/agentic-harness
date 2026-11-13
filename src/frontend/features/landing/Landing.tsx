"use client";

import { ArrowRight, Bot, ClipboardCheck, FileText, LogIn, ShieldCheck, Wand2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ThemeToggle } from "../../components/ui";
import { api } from "../../lib/api";

const FEATURES = [
  { icon: Bot, title: "Project harness", text: "An agent on Microsoft Agent Framework that plans, reads your repository, runs approved commands in a sandbox and uses skills, plugins and MCP tools." },
  { icon: FileText, title: "Requirements", text: "BRDs, user stories and Gherkin, checked by the official parser. Every save is an immutable version with its SHA-256." },
  { icon: ClipboardCheck, title: "Governed QE", text: "Test plans, cases, code and runs through gates G0 to G5. A named person signs each gate; agents never approve." },
  { icon: Wand2, title: "Skill Creator Studio", text: "Plan, generate, test and evaluate new agent skills on the real model before anyone can publish them." },
];

const button = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold";

/** Public home page: what the platform does, the desktop downloads and the way in. It reads no project data. */
export function Landing() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  useEffect(() => {
    api("/auth/me").then(() => setSignedIn(true)).catch(() => setSignedIn(false));
  }, []);
  const enter = signedIn ? (
    <Link href="/home" data-testid="landing-open" className={`${button} bg-indigo-600 text-white hover:bg-indigo-500`}>Open workspace <ArrowRight className="h-4 w-4" /></Link>
  ) : (
    <Link href="/login" data-testid="landing-sign-in" className={`${button} bg-indigo-600 text-white hover:bg-indigo-500`}><LogIn className="h-4 w-4" /> Sign in</Link>
  );
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <span className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white"><ShieldCheck className="h-5 w-5" /></span>
          <span className="text-base font-bold">Agentic QE Platform</span>
        </span>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {signedIn !== null && enter}
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-12 px-4 pb-16 pt-10">
        <section className="max-w-3xl space-y-4">
          <h1 className="text-3xl font-bold leading-tight sm:text-4xl">Requirements, code and governed testing, with agents you can audit</h1>
          <p className="text-base text-slate-600 dark:text-slate-400">
            A workspace for business analysts, developers and QE leads. Agents do the work on your real repositories. Every claim is checked against the code, every decision is signed by a person, and every change goes to a hash-chained ledger.
          </p>
          <div className="flex flex-wrap gap-3">
            {signedIn !== null && enter}
          </div>
        </section>

        <section aria-label="What it does" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <article key={title} className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#0b1329]">
              <Icon className="h-5 w-5 text-indigo-500" />
              <h2 className="font-semibold">{title}</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">{text}</p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
