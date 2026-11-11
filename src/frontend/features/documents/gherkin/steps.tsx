export const stepBadgeStyle = (kw: string) => {
  switch (kw) {
    case "GIVEN":
      return "bg-sky-500/15 text-sky-400 border border-sky-500/30";
    case "WHEN":
      return "bg-amber-500/15 text-amber-400 border border-amber-500/30";
    case "THEN":
      return "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
    case "AND":
    case "BUT":
      return "bg-purple-500/15 text-purple-400 border border-purple-500/30";
    default:
      return "bg-slate-700/40 text-slate-300 border border-slate-600";
  }
};

// Highlights quoted strings and variables in step text
export const formatStepText = (text: string) => {
  const parts = text.split(/("[^"]*"|<[^>]*>)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('"') && part.endsWith('"')) {
      return (
        <span key={idx} className="font-mono text-indigo-300 font-semibold bg-indigo-950/40 px-1 py-0.5 rounded border border-indigo-800/40">
          {part}
        </span>
      );
    }
    if (part.startsWith("<") && part.endsWith(">")) {
      return (
        <span key={idx} className="font-mono text-amber-300 font-bold bg-amber-950/40 px-1 py-0.5 rounded border border-amber-800/40">
          {part}
        </span>
      );
    }
    return <span key={idx}>{part}</span>;
  });
};
