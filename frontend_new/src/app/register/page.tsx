"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, CalendarClock, Users, User as UserIcon, Sparkles } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import { listPublicEvents } from "@/lib/api";
import type { PublicEventCard } from "@/types";

export default function PublicRegisterPage() {
  const [events, setEvents] = useState<PublicEventCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPublicEvents()
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load events"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 pt-28 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-10"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-[#e8503a]/30 bg-[#e8503a]/10 px-3 py-1 text-sm text-[#e8503a]">
            <Sparkles size={12} /> Open Registrations
          </span>
          <h1 className="mt-4 text-4xl font-black italic tracking-tight text-white sm:text-5xl">
            Find your event
          </h1>
          <p className="mt-2 max-w-2xl text-white/50">
            Browse live events and register — no account needed. Pick an event to see details
            and sign up as an individual or with your team.
          </p>
        </motion.div>

        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-48 animate-pulse rounded-2xl border border-white/5 bg-white/5" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-red-300">{error}</div>
        ) : events.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-12 text-center">
            <p className="text-lg text-white/60">No events are open for registration right now.</p>
            <p className="mt-1 text-sm text-white/40">Check back soon.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {events.map((e, i) => (
              <motion.div
                key={e.hash}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
              >
                <Link href={`/register/${e.hash}`} className="group block h-full">
                  <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-white/[0.02] p-6 transition-all hover:border-[#e8503a]/40 hover:bg-white/[0.04]">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="rounded-md bg-white/5 px-2 py-1 text-xs uppercase tracking-wide text-white/50">
                        {e.type}
                      </span>
                      <span
                        className={`flex items-center gap-1 text-xs ${
                          e.registration_open ? "text-emerald-400" : "text-white/40"
                        }`}
                      >
                        <CalendarClock size={12} />
                        {e.registration_open ? "Open" : "Closed"}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-white group-hover:text-[#e8503a]">
                      {e.name}
                    </h3>
                    {e.description && (
                      <p className="mt-2 line-clamp-3 flex-1 text-sm text-white/50">{e.description}</p>
                    )}
                    <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-4">
                      <span className="flex items-center gap-1.5 text-xs text-white/50">
                        {e.team_registration ? <Users size={14} /> : <UserIcon size={14} />}
                        {e.team_registration ? "Team registration" : "Individual"}
                      </span>
                      <span className="flex items-center gap-1 text-sm font-medium text-[#e8503a] opacity-0 transition-opacity group-hover:opacity-100">
                        Register <ArrowRight size={14} />
                      </span>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
