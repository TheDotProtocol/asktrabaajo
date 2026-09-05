"use client";

export const PublicPage = ({ children, testId }) => (
  <main id="main-content" data-testid={testId} className="relative">
    {children}
  </main>
);

export const PageHero = ({ eyebrow, title, copy, children }) => (
  <section className="relative pt-40 pb-16 sm:pb-24 overflow-hidden">
    <div className="absolute inset-0 grid-bg mask-fade-y" aria-hidden="true" />
    <div
      className="absolute inset-0"
      aria-hidden="true"
      style={{ background: "radial-gradient(ellipse 60% 50% at 70% 20%, rgba(212,175,55,0.08), transparent 65%)" }}
    />
    <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 className="mt-7 font-display font-bold tracking-tight leading-[1.06] text-4xl sm:text-6xl lg:text-7xl max-w-4xl">
        {title.split("\n").map((line, i) => (
          <span key={line} className={`block ${i === 1 ? "text-gold-grad" : "text-silver-grad"}`}>
            {line}
          </span>
        ))}
      </h1>
      {copy && (
        <p className="mt-7 max-w-2xl text-base sm:text-lg text-mist leading-relaxed">{copy}</p>
      )}
      {children}
    </div>
  </section>
);

export default PublicPage;
