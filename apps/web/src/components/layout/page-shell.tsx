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
      <main className={cn("flex-1 pt-16", className)}>
        <div className="mx-auto w-full max-w-[1600px] px-8 py-6">
          {children}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
