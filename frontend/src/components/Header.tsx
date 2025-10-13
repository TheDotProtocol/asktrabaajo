'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <Image
              src="/trabaajo-logo.png"
              alt="Ask Trabaajo Logo"
              width={40}
              height={40}
              className="h-8 sm:h-10 w-auto"
            />
            <span className="text-xl font-bold text-white">AskTrabaajo</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <Link href="/" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              Home
            </Link>
            <Link href="/about" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              About
            </Link>
            <Link href="/features" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              Features
            </Link>
            <Link href="/leadership" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              Leadership
            </Link>
            <Link href="/careers" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              Careers
            </Link>
            <Link href="/contact" className="text-white/80 hover:text-[#D4AF37] transition-colors">
              Contact
            </Link>
          </nav>

          {/* Auth Links */}
          <div className="hidden md:flex items-center space-x-4">
            <Link
              href="/login"
              className="text-white/80 hover:text-[#D4AF37] transition-colors"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-white"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/10">
            <nav className="flex flex-col space-y-4">
              <Link href="/" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                Home
              </Link>
              <Link href="/about" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                About
              </Link>
              <Link href="/features" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                Features
              </Link>
              <Link href="/leadership" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                Leadership
              </Link>
              <Link href="/careers" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                Careers
              </Link>
              <Link href="/contact" className="text-white/80 hover:text-[#D4AF37] transition-colors">
                Contact
              </Link>
              <div className="pt-4 border-t border-white/10">
                <Link
                  href="/login"
                  className="block text-white/80 hover:text-[#D4AF37] transition-colors mb-2"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="inline-block px-4 py-2 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors"
                >
                  Get Started
                </Link>
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
