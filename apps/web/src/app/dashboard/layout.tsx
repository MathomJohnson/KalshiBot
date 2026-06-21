/**
 * Shared dashboard navigation and layout shell.
 */
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

const navItems = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/mappings", label: "Mappings" },
  { href: "/dashboard/matches", label: "Matches" },
  { href: "/dashboard/config", label: "Config" },
  { href: "/dashboard/snapshots", label: "Snapshots" },
  { href: "/dashboard/signals", label: "Signals" },
  { href: "/dashboard/orders", label: "Orders" },
  { href: "/dashboard/fills", label: "Fills" },
  { href: "/dashboard/worker", label: "Worker" },
];

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("is_allowed")
    .eq("id", user.id)
    .single<{ is_allowed: boolean }>();

  if (!profile?.is_allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <h1 className="text-xl font-bold mb-2">Access Denied</h1>
          <p className="text-gray-400">
            Your account is not allowlisted. Set profiles.is_allowed = true in Supabase.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-[var(--border)] bg-[var(--card)] p-4 flex flex-col">
        <h1 className="text-lg font-bold mb-6 text-[var(--accent)]">KalshiBot</h1>
        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-sm hover:bg-[var(--background)] transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <form action="/auth/signout" method="post">
          <button
            type="submit"
            className="text-sm text-gray-400 hover:text-white w-full text-left px-3 py-2"
          >
            Sign out
          </button>
        </form>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
