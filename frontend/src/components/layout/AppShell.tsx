import {
  Activity,
  Bell,
  CircleAlert,
  FolderKanban,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Menu,
  ScanSearch,
  Search,
  Settings,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import { Wordmark } from "../ui/Logo";
import { useToast } from "../ui/Toast";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/repositories", label: "Repositories", icon: GitBranch },
  { to: "/analyses", label: "Analyses", icon: ScanSearch },
  { to: "/issues", label: "Issues", icon: CircleAlert },
  { to: "/team", label: "Team", icon: Users },
  { to: "/activity", label: "Activity", icon: Activity },
  { to: "/settings", label: "Settings", icon: Settings },
];

function useDismiss(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  return ref;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex h-full flex-col">
      <div className="flex h-16 items-center px-5">
        <Wordmark />
      </div>
      <ul className="flex-1 space-y-0.5 px-3 py-2">
        {NAV.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors " +
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 " +
                (isActive
                  ? "bg-brand-50 text-brand-800"
                  : "text-ink-600 hover:bg-sage-100 hover:text-ink-900")
              }
            >
              <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const ref = useDismiss(open, close);
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        aria-expanded={open}
        className="grid h-9 w-9 place-items-center rounded-md text-ink-500 hover:bg-sage-100 hover:text-ink-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <Bell className="h-[18px] w-[18px]" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-72 rounded-lg border border-line bg-white p-5 text-center shadow-pop">
          <p className="text-sm font-medium text-ink-900">No notifications yet</p>
          <p className="mt-1 text-xs text-ink-500">Analysis results and team changes will show up here.</p>
        </div>
      )}
    </div>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const ref = useDismiss(open, close);

  async function onLogout() {
    setOpen(false);
    await logout();
    toast.info("You've been signed out.");
    navigate("/login", { replace: true });
  }

  if (!user) return null;
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Account menu"
        aria-expanded={open}
        className="grid h-9 w-9 place-items-center rounded-full bg-brand-700 text-xs font-semibold text-white hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
      >
        {initials(user.name)}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-64 rounded-lg border border-line bg-white py-1 shadow-pop">
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-medium text-ink-900">{user.name}</p>
            <p className="truncate text-xs text-ink-500">{user.email}</p>
          </div>
          <button
            onClick={onLogout}
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-ink-700 hover:bg-sage-100 focus-visible:outline-none focus-visible:bg-sage-100"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function AppShell() {
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setNavOpen(false), [location.pathname]);
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNavOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [navOpen]);

  return (
    <div className="min-h-screen bg-ivory-100">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 border-r border-line bg-white lg:block">
        <Sidebar />
      </aside>

      {/* mobile drawer */}
      {navOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            className="absolute inset-0 bg-ink-900/30"
            aria-label="Close menu"
            onClick={() => setNavOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-64 bg-white shadow-pop">
            <button
              onClick={() => setNavOpen(false)}
              aria-label="Close menu"
              className="absolute right-3 top-4 grid h-8 w-8 place-items-center rounded-md text-ink-500 hover:bg-sage-100"
            >
              <X className="h-4 w-4" />
            </button>
            <Sidebar onNavigate={() => setNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-line bg-ivory-100/90 px-4 backdrop-blur sm:px-6">
          <button
            onClick={() => setNavOpen(true)}
            aria-label="Open menu"
            className="grid h-9 w-9 place-items-center rounded-md text-ink-600 hover:bg-sage-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" aria-hidden="true" />
            <input
              type="search"
              aria-label="Search"
              placeholder="Search projects, repositories, issues…"
              className="h-9 w-full rounded-md border border-line bg-white pl-9 pr-3 text-sm placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <NotificationsMenu />
            <UserMenu />
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
