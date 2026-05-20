"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useAppStore } from "@/lib/store";
import {
  Zap, LayoutDashboard, Plus, Calendar, Users, Gavel, Layers, BarChart3, Settings,
  Menu, Moon, Sun, LogOut, ChevronLeft
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/create", label: "Create Event", icon: Plus },
  { href: "/dashboard/events", label: "Events", icon: Calendar },
  { href: "/dashboard/participants", label: "Participants", icon: Users },
  { href: "/dashboard/judges", label: "Judges", icon: Gavel },
  { href: "/dashboard/rounds", label: "Rounds", icon: Layers },
  { href: "/dashboard/reports", label: "Reports", icon: BarChart3 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

function SidebarContent({ collapsed, pathname }: { collapsed: boolean; pathname: string }) {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 flex items-center gap-2">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <Zap className="h-4 w-4 text-white" />
        </div>
        {!collapsed && <span className="font-bold text-lg">Ekam</span>}
      </div>
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                collapsed && "justify-center px-2"
              )}
            >
              <item.icon className="h-4.5 w-4.5 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, toggleTheme, user, logout } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen flex">
      {/* Desktop Sidebar */}
      <aside className={cn(
        "hidden lg:flex flex-col border-r border-border/50 bg-card/30 backdrop-blur-sm transition-all duration-300",
        collapsed ? "w-16" : "w-56"
      )}>
        <SidebarContent collapsed={collapsed} pathname={pathname} />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="m-2 p-2 rounded-lg text-muted-foreground hover:bg-muted/50 transition-colors"
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-40 h-14 border-b border-border/50 bg-background/80 backdrop-blur-xl flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Sheet>
              <SheetTrigger render={
                <Button variant="ghost" size="icon" className="lg:hidden" />
              }>
                <Menu className="h-5 w-5" />
              </SheetTrigger>
              <SheetContent side="left" className="w-56 p-0">
                <SidebarContent collapsed={false} pathname={pathname} />
              </SheetContent>
            </Sheet>
            <h1 className="text-sm font-semibold capitalize">
              {navItems.find((n) => pathname === n.href || (n.href !== "/dashboard" && pathname.startsWith(n.href)))?.label || "Dashboard"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger render={
                <Button variant="ghost" className="relative h-8 w-8 rounded-full" />
              }>
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                      {user?.name?.charAt(0) || "D"}
                    </AvatarFallback>
                  </Avatar>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-3 py-2">
                  <p className="text-sm font-medium">{user?.name || "Demo User"}</p>
                  <p className="text-xs text-muted-foreground">{user?.email || "demo@ekam.io"}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem render={<Link href="/dashboard/settings" />}>Settings</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => { logout(); window.location.href = "/"; }}>
                  <LogOut className="h-4 w-4 mr-2" /> Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 sm:p-6 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
