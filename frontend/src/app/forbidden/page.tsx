import Link from 'next/link';

export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-6 dark:bg-neutral-950">
      <div className="max-w-md rounded-xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
        <p className="text-xs uppercase tracking-wide text-neutral-400">403</p>
        <h1 className="mt-1 text-xl font-semibold">Access denied</h1>
        <p className="mt-2 text-sm text-neutral-500">
          You are signed in, but this workspace is outside your permissions.
        </p>
        <Link href="/jobseeker" className="mt-4 inline-block text-sm font-medium text-amber-600 hover:underline">
          Go to Career OS
        </Link>
      </div>
    </div>
  );
}
