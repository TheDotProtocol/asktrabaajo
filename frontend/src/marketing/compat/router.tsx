"use client";

import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AnchorHTMLAttributes,
  ReactNode,
  useEffect,
  useState,
} from "react";

type To = string | { pathname?: string; hash?: string; search?: string };

function resolveTo(to: To): string {
  if (typeof to === "string") return to;
  const path = to.pathname || "/";
  const search = to.search || "";
  const hash = to.hash
    ? to.hash.startsWith("#")
      ? to.hash
      : `#${to.hash}`
    : "";
  return `${path}${search}${hash}`;
}

export function Link({
  to,
  href,
  children,
  ...props
}: {
  to?: To;
  href?: string;
  children?: ReactNode;
} & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href">) {
  const dest = resolveTo(to ?? href ?? "/");
  return (
    <NextLink href={dest} {...props}>
      {children}
    </NextLink>
  );
}

export function useNavigate() {
  const router = useRouter();
  return (to: To) => {
    router.push(resolveTo(to));
  };
}

export function useLocation() {
  const pathname = usePathname() || "/";
  const [search, setSearch] = useState("");
  const [hash, setHash] = useState("");
  useEffect(() => {
    setSearch(window.location.search);
    setHash(window.location.hash);
  }, [pathname]);
  return { pathname, search, hash };
}
