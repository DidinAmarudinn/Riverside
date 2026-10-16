"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "./brand-mark";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/demo", label: "Live demo" },
  { href: "/kiosk", label: "Kiosk" },
  { href: "/manager", label: "Manager" },
  { href: "/manager/gaps", label: "Gaps" },
  { href: "/about", label: "About" },
] as const;

// "/manager" must not light up on "/manager/gaps", which has its own tab; product pages belong to Manager.
function isActive(pathname: string, href: string) {
  pathname = pathname.replace(/\/+$/, "") || "/"; // static export serves /manager/ with a trailing slash
  if (href === "/") return pathname === "/";
  if (href === "/manager") return pathname === "/manager" || pathname.startsWith("/manager/sku");
  return pathname.startsWith(href);
}

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="mx-auto flex w-full max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 pt-5 sm:px-8">
      <Link href="/" aria-label="Demand Radar home" className="rounded-xl">
        <BrandMark />
      </Link>
      <nav
        aria-label="Primary"
        className="no-scrollbar -mx-4 flex w-[calc(100%+2rem)] items-center gap-1.5 overflow-x-auto px-4 md:mx-0 md:w-auto md:px-0"
      >
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex-shrink-0 rounded-full px-4 py-2.5 text-body-medium transition-colors md:px-5",
                active
                  ? "bg-primary-fixed font-semibold text-on-primary-fixed"
                  : "bg-surface-container-lowest text-on-surface hover:bg-surface-container-high",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
