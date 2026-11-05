import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agentic QE Harness | Microsoft Agent Framework",
  description:
    "Autonomous Quality Engineering Chatbot Harness powered by Microsoft Agent Framework (MAF 2.0)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#09090b] text-zinc-100 antialiased h-screen w-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
