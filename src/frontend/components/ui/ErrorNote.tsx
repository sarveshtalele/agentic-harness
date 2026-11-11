import Link from "next/link";

export function ErrorNote({ message }: { message?: string | null }) {
  if (!message) return null;
  // a run page named in the message (for example the run that is already active) becomes a link
  const parts = message.split(/(\/projects\/[\w-]+\/runs\/[\w-]+)/);
  return <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">{parts.map((part, i) => (i % 2 ? <Link key={i} href={part} className="mono underline">{part}</Link> : part))}</p>;
}
