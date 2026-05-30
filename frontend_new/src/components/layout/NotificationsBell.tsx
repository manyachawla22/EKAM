"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, Check, CheckCheck } from "lucide-react";
import { listMyNotifications, markNotificationRead } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Notification, NotificationType } from "@/types";

const POLL_MS = 30_000;
const MAX_PREVIEW = 25;

const TYPE_ACCENT: Record<NotificationType, string> = {
  info: "#60a5fa",
  alert: "#fbbf24",
  action_required: "#e8503a",
};

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const now = Date.now();
  const diffSec = Math.max(0, Math.floor((now - date.getTime()) / 1000));
  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)}d ago`;
  return date.toLocaleDateString();
}

export default function NotificationsBell() {
  const { user, profile } = useAuth();
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  const fetchNotifications = useCallback(async () => {
    if (!user || !profile) return;
    setLoading(true);
    try {
      const data = await listMyNotifications(false);
      setItems(data.slice(0, MAX_PREVIEW));
    } catch {
      // Don't toast — silent polling failure is fine, just leave the list as-is.
    } finally {
      setLoading(false);
    }
  }, [user, profile]);

  // Initial fetch + polling. Polling continues whether the popover is open or
  // not so the unread badge stays current.
  useEffect(() => {
    if (!user) return;
    fetchNotifications();
    const id = window.setInterval(fetchNotifications, POLL_MS);
    return () => window.clearInterval(id);
  }, [user, fetchNotifications]);

  // Close popover on outside click.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const unreadCount = items.filter((n) => !n.is_read).length;

  const handleMarkRead = async (n: Notification) => {
    if (n.is_read) return;
    // Optimistic update.
    setItems((prev) =>
      prev.map((it) => (it.id === n.id ? { ...it, is_read: true } : it))
    );
    try {
      await markNotificationRead(n.id);
    } catch {
      // Roll back on failure.
      setItems((prev) =>
        prev.map((it) => (it.id === n.id ? { ...it, is_read: false } : it))
      );
    }
  };

  const handleMarkAllRead = async () => {
    const unread = items.filter((n) => !n.is_read);
    if (!unread.length) return;
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    await Promise.all(
      unread.map((n) => markNotificationRead(n.id).catch(() => undefined))
    );
  };

  if (!user || !profile) return null;

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <button
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "2.25rem",
          width: "2.25rem",
          borderRadius: "0.5rem",
          background: open ? "rgba(255,255,255,0.06)" : "transparent",
          color: "rgba(255,255,255,0.75)",
          border: "1px solid",
          borderColor: open ? "#222" : "transparent",
          cursor: "pointer",
        }}
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "0.15rem",
              right: "0.15rem",
              minWidth: "1rem",
              height: "1rem",
              padding: "0 0.25rem",
              background: "#e8503a",
              color: "#fff",
              borderRadius: "9999px",
              fontSize: "0.65rem",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 0 2px #0a0a0a",
            }}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.12 }}
            style={{
              position: "absolute",
              top: "calc(100% + 0.5rem)",
              right: 0,
              width: "22rem",
              maxHeight: "28rem",
              borderRadius: "0.75rem",
              border: "1px solid #222",
              background: "#0f0f0f",
              boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
              overflow: "hidden",
              zIndex: 60,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                padding: "0.75rem 0.85rem",
                borderBottom: "1px solid #222",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  color: "#fff",
                }}
              >
                Notifications
                {unreadCount > 0 && (
                  <span
                    style={{
                      marginLeft: "0.4rem",
                      fontSize: "0.7rem",
                      color: "rgba(255,255,255,0.4)",
                      fontWeight: 500,
                    }}
                  >
                    {unreadCount} unread
                  </span>
                )}
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#e8503a",
                    fontSize: "0.72rem",
                    fontWeight: 500,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.25rem",
                    padding: 0,
                  }}
                >
                  <CheckCheck size={11} /> Mark all read
                </button>
              )}
            </div>

            <div style={{ overflowY: "auto", flex: 1 }}>
              {loading && items.length === 0 ? (
                <div
                  style={{
                    padding: "1.5rem",
                    fontSize: "0.8rem",
                    color: "rgba(255,255,255,0.4)",
                    textAlign: "center",
                  }}
                >
                  Loading…
                </div>
              ) : items.length === 0 ? (
                <div
                  style={{
                    padding: "2rem 1rem",
                    fontSize: "0.8rem",
                    color: "rgba(255,255,255,0.4)",
                    textAlign: "center",
                  }}
                >
                  You&apos;re all caught up.
                </div>
              ) : (
                items.map((n) => {
                  const accent = TYPE_ACCENT[n.type] || "#60a5fa";
                  const content = (
                    <div
                      onClick={() => {
                        handleMarkRead(n);
                        if (!n.action_link) setOpen(false);
                      }}
                      style={{
                        display: "flex",
                        gap: "0.6rem",
                        padding: "0.7rem 0.85rem",
                        borderBottom: "1px solid #1a1a1a",
                        background: n.is_read
                          ? "transparent"
                          : "rgba(232,80,58,0.04)",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          width: "0.4rem",
                          flexShrink: 0,
                          alignSelf: "stretch",
                          background: n.is_read ? "transparent" : accent,
                          borderRadius: "9999px",
                        }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "baseline",
                            gap: "0.5rem",
                          }}
                        >
                          <p
                            style={{
                              margin: 0,
                              fontSize: "0.82rem",
                              fontWeight: n.is_read ? 500 : 600,
                              color: n.is_read
                                ? "rgba(255,255,255,0.7)"
                                : "#fff",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {n.title}
                          </p>
                          <span
                            style={{
                              fontSize: "0.65rem",
                              color: "rgba(255,255,255,0.35)",
                              flexShrink: 0,
                            }}
                          >
                            {formatWhen(n.created_at)}
                          </span>
                        </div>
                        <p
                          style={{
                            margin: "0.2rem 0 0",
                            fontSize: "0.74rem",
                            color: "rgba(255,255,255,0.55)",
                            lineHeight: 1.4,
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {n.message}
                        </p>
                      </div>
                      {!n.is_read && (
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleMarkRead(n);
                          }}
                          title="Mark as read"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "rgba(255,255,255,0.4)",
                            cursor: "pointer",
                            alignSelf: "flex-start",
                            padding: "0.15rem",
                          }}
                        >
                          <Check size={13} />
                        </button>
                      )}
                    </div>
                  );

                  return n.action_link ? (
                    <Link
                      key={n.id}
                      href={n.action_link}
                      style={{ textDecoration: "none", color: "inherit" }}
                      onClick={() => setOpen(false)}
                    >
                      {content}
                    </Link>
                  ) : (
                    <div key={n.id}>{content}</div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
