import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Logo } from "../components/ui/Logo";
import { useAuth } from "./AuthContext";

function FullPageLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-ivory-100" role="status" aria-live="polite">
      <div className="flex animate-pulse items-center gap-3 text-ink-500">
        <Logo size={28} />
        <span className="text-sm">Loading CodeScope…</span>
      </div>
    </div>
  );
}

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageLoader />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}

/** For /login, /register, /forgot-password: signed-in users go straight to the app. */
export function GuestRoute() {
  const { status } = useAuth();
  if (status === "loading") return <FullPageLoader />;
  if (status === "authenticated") return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
