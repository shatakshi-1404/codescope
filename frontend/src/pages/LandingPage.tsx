import {
  Activity,
  ArrowRight,
  Binary,
  CheckCircle2,
  FileSearch,
  GitBranch,
  LineChart,
  Menu,
  ScanSearch,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { HeroPreview } from "../components/landing/HeroPreview";
import { buttonClasses } from "../components/ui/Button";
import { Wordmark } from "../components/ui/Logo";

// Replace with your repository's URL.
const GITHUB_URL = "https://github.com";

const NAV_LINKS = [
  { href: "#product", label: "Product" },
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#security", label: "Security" },
];

const STRIP = [
  { icon: Binary, label: "AST Analysis" },
  { icon: FileSearch, label: "Static Analysis" },
  { icon: ShieldCheck, label: "Security Checks" },
  { icon: LineChart, label: "Quality Trends" },
  { icon: GitBranch, label: "Repository Insights" },
];

const FEATURES = [
  { icon: GitBranch, title: "Repository Analysis", text: "Paste a public GitHub URL. CodeScope shallow-clones it into a temporary workspace, analyzes it, and deletes the clone." },
  { icon: CheckCircle2, title: "Code Quality", text: "Long functions, long parameter lists, duplicated bodies, unused imports and unclear names, found with deterministic rules." },
  { icon: Activity, title: "Complexity Analysis", text: "Cyclomatic complexity, nesting depth and branch counts per function, rolled up per file and per repository." },
  { icon: ShieldCheck, title: "Security Checks", text: "Static checks for hardcoded secrets, eval/exec, shell injection patterns and SQL built from strings." },
  { icon: LineChart, title: "Historical Trends", text: "Every analysis is kept. Watch quality, complexity and findings change as you ship improvements." },
  { icon: Users, title: "Team Collaboration", text: "Project roles (owner, admin, member, viewer), issue triage, and an audit log of who did what." },
];

const STEPS = [
  ["Connect repository", "Add a public GitHub repository to a project."],
  ["Run analysis", "Choose a branch and start. Progress is shown live."],
  ["Review findings", "Browse issues by severity, file and category."],
  ["Improve code", "Fix what matters and mark issues resolved or ignored."],
  ["Re-analyze", "Run again to measure the effect of your changes."],
  ["Track progress", "Follow your scores over time on the trend charts."],
] as const;

const SECURITY_POINTS = [
  { title: "Your code is not kept", text: "Repositories are cloned to a temporary folder and deleted right after analysis. Only findings and metrics are stored." },
  { title: "No external AI services", text: "Scores, findings and summaries are produced locally. Source code is never sent to a third-party LLM." },
  { title: "Honest about limits", text: "Security results are static checks, not a complete audit. Scores are a transparent heuristic, not a scientific measure." },
];

export default function LandingPage() {
  const { status } = useAuth();
  const authed = status === "authenticated";
  const [open, setOpen] = useState(false);
  const primaryHref = authed ? "/dashboard" : "/register";

  return (
    <div className="min-h-screen bg-ivory-100">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>

      {/* ---------------------------------------------------------- nav */}
      <header className="sticky top-0 z-30 border-b border-line bg-ivory-100/90 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between">
          <Link to="/" aria-label="CodeScope home" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
            <Wordmark />
          </Link>

          <nav aria-label="Primary" className="hidden items-center gap-7 md:flex">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="text-sm text-ink-600 transition-colors hover:text-ink-900">
                {l.label}
              </a>
            ))}
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="text-sm text-ink-600 transition-colors hover:text-ink-900">
              GitHub
            </a>
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            {authed ? (
              <Link to="/dashboard" className={buttonClasses("primary", "sm")}>Open dashboard</Link>
            ) : (
              <>
                <Link to="/login" className={buttonClasses("ghost", "sm")}>Login</Link>
                <Link to="/register" className={buttonClasses("primary", "sm")}>Get Started</Link>
              </>
            )}
          </div>

          <button
            className="grid h-9 w-9 place-items-center rounded-md text-ink-600 hover:bg-sage-100 md:hidden"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {open && (
          <div className="border-t border-line bg-ivory-100 md:hidden">
            <div className="container-page flex flex-col gap-1 py-3">
              {NAV_LINKS.map((l) => (
                <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-md px-2 py-2.5 text-sm text-ink-700 hover:bg-sage-100">
                  {l.label}
                </a>
              ))}
              <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="rounded-md px-2 py-2.5 text-sm text-ink-700 hover:bg-sage-100">
                GitHub
              </a>
              <div className="mt-2 flex gap-2">
                {authed ? (
                  <Link to="/dashboard" className={buttonClasses("primary", "md", "flex-1")}>Open dashboard</Link>
                ) : (
                  <>
                    <Link to="/login" className={buttonClasses("secondary", "md", "flex-1")}>Login</Link>
                    <Link to="/register" className={buttonClasses("primary", "md", "flex-1")}>Get Started</Link>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </header>

      <main id="main">
        {/* --------------------------------------------------------- hero */}
        <section id="product" className="container-page pb-16 pt-16 text-center sm:pt-24">
          <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800">
            <ScanSearch className="h-3.5 w-3.5" /> Developer intelligence for your codebase
          </p>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight text-ink-900 sm:text-5xl lg:text-6xl">
            Know your codebase before your codebase knows your problems.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-ink-500 sm:text-lg">
            Analyze GitHub repositories for code quality, complexity, maintainability, and security issues, all from one
            engineering dashboard.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to={primaryHref} className={buttonClasses("primary", "lg", "w-full sm:w-auto")}>
              Analyze Repository <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#features" className={buttonClasses("secondary", "lg", "w-full sm:w-auto")}>
              View Demo
            </a>
          </div>

          <div className="mt-16">
            <HeroPreview />
          </div>
        </section>

        {/* ----------------------------------------------------- tech strip */}
        <section aria-label="Capabilities" className="border-y border-line bg-white">
          <ul className="container-page flex flex-wrap items-center justify-center gap-x-10 gap-y-4 py-6">
            {STRIP.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-ink-500">
                <Icon className="h-4 w-4 text-brand-600" aria-hidden="true" />
                {label}
              </li>
            ))}
          </ul>
        </section>

        {/* ------------------------------------------------------ features */}
        <section id="features" className="container-page py-20 sm:py-28">
          <div className="max-w-2xl">
            <p className="font-mono text-xs uppercase tracking-widest text-brand-700">Features</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Everything you need to see what your code is really like.
            </h2>
          </div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <article key={title} className="card card-hover p-6">
                <span className="grid h-10 w-10 place-items-center rounded-md bg-brand-50 text-brand-700">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-base font-semibold text-ink-900">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-500">{text}</p>
              </article>
            ))}
          </div>
        </section>

        {/* -------------------------------------------------- how it works */}
        <section id="how-it-works" className="border-y border-line bg-white py-20 sm:py-28">
          <div className="container-page">
            <div className="max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-brand-700">How it works</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                From repository to measurable improvement.
              </h2>
            </div>
            <ol className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
              {STEPS.map(([title, text], i) => (
                <li key={title} className="flex gap-4">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-brand-200 bg-brand-50 font-mono text-sm font-medium text-brand-800">
                    {i + 1}
                  </span>
                  <div>
                    <h3 className="font-semibold text-ink-900">{title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-ink-500">{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ------------------------------------------------------ security */}
        <section id="security" className="container-page py-20 sm:py-28">
          <div className="max-w-2xl">
            <p className="font-mono text-xs uppercase tracking-widest text-brand-700">Security & privacy</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Built to be trusted with your repositories.
            </h2>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {SECURITY_POINTS.map((p) => (
              <article key={p.title} className="card p-6">
                <ShieldCheck className="h-5 w-5 text-brand-600" aria-hidden="true" />
                <h3 className="mt-4 font-semibold text-ink-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-500">{p.text}</p>
              </article>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------------------ CTA */}
        <section className="container-page pb-24">
          <div className="rounded-2xl bg-brand-800 px-6 py-14 text-center sm:px-12">
            <h2 className="mx-auto max-w-xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Analyze your first repository
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-sm text-brand-100 sm:text-base">
              Create a free account, add a public GitHub repository, and get your first report in minutes.
            </p>
            <Link
              to={primaryHref}
              className="mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-md bg-white px-6 text-base font-medium text-brand-900 transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-brand-800"
            >
              {authed ? "Open dashboard" : "Get Started"} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="container-page flex flex-col items-center justify-between gap-3 py-8 text-sm text-ink-500 sm:flex-row">
          <Wordmark />
          <p>Understand your codebase. Improve your engineering.</p>
        </div>
      </footer>
    </div>
  );
}
