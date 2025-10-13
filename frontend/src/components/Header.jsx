import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

export const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { path: '/', label: 'Home' },
    { path: '/features', label: 'Features' },
    { path: '/about', label: 'About Us' },
    { path: '/leadership', label: 'Leadership' },
    { path: '/careers', label: 'Careers' },
    { path: '/contact', label: 'Contact' }
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? 'bg-white dark:bg-black/95 backdrop-blur-sm shadow-lg' : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="relative h-8 sm:h-10 w-auto">
              <img
                src="https://customer-assets.emergentagent.com/job_trabaajo-ai-hr/artifacts/6u5qvy8h_Untitled-1.png"
                alt="Ask Trabaajo Logo"
                className="h-8 sm:h-10 w-auto brightness-0 saturate-100"
                style={{
                  filter: 'brightness(0) saturate(100%) invert(72%) sepia(51%) saturate(558%) hue-rotate(2deg) brightness(91%) contrast(86%)'
                }}
              />
            </div>
            <div className="text-xl sm:text-2xl font-bold hidden sm:block">
              <span className="text-gray-900 dark:text-white">Ask</span>
              <span className="text-[#D4AF37]">Trabaajo</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center space-x-6 xl:space-x-8">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-sm font-medium transition-colors duration-200 ${
                  location.pathname === link.path
                    ? 'text-[#D4AF37]'
                    : 'text-gray-700 dark:text-white/80 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <ThemeToggle />
            <a
              href="#demo"
              className="px-4 xl:px-5 py-2 bg-[#D4AF37] text-black font-semibold rounded hover:bg-[#C49F2F] transition-colors duration-200"
            >
              Try Demo
            </a>
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex items-center space-x-3 lg:hidden">
            <ThemeToggle />
            <button
              className="text-gray-900 dark:text-white"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <nav className="lg:hidden mt-4 pb-4 space-y-3">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block text-sm font-medium transition-colors duration-200 ${
                  location.pathname === link.path
                    ? 'text-[#D4AF37]'
                    : 'text-gray-700 dark:text-white/80 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <a
              href="#demo"
              className="block w-full text-center px-5 py-2 bg-[#D4AF37] text-black font-semibold rounded hover:bg-[#C49F2F] transition-colors duration-200"
            >
              Try Demo
            </a>
          </nav>
        )}
      </div>
    </header>
  );
};