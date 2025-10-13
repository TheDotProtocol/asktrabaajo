import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, Users, Target, Heart, Award } from 'lucide-react';

export default function Leadership() {
  const leadershipTeam = [
    {
      name: "Arun Kumar",
      title: "Founder & CEO",
      image: "/arun.jpeg",
      description: "Visionary leader with 15+ years in HR technology and blockchain innovation. Passionate about transforming how companies hire and manage talent."
    },
    {
      name: "Kelsey Morgan",
      title: "Chief Executive Officer",
      initials: "KM",
      description: "Brings operational expertise and strategic insight to AR Holdings. With extensive experience leading complex technology and corporate initiatives, she ensures seamless execution across verticals."
    },
    {
      name: "Timothy Burton",
      title: "Veteran Advisor & Chairman",
      initials: "TB",
      description: "Seasoned leader with decades of experience in technology, blockchain, and logistics. His expertise strengthens AR Holdings' long-term direction and market leadership."
    },
    {
      name: "Saleena Thamani",
      title: "Founder, Dot Protocol Company Limited",
      initials: "ST",
      description: "Pioneering blockchain developer and architect of the DPC-20 token standard. She merges technical excellence with creativity, innovating at the intersection of fintech and blockchain. Also an accomplished fashion designer."
    },
    {
      name: "Rudra Narayanan",
      title: "Head of Business & Strategy",
      initials: "RN",
      description: "Leads business development, strategic partnerships, and go-to-market execution. With a background in cross-border ventures, he focuses on driving sustainable growth and expanding global footprint."
    }
  ];

  const values = [
    {
      icon: <Users className="h-8 w-8 text-[#D4AF37]" />,
      title: "Human-Centered",
      description: "Every decision we make puts people first, whether they're our team members, clients, or the candidates we help place."
    },
    {
      icon: <Target className="h-8 w-8 text-[#D4AF37]" />,
      title: "Results-Driven",
      description: "We measure success by the impact we create, not just the features we build or the revenue we generate."
    },
    {
      icon: <Heart className="h-8 w-8 text-[#D4AF37]" />,
      title: "Passion-Fueled",
      description: "We're not just building software—we're building the future of work, and that passion drives everything we do."
    },
    {
      icon: <Award className="h-8 w-8 text-[#D4AF37]" />,
      title: "Excellence-Oriented",
      description: "We strive for excellence in everything we do, from the code we write to the relationships we build."
    }
  ];

  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white min-h-screen pt-16">
      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
              Meet Our <span className="text-[#D4AF37]">Leadership</span>
            </h1>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              The visionaries behind AskTrabaajo, building the future of HR technology with passion, innovation, and human-centered design.
            </p>
          </div>
        </div>
      </section>

      {/* Leadership Team */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {leadershipTeam.map((leader, index) => (
              <div
                key={index}
                className="p-8 bg-white/5 border border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 transition-all duration-300"
              >
                <div className="text-center mb-6">
                  {leader.image ? (
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full overflow-hidden">
                      <Image
                        src={leader.image}
                        alt={leader.name}
                        width={80}
                        height={80}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-20 h-20 bg-[#D4AF37]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold text-[#D4AF37]">{leader.initials}</span>
                    </div>
                  )}
                  <h3 className="text-2xl font-bold mb-2">{leader.name}</h3>
                  <p className="text-[#D4AF37] font-semibold">{leader.title}</p>
                </div>
                <p className="text-white/70 text-sm leading-relaxed">
                  {leader.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Company Values */}
      <section className="py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Our <span className="text-[#D4AF37]">Values</span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              The principles that guide everything we do
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {values.map((value, index) => (
              <div key={index} className="text-center p-6">
                <div className="w-16 h-16 bg-[#D4AF37]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  {value.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
                  {value.title}
                </h3>
                <p className="text-gray-600 dark:text-white/70">
                  {value.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Philosophy Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                Our <span className="text-[#D4AF37]">Philosophy</span>
              </h2>
              <p className="text-lg text-gray-600 dark:text-white/70 mb-6">
                We believe that technology should serve people, not the other way around. Every feature we build, every algorithm we train, and every decision we make is guided by one simple question: &quot;How does this help people do their best work?&quot;
              </p>
              <p className="text-base text-gray-600 dark:text-white/60 mb-8">
                This human-centered approach is what sets AskTrabaajo apart. We&apos;re not just building software—we&apos;re building the future of work, one relationship at a time.
              </p>
              <Link
                href="/about"
                className="inline-flex items-center text-[#D4AF37] hover:text-[#C49F2F] font-semibold transition-colors duration-200"
              >
                Learn More About Us
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
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

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">
            Ready to Work With <span className="text-[#D4AF37]">Us</span>?
          </h2>
          <p className="text-xl text-gray-600 dark:text-white/70 mb-8">
            Join the companies that are already transforming their hiring process with AskTrabaajo.
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
              href="/careers"
              className="px-8 py-4 bg-gray-100 dark:bg-white/10 border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white font-semibold rounded-lg hover:bg-gray-200 dark:hover:bg-white/20 transition-all duration-200 inline-flex items-center justify-center"
            >
              Join Our Team
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
