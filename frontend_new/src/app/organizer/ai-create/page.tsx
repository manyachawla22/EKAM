"use client";

export const dynamic = "force-dynamic";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  User,
  Rocket,
  ChevronDown,
  ChevronUp,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { aiChat, aiDeploy } from "@/lib/api";
import type { AIChatMessage, EventConfig } from "@/types";
import Button from "@/components/ui/Button";

interface Message {
  role: "user" | "assistant";
  content: string;
}

function ConfigPreview({ config }: { config: EventConfig }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      style={{
        borderRadius: "0.75rem",
        border: "1px solid rgba(232,80,58,0.2)",
        background: "rgba(232,80,58,0.05)",
        padding: "1rem",
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "#e8503a",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: 0,
        }}
      >
        <span
          style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
        >
          <Zap size={16} />
          Event Config Being Built
        </span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: "hidden" }}
          >
            <pre
              style={{
                marginTop: "0.75rem",
                overflowX: "auto",
                borderRadius: "0.5rem",
                background: "#0a0a0a",
                padding: "0.75rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.7)",
              }}
            >
              {JSON.stringify(config, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
      {!expanded && (
        <div
          style={{
            marginTop: "0.75rem",
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          {config.name && (
            <span
              style={{
                borderRadius: "9999px",
                background: "rgba(255,255,255,0.05)",
                padding: "0.25rem 0.625rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              📋 {config.name}
            </span>
          )}
          {config.type && (
            <span
              style={{
                borderRadius: "9999px",
                background: "rgba(255,255,255,0.05)",
                padding: "0.25rem 0.625rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              🏷️ {config.type}
            </span>
          )}
          {config.max_participants && (
            <span
              style={{
                borderRadius: "9999px",
                background: "rgba(255,255,255,0.05)",
                padding: "0.25rem 0.625rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              👥 {config.max_participants} participants
            </span>
          )}
          {config.rounds && (
            <span
              style={{
                borderRadius: "9999px",
                background: "rgba(255,255,255,0.05)",
                padding: "0.25rem 0.625rem",
                fontSize: "0.75rem",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              🔄 {config.rounds.length} rounds
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default function AICreatePage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your AI event creation assistant. I'll help you design a complete event by asking you a few questions. Let's start — what type of event are you looking to create? (e.g., Hackathon, Coding Contest, Team Challenge)",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [eventConfig, setEventConfig] = useState<EventConfig | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [deployedEventId, setDeployedEventId] = useState<string | null>(null);
  const [inputFocus, setInputFocus] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const apiMessages: AIChatMessage[] = newMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await aiChat(
        apiMessages,
        undefined,
        eventConfig || undefined
      );

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.message },
      ]);

      if (response.event_config) {
        setEventConfig(response.event_config);
      }

      if (response.is_complete) {
        setIsComplete(true);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "AI chat failed");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!eventConfig) {
      toast.error("No event config to deploy");
      return;
    }
    setDeploying(true);
    try {
      const result = await aiDeploy(eventConfig);
      if (result.success && result.event_id) {
        setDeployedEventId(result.event_id);
        toast.success("Event submitted for approval — approve it in Approvals to publish (event + form go live together).");
      } else {
        toast.error("Deployment failed");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Deployment failed");
    } finally {
      setDeploying(false);
    }
  };

  const bubble = (role: "user" | "assistant"): React.CSSProperties => ({
    maxWidth: "80%",
    borderRadius: "1rem",
    padding: "0.75rem 1rem",
    fontSize: "0.875rem",
    lineHeight: 1.5,
    background: role === "assistant" ? "#1a1a1a" : "rgba(232,80,58,0.15)",
    color: role === "assistant" ? "rgba(255,255,255,0.9)" : "#fff",
    border:
      role === "assistant" ? "none" : "1px solid rgba(232,80,58,0.2)",
    borderTopLeftRadius: role === "assistant" ? "0.25rem" : "1rem",
    borderTopRightRadius: role === "assistant" ? "1rem" : "0.25rem",
  });

  const avatar = (role: "user" | "assistant"): React.CSSProperties => ({
    display: "flex",
    height: "2rem",
    width: "2rem",
    flexShrink: 0,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "9999px",
    background:
      role === "assistant" ? "rgba(232,80,58,0.2)" : "rgba(255,255,255,0.1)",
    color: role === "assistant" ? "#e8503a" : "#fff",
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 7rem)",
        maxWidth: "56rem",
        margin: "0 auto",
        width: "100%",
      }}
    >
      <div
        style={{
          marginBottom: "1rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <Bot size={24} color="#e8503a" />
            AI Event Creation
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            Chat with AI to design and deploy your event
          </p>
        </div>

        {deployedEventId && (
          <Button
            variant="primary"
            onClick={() =>
              router.push(`/organizer/events/${deployedEventId}`)
            }
          >
            <Rocket size={16} />
            View Event
          </Button>
        )}
      </div>

      {eventConfig && (
        <div style={{ marginBottom: "1rem" }}>
          <ConfigPreview config={eventConfig} />
        </div>
      )}

      {isComplete && !deployedEventId && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            marginBottom: "1rem",
            borderRadius: "0.75rem",
            border: "1px solid rgba(34,197,94,0.2)",
            background: "rgba(34,197,94,0.1)",
            padding: "1rem",
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: "12rem" }}>
            <p
              style={{
                fontWeight: 600,
                color: "#4ade80",
                margin: 0,
              }}
            >
              Event configuration complete!
            </p>
            <p
              style={{
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.4)",
                marginTop: "0.125rem",
              }}
            >
              Ready to deploy. Clicking deploy submits the event for approval — it goes live once you approve it in the Approvals panel.
            </p>
          </div>
          <Button variant="primary" loading={deploying} onClick={handleDeploy}>
            <Rocket size={16} />
            Deploy Event
          </Button>
        </motion.div>
      )}

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          borderRadius: "0.75rem",
          border: "1px solid #222",
          background: "#111",
          padding: "1.25rem",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        {messages.map((message, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            style={{
              display: "flex",
              gap: "0.75rem",
              flexDirection:
                message.role === "user" ? "row-reverse" : "row",
            }}
          >
            <div style={avatar(message.role)}>
              {message.role === "assistant" ? (
                <Bot size={16} />
              ) : (
                <User size={16} />
              )}
            </div>
            <div style={bubble(message.role)}>{message.content}</div>
          </motion.div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <div style={avatar("assistant")}>
              <Bot size={16} />
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.375rem",
                borderRadius: "1rem",
                borderTopLeftRadius: "0.25rem",
                background: "#1a1a1a",
                padding: "0.75rem 1rem",
              }}
            >
              {[0, 150, 300].map((d) => (
                <span
                  key={d}
                  style={{
                    height: "0.375rem",
                    width: "0.375rem",
                    borderRadius: "9999px",
                    background: "rgba(255,255,255,0.4)",
                    animation: "bounce 1.4s infinite",
                    animationDelay: `${d}ms`,
                    display: "inline-block",
                  }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div
        style={{
          marginTop: "1rem",
          display: "flex",
          gap: "0.75rem",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => setInputFocus(true)}
          onBlur={() => setInputFocus(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder={
            isComplete
              ? "Event is configured. Deploy it above!"
              : "Type your answer..."
          }
          disabled={loading || (isComplete && !!deployedEventId)}
          style={{
            flex: 1,
            borderRadius: "0.75rem",
            border: `1px solid ${inputFocus ? "#e8503a" : "#222"}`,
            background: "#111",
            padding: "0.75rem 1rem",
            fontSize: "0.875rem",
            color: "#fff",
            outline: "none",
            boxShadow: inputFocus
              ? "0 0 0 3px rgba(232,80,58,0.15)"
              : "none",
            transition: "all 0.2s",
            fontFamily: "inherit",
            boxSizing: "border-box",
            opacity: loading || (isComplete && !!deployedEventId) ? 0.5 : 1,
          }}
        />
        <Button
          variant="primary"
          onClick={sendMessage}
          loading={loading}
          disabled={!input.trim() || (isComplete && !!deployedEventId)}
        >
          <Send size={16} />
        </Button>
      </div>
    </div>
  );
}
