import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Check, Zap, Shield, Users, Brain, Clock, DollarSign, ArrowRight } from 'lucide-react';

export default function Features() {
  const features = [
    {
      icon: <Brain className="h-8 w-8 text-[#D4AF37]" />,
      title: "AI-Powered Assessments",
      description: "Intelligent candidate evaluation with machine learning algorithms that adapt to your hiring needs."
    },
    {
      icon: <Users className="h-8 w-8 text-[#D4AF37]" />,
      title: "Video Interviews",
      description: "Real-time video interviews with facial detection and behavioral analysis for comprehensive candidate insights."
    },
    {
      icon: <Shield className="h-8 w-8 text-[#D4AF37]" />,
      title: "Blockchain Security",
      description: "Immutable candidate records and secure data storage using blockchain technology for maximum data integrity."
    },
    {
      icon: <Zap className="h-8 w-8 text-[#D4AF37]" />,
      title: "Lightning Fast",
      description: "Process candidates in seconds, not days. Automated workflows that scale with your hiring volume."
    },
    {
      icon: <Clock className="h-8 w-8 text-[#D4AF37]" />,
      title: "24/7 Availability",
      description: "Round-the-clock candidate processing and AI assistance that never sleeps or takes breaks."
    },
    {
      icon: <DollarSign className="h-8 w-8 text-[#D4AF37]" />,
      title: "Cost Effective",
      description: "Reduce hiring costs by up to 80% while improving candidate quality and reducing time-to-hire."
    }
  ];

  const comparisonFeatures = [
    { feature: "AI-Powered Screening", asktrabaajo: true, traditional: false },
    { feature: "Video Interview Analysis", asktrabaajo: true, traditional: false },
    { feature: "Blockchain Security", asktrabaajo: true, traditional: false },
    { feature: "Real-time Processing", asktrabaajo: true, traditional: false },
    { feature: "Automated Compliance", asktrabaajo: true, traditional: false },
    { feature: "Multi-language Support", asktrabaajo: true, traditional: false },
    { feature: "Integration APIs", asktrabaajo: true, traditional: true },
    { feature: "Basic Reporting", asktrabaajo: true, traditional: true }
  ];

  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white min-h-screen pt-16">
      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
              Powerful <span className="text-[#D4AF37]">Features</span>
              <br />
              That Scale With You
            </h1>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              Everything you need to revolutionize your hiring process, powered by cutting-edge AI and blockchain technology.
            </p>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="p-8 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300 hover:scale-105"
              >
                <div className="mb-6">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-white/70">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              AskTrabaajo vs <span className="text-[#D4AF37]">Traditional HR</span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              See how we stack up against conventional hiring methods
            </p>
          </div>

          <div className="bg-white dark:bg-white/5 rounded-xl shadow-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-white/10">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Feature
                    </th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-[#D4AF37]">
                      AskTrabaajo
                    </th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-500">
                      Traditional HR
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-white/10">
                  {comparisonFeatures.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50 dark:hover:bg-white/5">
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {item.feature}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {item.asktrabaajo ? (
                          <Check className="h-5 w-5 text-[#D4AF37] mx-auto" />
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {item.traditional ? (
                          <Check className="h-5 w-5 text-gray-400 mx-auto" />
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">
            Ready to Experience the <span className="text-[#D4AF37]">Future</span>?
          </h2>
          <p className="text-xl text-gray-600 dark:text-white/70 mb-8">
            Join thousands of companies already using AskTrabaajo to revolutionize their hiring process.
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
              href="/about"
              className="px-8 py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-semibold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
