import Navbar from "@/components/layout/Navbar";
import HeroSection from "@/components/landing/HeroSection";
import EventModesSection from "@/components/landing/EventModesSection";
import FeaturesSection from "@/components/landing/FeaturesSection";
import Link from "next/link";
import { Zap } from "lucide-react";

function Footer() {
  return (
    <footer className="border-t border-[#111] bg-[#0a0a0a] py-12">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex flex-col items-center gap-6 md:flex-row md:justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#e8503a]">
              <Zap className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-lg font-black italic text-white">EKAM</span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6 text-sm text-white/40">
            <Link href="/login" className="hover:text-white transition-colors">
              Login
            </Link>
            <Link href="/signup" className="hover:text-white transition-colors">
              Sign Up
            </Link>
          </div>

          {/* Copyright */}
          <p className="text-sm text-white/30">
            © {new Date().getFullYear()} EKAM. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar />
      <main>
        <HeroSection />
        <EventModesSection />
        <FeaturesSection />
      </main>
      <Footer />
    </div>
  );
}
