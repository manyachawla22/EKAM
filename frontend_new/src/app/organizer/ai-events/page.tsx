"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Bot, Calendar, Users, ChevronRight, Zap } from "lucide-react";
import { toast } from "sonner";
import { listAIEvents } from "@/lib/api";
import type { Event } from "@/types";
import { EventStatusBadge, EventStageBadge } from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Link from "next/link";

export default function AIEventsPage() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAIEvents()
      .then(setEvents)
      .catch(() => toast.error("Failed to load AI-created events"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-black italic text-white flex items-center gap-2">
            <Bot className="h-6 w-6 text-[#e8503a]" />
            AI-Created Events
          </h1>
          <p className="mt-1 text-sm text-white/40">
            Events deployed via the AI event creation assistant
          </p>
        </div>
        <Button variant="primary" onClick={() => router.push("/organizer/ai-create")}>
          <Zap className="h-4 w-4" />
          Create with AI
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-44 rounded-xl bg-[#111] shimmer" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center gap-6 py-24 text-center"
        >
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-[#e8503a]/20 bg-[#e8503a]/5">
            <Bot className="h-10 w-10 text-[#e8503a]/60" />
          </div>
          <div>
            <p className="text-lg font-semibold text-white/60">No AI-created events yet</p>
            <p className="mt-1 text-sm text-white/30">
              Use the AI assistant to design and deploy your first event.
            </p>
          </div>
          <Button variant="primary" onClick={() => router.push("/organizer/ai-create")}>
            <Zap className="h-4 w-4" />
            Create with AI
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {events.map((event, i) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Link href={`/organizer/events/${event.id}`}>
                <motion.div
                  whileHover={{ y: -3 }}
                  className="group relative rounded-xl border border-[#222] bg-[#111] p-5 hover:border-[#e8503a]/30 transition-all cursor-pointer overflow-hidden"
                >
                  {/* AI badge */}
                  <div className="absolute top-3 right-3 flex items-center gap-1 rounded-full border border-[#e8503a]/20 bg-[#e8503a]/10 px-2 py-0.5">
                    <Bot className="h-3 w-3 text-[#e8503a]" />
                    <span className="text-[10px] font-semibold text-[#e8503a]">AI</span>
                  </div>

                  {/* Subtle glow on hover */}
                  <div className="pointer-events-none absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ background: "radial-gradient(circle at 50% 0%, rgba(232,80,58,0.06) 0%, transparent 70%)" }}
                  />

                  <div className="mb-3 flex flex-wrap gap-2 pr-16">
                    <EventStatusBadge status={event.status} />
                    <EventStageBadge stage={event.stage} />
                  </div>

                  <h3 className="font-bold text-white truncate pr-2">{event.name}</h3>
                  <p className="mt-0.5 text-sm font-medium text-[#e8503a]">{event.type}</p>
                  <p className="mt-2 text-xs text-white/40 line-clamp-2 leading-relaxed">
                    {event.description}
                  </p>

                  <div className="mt-4 flex items-center justify-between border-t border-[#222] pt-4">
                    <div className="flex items-center gap-3 text-xs text-white/30">
                      <span className="flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
                        {event.max_participants}
                      </span>
                      {event.created_at && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          {new Date(event.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <ChevronRight className="h-4 w-4 text-white/20 group-hover:text-[#e8503a] transition-colors" />
                  </div>
                </motion.div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
