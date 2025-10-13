import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, MapPin, Clock, Users, Heart, Zap, Shield, Brain } from 'lucide-react';

export default function Careers() {
  const openPositions = [
    {
      title: "Senior Full-Stack Developer",
      location: "Remote / San Francisco, CA",
      type: "Full-time",
      department: "Engineering",
      description: "Join our core engineering team to build the next generation of HR technology. You'll work with cutting-edge AI, blockchain, and video processing technologies."
    },
    {
      title: "AI/ML Engineer",
      location: "Remote / New York, NY",
      type: "Full-time",
      department: "AI Research",
      description: "Lead the development of our AI-powered assessment algorithms and behavioral analysis systems. Work with state-of-the-art machine learning models."
    },
    {
      title: "Product Manager",
      location: "Remote / Austin, TX",
      type: "Full-time",
      department: "Product",
      description: "Drive product strategy and roadmap for our HR platform. Work closely with engineering, design, and customer success teams to deliver exceptional user experiences."
    },
    {
      title: "UX/UI Designer",
      location: "Remote / Seattle, WA",
      type: "Full-time",
      department: "Design",
      description: "Create intuitive and beautiful user experiences for our HR platform. Work on everything from user research to high-fidelity prototypes."
    },
    {
      title: "DevOps Engineer",
      location: "Remote / Denver, CO",
      type: "Full-time",
      department: "Infrastructure",
      description: "Build and maintain our cloud infrastructure. Work with Kubernetes, Docker, and modern deployment pipelines to ensure our platform scales globally."
    },
    {
      title: "Customer Success Manager",
      location: "Remote / Chicago, IL",
      type: "Full-time",
      department: "Customer Success",
      description: "Help our clients maximize the value of AskTrabaajo. Work directly with enterprise customers to ensure successful implementations and adoption."
    }
  ];

  const benefits = [
    {
      icon: <Heart className="h-8 w-8 text-[#D4AF37]" />,
      title: "Health & Wellness",
      description: "Comprehensive health, dental, and vision coverage for you and your family"
    },
    {
      icon: <Zap className="h-8 w-8 text-[#D4AF37]" />,
      title: "Flexible Work",
      description: "Remote-first culture with flexible hours and unlimited PTO"
    },
    {
      icon: <Brain className="h-8 w-8 text-[#D4AF37]" />,
      title: "Learning & Growth",
      description: "Annual learning budget, conference attendance, and career development programs"
    },
    {
      icon: <Shield className="h-8 w-8 text-[#D4AF37]" />,
      title: "Equity & Ownership",
      description: "Competitive equity packages so you can share in our success"
    },
    {
      icon: <Users className="h-8 w-8 text-[#D4AF37]" />,
      title: "Amazing Team",
      description: "Work with brilliant, passionate people who are changing the future of work"
    },
    {
      icon: <MapPin className="h-8 w-8 text-[#D4AF37]" />,
      title: "Global Offices",
      description: "Work from any of our offices worldwide or stay fully remote"
    }
  ];

  const cultureValues = [
    "Innovation First",
    "Human-Centered Design",
    "Transparency & Trust",
    "Continuous Learning",
    "Work-Life Balance",
    "Diversity & Inclusion"
  ];

  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white min-h-screen pt-16">
      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
              Join Our <span className="text-[#D4AF37]">Mission</span>
            </h1>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              Help us build the future of HR technology. We&apos;re looking for passionate, innovative people who want to make a real impact on how companies hire and manage talent.
            </p>
          </div>
        </div>
      </section>

      {/* Culture Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                Our <span className="text-[#D4AF37]">Culture</span>
              </h2>
              <p className="text-lg text-gray-600 dark:text-white/70 mb-8">
                At AskTrabaajo, we believe that great products come from great teams. We&apos;re building a culture where everyone can do their best work, learn continuously, and make a meaningful impact.
              </p>
              <div className="grid grid-cols-2 gap-4">
                {cultureValues.map((value, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-[#D4AF37] rounded-full"></div>
                    <span className="text-gray-700 dark:text-white/80">{value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <Image
                src="/team-meeting.jpg"
                alt="Team collaboration"
                width={600}
                height={400}
                className="rounded-lg shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Why Work With <span className="text-[#D4AF37]">Us</span>?
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              We offer competitive benefits and a culture that values your growth and well-being
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {benefits.map((benefit, index) => (
              <div key={index} className="p-6 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300">
                <div className="mb-4">
                  {benefit.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
                  {benefit.title}
                </h3>
                <p className="text-gray-600 dark:text-white/70">
                  {benefit.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Open Positions */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Open <span className="text-[#D4AF37]">Positions</span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              Find your next role and help us build the future of HR
            </p>
          </div>

          <div className="space-y-6">
            {openPositions.map((position, index) => (
              <div
                key={index}
                className="p-6 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                      {position.title}
                    </h3>
                    <div className="flex flex-wrap items-center space-x-4 text-sm text-gray-600 dark:text-white/70 mb-3">
                      <div className="flex items-center">
                        <MapPin className="h-4 w-4 mr-1" />
                        {position.location}
                      </div>
                      <div className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {position.type}
                      </div>
                      <div className="flex items-center">
                        <Users className="h-4 w-4 mr-1" />
                        {position.department}
                      </div>
                    </div>
                    <p className="text-gray-600 dark:text-white/70 mb-4">
                      {position.description}
                    </p>
                  </div>
                  <div className="mt-4 md:mt-0 md:ml-6">
                    <button className="px-6 py-2 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors duration-200 inline-flex items-center">
                      Apply Now
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">
            Don&apos;t See Your <span className="text-[#D4AF37]">Dream Role</span>?
          </h2>
          <p className="text-xl text-gray-600 dark:text-white/70 mb-8">
            We&apos;re always looking for exceptional talent. Send us your resume and let us know how you&apos;d like to contribute to our mission.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/contact"
              className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
            >
              Get in Touch
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link
              href="/about"
              className="px-8 py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-semibold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              Learn About Us
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
