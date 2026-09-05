'use client'

import { usePathname } from 'next/navigation'
import Header from '@/components/Header'
import Link from 'next/link'
import Logo from '@/components/Logo'
import { MarketingShell } from '@/marketing/MarketingShell'

function SiteFooter() {
  return (
    <footer className="bg-gray-50 dark:bg-black text-gray-900 dark:text-white py-16 border-t border-gray-200 dark:border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <div className="mb-4">
              <Logo showWordmark />
            </div>
            <p className="text-gray-600 dark:text-white/70 mb-4 max-w-md">
              The HR Department That Runs Itself. Powered by AI, secured by blockchain.
            </p>
            <p>&copy; 2026 AskTrabaajo Corp, a AR Holdings Group Company. All rights reserved.</p>
          </div>
          <div>
            <h3 className="font-semibold mb-4">Product</h3>
            <ul className="space-y-2 text-gray-600 dark:text-white/70">
              <li><Link href="/features" className="hover:text-[#D4AF37] transition-colors">Features</Link></li>
              <li><Link href="/pricing" className="hover:text-[#D4AF37] transition-colors">Pricing</Link></li>
              <li><Link href="/demo" className="hover:text-[#D4AF37] transition-colors">Demo</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-2 text-gray-600 dark:text-white/70">
              <li><Link href="/about" className="hover:text-[#D4AF37] transition-colors">About</Link></li>
              <li><Link href="/leadership" className="hover:text-[#D4AF37] transition-colors">Leadership</Link></li>
              <li><Link href="/careers" className="hover:text-[#D4AF37] transition-colors">Careers</Link></li>
              <li><Link href="/contact" className="hover:text-[#D4AF37] transition-colors">Contact</Link></li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  )
}

const MARKETING_EXACT = new Set([
  '/',
  '/about',
  '/contact',
  '/privacy',
  '/terms',
  '/payment-policy',
  '/refund-policy',
  '/jobseekers',
  '/companies',
  '/recruiters',
  '/governments',
  '/institutions',
])

const STANDALONE_PREFIXES = [
  '/careers',
  '/dashboard/candidate',
  '/dashboard/employer',
  '/jobseeker',
  '/company',
  '/employer',
  '/admin',
  '/id',
  '/forbidden',
  '/login',
  '/register',
  '/forgot-password',
  '/portals',
  '/government',
]

export default function ConditionalChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  if (MARKETING_EXACT.has(pathname)) {
    return <MarketingShell>{children}</MarketingShell>
  }
  const standalone = STANDALONE_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  )

  if (standalone) {
    return <>{children}</>
  }

  return (
    <>
      <Header />
      {children}
      <SiteFooter />
    </>
  )
}
