import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "RepoRadar: repository health for open source",
    template: "%s · RepoRadar",
  },
  description: "Find out why developers leave your GitHub repository without contributing. Transparent health scores, actionable fixes and shareable reports.",
  icons: { icon: "/icon.svg" },
  openGraph: {
    title: "RepoRadar",
    description: "Find out why developers leave your GitHub repository without contributing.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#07080c",
  width: "device-width",
  initialScale: 1,
};

function Logo() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight text-zinc-100">
      <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden>
        <circle cx="12" cy="12" r="9" fill="none" stroke="#22d3ee" strokeOpacity="0.5" strokeWidth="1.5" />
        <circle cx="12" cy="12" r="5" fill="none" stroke="#22d3ee" strokeOpacity="0.8" strokeWidth="1.5" />
        <path d="M12 12 L19 7" stroke="#34d399" strokeWidth="2" strokeLinecap="round" />
        <circle cx="12" cy="12" r="1.8" fill="#34d399" />
      </svg>
      RepoRadar
    </span>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-zinc-100 focus:px-3 focus:py-2 focus:text-zinc-900"
        >
          Skip to content
        </a>
        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-zinc-950/60 backdrop-blur-md">
          <nav aria-label="Main" className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 md:px-6">
            <Link href="/" aria-label="RepoRadar home">
              <Logo />
            </Link>
            <div className="flex items-center gap-1 text-sm text-zinc-400 md:gap-4">
              <Link href="/contribute" className="rounded-lg px-3 py-1.5 transition hover:bg-white/5 hover:text-zinc-100">
                Contribute
              </Link>
              <Link href="/methodology" className="rounded-lg px-3 py-1.5 transition hover:bg-white/5 hover:text-zinc-100">
                Methodology
              </Link>
              <a
                href="https://github.com/Suryacharan644/reporadar"
                target="_blank"
                rel="noreferrer"
                className="hidden rounded-lg px-3 py-1.5 transition hover:bg-white/5 hover:text-zinc-100 sm:block"
              >
                GitHub
              </a>
            </div>
          </nav>
        </header>
        <main id="main" className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-14">
          {children}
        </main>
        <footer className="mx-auto mt-10 max-w-6xl px-4 pb-10 text-xs text-zinc-600 md:px-6">
          RepoRadar is open source under the MIT licence. Analyses use public GitHub data only.
        </footer>
      </body>
    </html>
  );
}
