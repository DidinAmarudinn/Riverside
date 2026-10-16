import { cn } from "@/lib/utils";
import { TopNav } from "./top-nav";
import { SiteFooter } from "./site-footer";

export function PageShell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <main className={cn("flex-1", className)}>
        <div className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-8">
          {children}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
