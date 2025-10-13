'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, Zap, Shield } from 'lucide-react';

// Mock data
const heroImages = [
  "https://images.unsplash.com/photo-1522071820081-009f0129c71c",
  "https://images.unsplash.com/photo-1522202176988-66273c2fd55f"
];

const dashboardImages = [
  "/secure-dashboard.png"
];

const stats = [
  { value: "80%", label: "Cost Reduction" },
  { value: "100%", label: "Efficiency Gain" },
  { value: "24/7", label: "AI Availability" },
  { value: "5x", label: "Faster Hiring" }
];

export default function Home() {
  const [animatedStats, setAnimatedStats] = useState(stats.map(() => 0));
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const statsSection = document.getElementById('stats-section');
      if (!statsSection || hasAnimated) return;

      const rect = statsSection.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight && rect.bottom >= 0;

      if (isVisible) {
        setHasAnimated(true);
        stats.forEach((stat, index) => {
          let current = 0;
          const target = parseInt(stat.value);
          const increment = target / 50;
          
          const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
              setAnimatedStats(prev => {
                const newStats = [...prev];
                newStats[index] = target;
                return newStats;
              });
              clearInterval(timer);
            } else {
              setAnimatedStats(prev => {
                const newStats = [...prev];
                newStats[index] = Math.floor(current);
                return newStats;
              });
            }
          }, 30);
        });
      }
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [hasAnimated]);

  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16 sm:pt-20">
        <div className="absolute inset-0 z-0">
          <Image
            src={heroImages[0]}
            alt="Diverse team"
            width={1920}
            height={1080}
            className="w-full h-full object-cover opacity-20 dark:opacity-30"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-white via-white/80 to-white dark:from-black dark:via-black/70 dark:to-black"></div>
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-4 sm:mb-6 leading-tight">
            The HR Department
            <br />
            <span className="text-[#D4AF37]">That Runs Itself</span>
          </h1>
          <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-gray-700 dark:text-white/80 mb-6 sm:mb-8 max-w-3xl mx-auto px-4">
            Ask Trabaajo automates everything — hiring, onboarding, payroll, compliance, engagement — all through voice commands and smart AI.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center px-4">
            <a
              href="#demo"
              className="px-6 sm:px-8 py-3 sm:py-4 bg-[#D4AF37] text-black font-bold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
            >
              <span className="text-sm sm:text-base">Experience the Future</span>
              <ArrowRight className="ml-2" size={18} />
            </a>
            <Link
              href="/features"
              className="px-6 sm:px-8 py-3 sm:py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-bold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              <span className="text-sm sm:text-base">View Features</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Powered By Section */}
      <section className="py-12 sm:py-16 lg:py-20 bg-gradient-to-b from-white to-gray-50 dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-8 lg:gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6">
                Powered by AI.
                <br />
                <span className="text-[#D4AF37]">Secured by Blockchain.</span>
              </h2>
              <p className="text-lg sm:text-xl text-gray-700 dark:text-white/70 mb-6 sm:mb-8">
                We combine automation, compliance, and intelligence into one powerful ecosystem that scales with your company — and cuts operational cost by 80%.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                <div className="flex items-start space-x-3">
                  <Zap className="text-[#D4AF37] mt-1 flex-shrink-0" size={24} />
                  <div>
                    <h3 className="font-semibold mb-1 text-gray-900 dark:text-white">Lightning Fast</h3>
                    <p className="text-sm text-gray-600 dark:text-white/60">Process in seconds, not days</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Shield className="text-[#D4AF37] mt-1 flex-shrink-0" size={24} />
                  <div>
                    <h3 className="font-semibold mb-1 text-gray-900 dark:text-white">Secure & Compliant</h3>
                    <p className="text-sm text-gray-600 dark:text-white/60">Blockchain-backed security</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="relative">
              <Image
                src={dashboardImages[0]}
                alt="AI Dashboard"
                width={600}
                height={400}
                className="rounded-lg shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section id="stats-section" className="py-12 sm:py-16 lg:py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12 sm:mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4">
              <span className="text-[#D4AF37]">80%</span> Lower Cost.
              <br />
              <span className="text-[#D4AF37]">100%</span> Higher Efficiency.
            </h2>
            <p className="text-lg sm:text-xl text-gray-700 dark:text-white/70">
              No more redundant HR layers, endless approvals, or bloated software costs.
            </p>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-8">
            {stats.map((stat, index) => (
              <div
                key={index}
                className="text-center p-4 sm:p-6 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg hover:border-[#D4AF37] transition-all duration-300 hover:scale-105"
              >
                <div className="text-3xl sm:text-4xl md:text-5xl font-bold text-[#D4AF37] mb-2">
                  {stat.value.includes('%') || stat.value.includes('x')
                    ? animatedStats[index] + (stat.value.includes('%') ? '%' : 'x')
                    : stat.value}
                </div>
                <div className="text-sm sm:text-base text-gray-600 dark:text-white/60">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Meet Trabaajo Section */}
      <section id="demo" className="py-12 sm:py-16 lg:py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-8 sm:mb-12">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6">
              Meet <span className="text-[#D4AF37]">Trabaajo</span>
              <br className="hidden sm:block" />
              <span className="block sm:inline"> The Assistant with Attitude</span>
            </h2>
            <p className="text-lg sm:text-xl text-gray-700 dark:text-white/70 max-w-3xl mx-auto">
              She's witty, sharp, and brutally efficient. Try her demo — she'll probably roast you, but she'll also run your HR smoother than anyone you've ever hired.
            </p>
          </div>

          <div className="max-w-2xl mx-auto text-center">
            <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-[#D4AF37]/30 rounded-2xl p-6 sm:p-8">
              <div className="mb-6">
                <div className="w-16 h-16 sm:w-20 sm:h-20 mx-auto bg-gradient-to-br from-[#D4AF37] to-[#C49F2F] rounded-full flex items-center justify-center mb-4 animate-pulse-slow">
                  <span className="text-2xl sm:text-3xl">🎤</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold mb-2 text-gray-900 dark:text-white">Click the Voice Button</h3>
                <p className="text-sm sm:text-base text-gray-600 dark:text-white/60">Try asking Trabaajo questions in the bottom-right corner</p>
              </div>

              <div className="space-y-3 text-left">
                <div className="p-3 sm:p-4 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg">
                  <p className="text-xs sm:text-sm text-gray-700 dark:text-white/80">💬 "Who's our top performer this month?"</p>
                </div>
                <div className="p-3 sm:p-4 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg">
                  <p className="text-xs sm:text-sm text-gray-700 dark:text-white/80">💬 "Hire a new content manager."</p>
                </div>
                <div className="p-3 sm:p-4 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg">
                  <p className="text-xs sm:text-sm text-gray-700 dark:text-white/80">💬 "How efficient am I?"</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Human Behind AI Section */}
      <section className="py-12 sm:py-16 lg:py-20 bg-white dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-8 lg:gap-12 items-center">
            <div className="order-2 md:order-1">
              <Image
                src={heroImages[1]}
                alt="Team collaboration"
                width={600}
                height={400}
                className="rounded-lg shadow-2xl"
              />
            </div>
            <div className="order-1 md:order-2">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6">
                The <span className="text-[#D4AF37]">Human</span>
                <br />
                Behind the AI
              </h2>
              <p className="text-lg sm:text-xl text-gray-700 dark:text-white/70 mb-4 sm:mb-6">
                AskTrabaajo isn't just AI — it's built by people who've been frustrated by HR bloat, endless forms, and poor hiring tools.
              </p>
              <p className="text-base sm:text-lg text-gray-600 dark:text-white/60 mb-6 sm:mb-8">
                We've just automated the parts that waste your time, so you can focus on what truly matters: building great teams and meaningful relationships.
              </p>
              <Link
                href="/about"
                className="inline-flex items-center text-[#D4AF37] hover:text-[#C49F2F] font-semibold transition-colors duration-200"
              >
                Learn Our Story
                <ArrowRight className="ml-2" size={20} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12 sm:py-16 lg:py-20 bg-gradient-to-b from-white to-gray-50 dark:from-black/95 dark:to-black">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6">
            Ready to Transform Your HR?
          </h2>
          <p className="text-lg sm:text-xl text-gray-700 dark:text-white/70 mb-6 sm:mb-8">
            Join forward-thinking companies that are already running HR like Fortune 500 enterprises.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
            <Link
              href="/contact"
              className="px-6 sm:px-8 py-3 sm:py-4 bg-[#D4AF37] text-black font-bold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
            >
              Get Started Today
              <ArrowRight className="ml-2" size={20} />
            </Link>
            <a
              href="#demo"
              className="px-6 sm:px-8 py-3 sm:py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-bold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              Try the Demo
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}