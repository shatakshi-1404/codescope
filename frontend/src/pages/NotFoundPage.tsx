import { Link } from "react-router-dom";
import { buttonClasses } from "../components/ui/Button";

export default function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center px-6 text-center">
      <div>
        <p className="font-mono text-sm text-brand-700">404</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Page not found</h1>
        <p className="mt-2 text-sm text-ink-500">That page doesn't exist or was moved.</p>
        <Link to="/" className={buttonClasses("primary", "md", "mt-6")}>
          Back to home
        </Link>
      </div>
    </main>
  );
}
