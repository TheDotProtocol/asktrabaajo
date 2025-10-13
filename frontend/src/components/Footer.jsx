import React from 'react';
import { Link } from 'react-router-dom';
import { Mail, Globe } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="bg-gray-50 dark:bg-black border-t border-gray-200 dark:border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div className="col-span-1 sm:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <img
                src="https://customer-assets.emergentagent.com/job_trabaajo-ai-hr/artifacts/6u5qvy8h_Untitled-1.png"
                alt="Ask Trabaajo Logo"
                className="h-8 w-auto"
                style={{
                  filter: 'brightness(0) saturate(100%) invert(72%) sepia(51%) saturate(558%) hue-rotate(2deg) brightness(91%) contrast(86%)'
                }}
              />
              <div className="text-xl sm:text-2xl font-bold">
                <span className="text-gray-900 dark:text-white">Ask</span>
                <span className="text-[#D4AF37]">Trabaajo</span>
              </div>
            </div>
            <p className="text-gray-600 dark:text-white/60 text-sm mb-4 max-w-md">
              The AI + Blockchain HR Ecosystem that runs your HR like a Fortune 500 powerhouse.
            </p>
            <div className="flex items-center space-x-4">
              <a
                href="mailto:connect@asktrabaajo.com"
                className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] transition-colors duration-200"
              >
                <Mail size={20} />
              </a>
              <a
                href="#"
                className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] transition-colors duration-200"
              >
                <Globe size={20} />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-gray-900 dark:text-white font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li>
                <Link to="/features" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  Features
                </Link>
              </li>
              <li>
                <Link to="/about" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  About Us
                </Link>
              </li>
              <li>
                <Link to="/careers" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  Careers
                </Link>
              </li>
              <li>
                <Link to="/contact" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  Contact
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-gray-900 dark:text-white font-semibold mb-4">Legal</h3>
            <ul className="space-y-2">
              <li>
                <a href="#" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  Privacy Policy
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-600 dark:text-white/60 hover:text-[#D4AF37] dark:hover:text-[#D4AF37] text-sm transition-colors duration-200">
                  Terms of Service
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-200 dark:border-white/10 pt-6 sm:pt-8">
          <p className="text-gray-500 dark:text-white/40 text-xs sm:text-sm text-center">
            © 2025 Ask Trabaajo — An AR Holdings Company | Built with AI, Blockchain, and a Slight Attitude.
          </p>
        </div>
      </div>
    </footer>
  );
};