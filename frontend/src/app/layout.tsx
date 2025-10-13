import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Menu, X } from "lucide-react";
import { useState } from "react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AskTrabaajo - AI-Powered HRTech Platform",
  description: "Resume-free, AI-based recruitment engine with video interviews and blockchain security",
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '32x32', type: 'image/x-icon' },
      { url: '/trabaajo-logo.png', sizes: '16x16', type: 'image/png' },
      { url: '/trabaajo-logo.png', sizes: '32x32', type: 'image/png' },
      { url: '/trabaajo-logo.png', sizes: '64x64', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    other: [
      { url: '/android-chrome-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/android-chrome-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
  manifest: '/site.webmanifest',
};

function Header() {
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

function Footer() {
  return (
    <footer className="bg-black text-white py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center space-x-2 mb-4">
              <Image
                src="/trabaajo-logo.png"
                alt="Ask Trabaajo Logo"
                width={32}
                height={32}
                className="h-8 w-auto"
              />
              <span className="text-xl font-bold">AskTrabaajo</span>
            </div>
            <p className="text-white/70 mb-4 max-w-md">
              The HR Department That Runs Itself. Powered by AI, secured by blockchain.
            </p>
            <p>&copy; 2024 AskTrabaajo Corp, a AR Holdings Group Company. All rights reserved.</p>
            <p className="mt-2 text-xs text-gray-500">AskTrabaajo Corp is a subsidiary of AR Holdings Group, dedicated to revolutionizing HR technology worldwide.</p>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Product</h3>
            <ul className="space-y-2 text-white/70">
              <li><Link href="/features" className="hover:text-[#D4AF37] transition-colors">Features</Link></li>
              <li><Link href="/pricing" className="hover:text-[#D4AF37] transition-colors">Pricing</Link></li>
              <li><Link href="/demo" className="hover:text-[#D4AF37] transition-colors">Demo</Link></li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-2 text-white/70">
              <li><Link href="/about" className="hover:text-[#D4AF37] transition-colors">About</Link></li>
              <li><Link href="/leadership" className="hover:text-[#D4AF37] transition-colors">Leadership</Link></li>
              <li><Link href="/careers" className="hover:text-[#D4AF37] transition-colors">Careers</Link></li>
              <li><Link href="/contact" className="hover:text-[#D4AF37] transition-colors">Contact</Link></li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Header />
        {children}
        <Footer />
      </body>
    </html>
  );
}