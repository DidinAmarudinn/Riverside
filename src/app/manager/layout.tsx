import { PageShell } from "@/components/layout/page-shell";

export default function ManagerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <PageShell>{children}</PageShell>;
}
