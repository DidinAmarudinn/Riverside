"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity } from "lucide-react";
import { BrandMark } from "./brand-mark";
import { cn } from "@/lib/utils";
import { env } from "@/lib/env";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/manager", label: "Manager" },
  { href: "/manager/gaps", label: "Gaps" },
  { href: "/about", label: "About" },
] as const;

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-surface-container-lowest/95 shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between gap-6 px-8">
        <div className="flex items-center gap-8">
          <Link href="/" aria-label="Demand Radar home">
            <BrandMark />
          </Link>
          <nav
            aria-label="Primary"
            className="hidden items-center gap-1 rounded-xl bg-surface-container-low p-1 md:flex"
          >
            {NAV.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "rounded-lg px-4 py-1.5 transition-all",
                    active
                      ? "bg-surface-container text-headline-sm text-primary-container"
                      : "text-body-medium text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 rounded-xl bg-surface-container-low px-3 py-2 text-caption font-label-mono text-on-surface-variant lg:flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
            {env.dataMode === "live" ? "Live data" : "Demo mode"}
          </span>
          {env.githubUrl ? (
            <a
              href={env.githubUrl}
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-lg px-3 py-2 text-caption font-medium text-on-surface-variant transition hover:bg-surface-container hover:text-on-surface sm:block"
            >
              GitHub
            </a>
          ) : null}
          <span className="hidden items-center gap-1.5 rounded-lg bg-surface-container-low px-3 py-2 text-caption text-on-surface-variant xl:flex">
            <Activity className="h-4 w-4 text-primary" aria-hidden />
            WIB Active Shift
          </span>
        </div>
      </div>
    </header>
  );
}
