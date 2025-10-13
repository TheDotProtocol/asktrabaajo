import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, Users, Target, Heart } from 'lucide-react';

export default function About() {
  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white min-h-screen pt-16">
      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
              The <span className="text-[#D4AF37]">Human</span> Story
              <br />
              Behind the AI
            </h1>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              We&apos;re not just building software — we&apos;re solving problems that have frustrated HR professionals for decades.
            </p>
          </div>
        </div>
      </section>

      {/* Our Story Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                Born from <span className="text-[#D4AF37]">Frustration</span>
              </h2>
              <p className="text-lg text-gray-600 dark:text-white/70 mb-6">
                AskTrabaajo was born from the collective frustration of HR professionals who were tired of:
              </p>
              <ul className="space-y-3 text-gray-600 dark:text-white/70">
                <li className="flex items-start">
                  <span className="text-[#D4AF37] mr-2">•</span>
                  Endless paperwork and redundant processes
                </li>
                <li className="flex items-start">
                  <span className="text-[#D4AF37] mr-2">•</span>
                  Bloated software that promised everything but delivered nothing
                </li>
                <li className="flex items-start">
                  <span className="text-[#D4AF37] mr-2">•</span>
                  Hiring processes that took weeks instead of days
                </li>
                <li className="flex items-start">
                  <span className="text-[#D4AF37] mr-2">•</span>
                  Compliance nightmares that kept everyone up at night
                </li>
              </ul>
            </div>
            <div className="relative">
              <Image
                src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f"
                alt="Team collaboration"
                width={600}
                height={400}
                className="rounded-lg shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Vision Section */}
      <section className="py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Our <span className="text-[#D4AF37]">Vision</span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              To create an HR ecosystem that actually works — where technology serves people, not the other way around.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#D4AF37]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="h-8 w-8 text-[#D4AF37]" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Human-Centered</h3>
              <p className="text-gray-600 dark:text-white/70">
                Every feature is designed with real people in mind, not just impressive technology.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#D4AF37]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Target className="h-8 w-8 text-[#D4AF37]" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Results-Driven</h3>
              <p className="text-gray-600 dark:text-white/70">
                We measure success by the impact on your team, not by the number of features we ship.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#D4AF37]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Heart className="h-8 w-8 text-[#D4AF37]" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Passion-Fueled</h3>
              <p className="text-gray-600 dark:text-white/70">
                We&apos;re not just building software — we&apos;re building the future of work.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">
            Ready to Join the <span className="text-[#D4AF37]">Revolution</span>?
          </h2>
            <p className="text-xl text-gray-600 dark:text-white/70 mb-8">
              Be part of the movement that&apos;s transforming HR from a cost center into a strategic advantage.
            </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/contact"
              className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
            >
              Get Started Today
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link
              href="/leadership"
              className="px-8 py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-semibold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              Meet Our Team
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
