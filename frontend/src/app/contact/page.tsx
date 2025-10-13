import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, Mail, Phone, MapPin, Clock, Send } from 'lucide-react';

export default function Contact() {
  const globalOffices = [
    {
      city: "Mountain View",
      country: "United States (HQ)",
      address: "1075 Terra Bella Ave, Mountain View, CA, 94043",
      phone: "+1 (555) 123-4567",
      email: "hq@asktrabaajo.com"
    },
    {
      city: "Dubai",
      country: "UAE",
      address: "Level 29, Marina Plaza, Dubai Marina",
      phone: "+971 4 123 4567",
      email: "dubai@asktrabaajo.com"
    },
    {
      city: "Belize",
      country: "Belize",
      address: "Suite 305, Matalon Building, Coney Drive, Belize City",
      phone: "+501 123-4567",
      email: "belize@asktrabaajo.com"
    },
    {
      city: "Istanbul",
      country: "Turkey",
      address: "Maslak Mah., Büyükdere Cad., Istanbul 34398",
      phone: "+90 212 123 4567",
      email: "turkey@asktrabaajo.com"
    },
    {
      city: "Bengaluru",
      country: "India",
      address: "91 Springboard, MG Road, Bengaluru, 560001",
      phone: "+91 80 1234 5678",
      email: "india@asktrabaajo.com"
    },
    {
      city: "Bangkok",
      country: "Thailand (Asia HQ)",
      address: "23 Sukhumvit Soi 13, Khlong Toei Nuea, Bangkok 10110",
      phone: "+66 2 123 4567",
      email: "thailand@asktrabaajo.com"
    },
    {
      city: "Singapore",
      country: "Singapore",
      address: "20 Collyer Quay, #23-01, Raffles Place, 049319",
      phone: "+65 6123 4567",
      email: "singapore@asktrabaajo.com"
    },
    {
      city: "Kuala Lumpur",
      country: "Malaysia",
      address: "Level 36, Menara Citibank, Jalan Ampang, Kuala Lumpur 50450",
      phone: "+60 3 1234 5678",
      email: "malaysia@asktrabaajo.com"
    },
    {
      city: "Jakarta",
      country: "Indonesia",
      address: "World Trade Center 3, Jalan Jenderal Sudirman, Jakarta 12930",
      phone: "+62 21 1234 5678",
      email: "indonesia@asktrabaajo.com"
    },
    {
      city: "Ho Chi Minh City",
      country: "Vietnam",
      address: "Saigon Trade Center, 37 Ton Duc Thang, District 1, Ho Chi Minh City",
      phone: "+84 28 1234 5678",
      email: "vietnam@asktrabaajo.com"
    },
    {
      city: "Seoul",
      country: "South Korea",
      address: "23F, Seoul Finance Center, 136 Sejong-daero, Jung-gu, Seoul",
      phone: "+82 2 1234 5678",
      email: "korea@asktrabaajo.com"
    }
  ];

  const contactMethods = [
    {
      icon: <Mail className="h-8 w-8 text-[#D4AF37]" />,
      title: "Email Us",
      description: "Get in touch via email",
      contact: "hello@asktrabaajo.com",
      action: "mailto:hello@asktrabaajo.com"
    },
    {
      icon: <Phone className="h-8 w-8 text-[#D4AF37]" />,
      title: "Call Us",
      description: "Speak with our team",
      contact: "+1 (555) 123-4567",
      action: "tel:+15551234567"
    },
    {
      icon: <Clock className="h-8 w-8 text-[#D4AF37]" />,
      title: "Business Hours",
      description: "We're here to help",
      contact: "Mon-Fri, 9AM-6PM PST",
      action: "#"
    }
  ];

  return (
    <div className="bg-white dark:bg-black text-gray-900 dark:text-white min-h-screen pt-16">
      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white dark:from-black dark:to-black/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
              Get In <span className="text-[#D4AF37]">Touch</span>
            </h1>
            <p className="text-xl text-gray-600 dark:text-white/70 max-w-3xl mx-auto">
              Ready to transform your hiring process? We&apos;d love to hear from you. Reach out to our team and let&apos;s discuss how AskTrabaajo can revolutionize your HR operations.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Methods */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            {contactMethods.map((method, index) => (
              <div
                key={index}
                className="p-8 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300 text-center"
              >
                <div className="mb-6">
                  {method.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
                  {method.title}
                </h3>
                <p className="text-gray-600 dark:text-white/70 mb-4">
                  {method.description}
                </p>
                <a
                  href={method.action}
                  className="text-[#D4AF37] hover:text-[#C49F2F] font-semibold transition-colors"
                >
                  {method.contact}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Form */}
      <section className="py-20 bg-gray-50 dark:bg-black">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Send Us a <span className="text-[#D4AF37]">Message</span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              Have questions? We&apos;d love to hear from you. Send us a message and we&apos;ll respond as soon as possible.
            </p>
          </div>

          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl p-8">
            <form className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                    First Name
                  </label>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    required
                    className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                    placeholder="John"
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                    Last Name
                  </label>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    required
                    className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                    placeholder="Doe"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  required
                  className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                  placeholder="john@company.com"
                />
              </div>

              <div>
                <label htmlFor="company" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Company
                </label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                  placeholder="Your Company Name"
                />
              </div>

              <div>
                <label htmlFor="subject" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Subject
                </label>
                <input
                  type="text"
                  id="subject"
                  name="subject"
                  required
                  className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                  placeholder="How can we help you?"
                />
              </div>

              <div>
                <label htmlFor="message" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Message
                </label>
                <textarea
                  id="message"
                  name="message"
                  rows={6}
                  required
                  className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors resize-none"
                  placeholder="Tell us about your project, questions, or how we can help..."
                />
              </div>

              <div className="text-center">
                <button
                  type="submit"
                  className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center"
                >
                  Send Message
                  <Send className="ml-2 h-5 w-5" />
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* Global Offices */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Our <span className="text-[#D4AF37]">Global</span> Presence
            </h2>
            <p className="text-xl text-gray-600 dark:text-white/70">
              We&apos;re proud to serve clients worldwide with offices across multiple continents
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {globalOffices.map((office, index) => (
              <div
                key={index}
                className="p-6 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:border-[#D4AF37] hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300"
              >
                <div className="flex items-start mb-4">
                  <MapPin className="h-5 w-5 text-[#D4AF37] mr-2 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {office.city}
                    </h3>
                    <p className="text-sm text-[#D4AF37] font-medium">
                      {office.country}
                    </p>
                  </div>
                </div>
                <div className="space-y-2 text-sm text-gray-600 dark:text-white/70">
                  <p className="flex items-start">
                    <MapPin className="h-4 w-4 mr-2 mt-0.5 flex-shrink-0" />
                    {office.address}
                  </p>
                  <p className="flex items-center">
                    <Phone className="h-4 w-4 mr-2 flex-shrink-0" />
                    <a href={`tel:${office.phone}`} className="hover:text-[#D4AF37] transition-colors">
                      {office.phone}
                    </a>
                  </p>
                  <p className="flex items-center">
                    <Mail className="h-4 w-4 mr-2 flex-shrink-0" />
                    <a href={`mailto:${office.email}`} className="hover:text-[#D4AF37] transition-colors">
                      {office.email}
                    </a>
                  </p>
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
            Ready to Get <span className="text-[#D4AF37]">Started</span>?
          </h2>
          <p className="text-xl text-gray-600 dark:text-white/70 mb-8">
            Let&apos;s discuss how AskTrabaajo can transform your hiring process and help you find the best talent.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/features"
              className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
            >
              Explore Features
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
