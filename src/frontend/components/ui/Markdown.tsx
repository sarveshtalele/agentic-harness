import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// document text is untrusted, and loading an outside image would tell that site who is reading
function SafeImage({ src, alt }: { src?: unknown; alt?: string }) {
  const url = typeof src === "string" ? src : "";
  if (url.startsWith("/api/documents/")) return <img src={url} alt={alt || ""} className="my-2 max-w-full rounded-lg" />; // eslint-disable-line @next/next/no-img-element
  return <span className="text-xs text-slate-500">[Image from another site not loaded: {alt || url}]</span>;
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-atlas">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          img: SafeImage,
          table: ({ children, ...props }) => (
            <div className="my-3 w-full max-w-full overflow-x-auto rounded-lg border border-slate-200 shadow-xs dark:border-slate-800">
              <table className="w-full text-left text-xs border-collapse" {...props}>
                {children}
              </table>
            </div>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
