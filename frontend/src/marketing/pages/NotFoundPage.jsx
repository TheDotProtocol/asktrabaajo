"use client";

import { Link } from "@/marketing/compat/router";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import { SITE } from "@/marketing/config/site";

export const NotFoundPage = () => {
  usePageMeta({
    title: "Page not found",
    description: "This page is not part of the public AskTrabaajo website.",
  });

  return (
    <main id="main-content" data-testid="not-found-page" className="min-h-[70vh] flex flex-col items-center justify-center text-center px-6 pt-24">
      <p className="eyebrow">404</p>
      <h1 className="mt-6 font-display text-3xl sm:text-5xl font-semibold text-silver-grad tracking-tight">
        This page is not on the public site.
      </h1>
      <p className="mt-6 max-w-md text-mist leading-relaxed">
        Login, register and the AskTrabaajo application live on the canonical
        platform — not as pages of this website.
      </p>
      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <Link
          to="/"
          data-testid="not-found-home"
          className="inline-flex items-center gap-2 border border-gold/40 text-gold-soft font-mono text-[11px] uppercase tracking-[0.18em] px-6 py-3 rounded-sm hover:bg-gold hover:text-ink transition-colors duration-300"
        >
          Back to the public website
        </Link>
        <a
          href={SITE.urls.login}
          data-testid="not-found-login"
          className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-mist hover:text-gold-soft"
        >
          Login
        </a>
      </div>
    </main>
  );
};

export default NotFoundPage;
