import Image from 'next/image'
import { LOGO_URL } from '@/lib/brand'

type LogoProps = {
  size?: number
  className?: string
  variant?: 'gold' | 'adaptive'
  showWordmark?: boolean
}

export default function Logo({
  size = 40,
  className = '',
  variant = 'adaptive',
  showWordmark = true,
}: LogoProps) {
  const imageClass =
    variant === 'gold'
      ? 'logo-gold'
      : 'logo-adaptive'

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Image
        src={LOGO_URL}
        alt="Ask Trabaajo Logo"
        width={size}
        height={size}
        className={`h-8 sm:h-10 w-auto ${imageClass}`}
        priority
      />
      {showWordmark && (
        <span className="text-xl sm:text-2xl font-bold">
          <span className="text-gray-900 dark:text-white">Ask</span>
          <span className="text-[#D4AF37]">Trabaajo</span>
        </span>
      )}
    </div>
  )
}
