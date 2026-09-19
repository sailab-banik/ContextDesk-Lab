import type { Metadata } from "next";
import { Atkinson_Hyperlegible_Mono, Atkinson_Hyperlegible_Next } from "next/font/google";

import { AppHeader } from "@/components/app-header";
import { ConsoleProvider } from "@/components/chat/console-provider";

import "./globals.css";

// A face drawn for legibility, for a tool whose whole job is making things
// visible. The mono cut is reserved for literal code: tool names, ids, prompts.
const atkinson = Atkinson_Hyperlegible_Next({
  variable: "--font-atkinson",
  subsets: ["latin"],
});

const atkinsonMono = Atkinson_Hyperlegible_Mono({
  variable: "--font-atkinson-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "ContextDesk Lab", template: "%s – ContextDesk Lab" },
  description:
    "See where each AI response got its context, what was left out, and what every step cost.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${atkinson.variable} ${atkinsonMono.variable} antialiased`}>
      <body className="flex min-h-dvh flex-col">
        <ConsoleProvider>
          <AppHeader />
          {children}
        </ConsoleProvider>
      </body>
    </html>
  );
}
