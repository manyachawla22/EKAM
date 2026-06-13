"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, FileUp, Loader2, Plus, Trash2, CheckCircle2, Users, User as UserIcon } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import DynamicField from "@/components/register/DynamicField";
import TurnstileWidget from "@/components/register/TurnstileWidget";
import { getPublicEvent, uploadPublicResume, registerPublic } from "@/lib/api";
import type { PublicEventDetail, RegistrationFormField } from "@/types";
import { toast } from "sonner";

interface Person {
  answers: Record<string, unknown>;
  resumeUrl: string;
  resumeName: string;
  prefilled: Set<string>;
  uploading: boolean;
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";

function emptyPerson(): Person {
  return { answers: {}, resumeUrl: "", resumeName: "", prefilled: new Set(), uploading: false };
}

export default function PublicEventRegisterPage() {
  const params = useParams();
  const hash = String(params.hash);

  const [detail, setDetail] = useState<PublicEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [teamName, setTeamName] = useState("");
  const [persons, setPersons] = useState<Person[]>([emptyPerson()]);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    getPublicEvent(hash)
      .then((d) => {
        setDetail(d);
        // Preformed-team events start with min_team_size member slots.
        if (d.team_registration) {
          const n = Math.max(d.min_team_size || 1, 1);
          setPersons(Array.from({ length: n }, emptyPerson));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load event"))
      .finally(() => setLoading(false));
  }, [hash]);

  const fields: RegistrationFormField[] = detail?.registration_form_fields || [];
  const isTeam = !!detail?.team_registration;

  const setAnswer = useCallback((idx: number, fieldId: string, value: unknown) => {
    setPersons((prev) => {
      const next = [...prev];
      const p = { ...next[idx], answers: { ...next[idx].answers, [fieldId]: value } };
      // Editing a field clears its "auto-filled" hint.
      if (p.prefilled.has(fieldId)) {
        const pf = new Set(p.prefilled);
        pf.delete(fieldId);
        p.prefilled = pf;
      }
      next[idx] = p;
      return next;
    });
  }, []);

  const handleResume = useCallback(
    async (idx: number, file: File) => {
      setPersons((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], uploading: true };
        return next;
      });
      try {
        const res = await uploadPublicResume(hash, file);
        setPersons((prev) => {
          const next = [...prev];
          const prefill = (res.prefill || {}) as Record<string, unknown>;
          const merged = { ...next[idx].answers };
          const pf = new Set(next[idx].prefilled);
          for (const [k, val] of Object.entries(prefill)) {
            if (val !== null && val !== undefined && val !== "") {
              merged[k] = val;
              pf.add(k);
            }
          }
          next[idx] = {
            ...next[idx],
            answers: merged,
            resumeUrl: res.url,
            resumeName: res.name,
            prefilled: pf,
            uploading: false,
          };
          return next;
        });
        const filled = Object.keys(res.prefill || {}).length;
        toast.success(filled ? `Resume parsed — ${filled} field(s) auto-filled` : "Resume uploaded");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Resume upload failed");
        setPersons((prev) => {
          const next = [...prev];
          next[idx] = { ...next[idx], uploading: false };
          return next;
        });
      }
    },
    [hash]
  );

  const addMember = () => {
    if (!detail) return;
    if (persons.length >= (detail.max_team_size || 4)) return;
    setPersons((p) => [...p, emptyPerson()]);
  };

  const removeMember = (idx: number) => {
    if (!detail) return;
    if (persons.length <= (detail.min_team_size || 1)) return;
    setPersons((p) => p.filter((_, i) => i !== idx));
  };

  const validate = (): string | null => {
    if (isTeam && !teamName.trim()) return "Please enter a team name.";
    for (let i = 0; i < persons.length; i++) {
      const p = persons[i];
      const who = isTeam ? (i === 0 ? "Team leader" : `Member ${i + 1}`) : "You";
      if (!p.resumeUrl) return `${who}: please upload a resume.`;
      for (const f of fields) {
        if (f.required) {
          const v = p.answers[f.field_id];
          if (v === undefined || v === null || (typeof v === "string" && !v.trim())) {
            return `${who}: "${f.label}" is required.`;
          }
        }
      }
    }
    if (SITE_KEY && !captchaToken) return "Please complete the captcha.";
    return null;
  };

  const submit = async () => {
    const err = validate();
    if (err) {
      toast.error(err);
      return;
    }
    setSubmitting(true);
    try {
      if (isTeam) {
        await registerPublic(hash, {
          captcha_token: captchaToken || undefined,
          team_name: teamName.trim(),
          members: persons.map((p, i) => ({
            answers: p.answers,
            resume_url: p.resumeUrl,
            is_leader: i === 0,
          })),
        });
      } else {
        await registerPublic(hash, {
          captcha_token: captchaToken || undefined,
          answers: persons[0].answers,
          resume_url: persons[0].resumeUrl,
        });
      }
      setDone(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a]">
        <Navbar />
        <div className="mx-auto max-w-3xl px-6 pt-32">
          <div className="h-64 animate-pulse rounded-2xl border border-white/5 bg-white/5" />
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-[#0a0a0a]">
        <Navbar />
        <div className="mx-auto max-w-3xl px-6 pt-32">
          <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-red-300">
            {error || "Event not found."}
          </div>
          <Link href="/register" className="mt-4 inline-flex items-center gap-1 text-sm text-[#e8503a]">
            <ArrowLeft size={14} /> Back to events
          </Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen bg-[#0a0a0a]">
        <Navbar />
        <div className="mx-auto max-w-2xl px-6 pt-32 text-center">
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
            <CheckCircle2 className="mx-auto h-16 w-16 text-emerald-400" />
            <h1 className="mt-4 text-3xl font-black italic text-white">You&apos;re registered!</h1>
            <p className="mt-2 text-white/50">
              Your registration for <span className="text-white">{detail.name}</span> is confirmed.
            </p>
            <Link
              href="/register"
              className="mt-6 inline-flex items-center gap-1 rounded-lg bg-[#e8503a] px-5 py-2.5 text-sm font-semibold text-white"
            >
              Browse more events
            </Link>
          </motion.div>
        </div>
      </div>
    );
  }

  const closed = !detail.registration_open;

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 pt-28 pb-20">
        <Link href="/register" className="inline-flex items-center gap-1 text-sm text-white/50 hover:text-white">
          <ArrowLeft size={14} /> All events
        </Link>

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-white/40">
            <span className="rounded bg-white/5 px-2 py-1">{detail.type}</span>
            <span className="flex items-center gap-1">
              {isTeam ? <Users size={12} /> : <UserIcon size={12} />}
              {isTeam ? "Team registration" : "Individual registration"}
            </span>
          </div>
          <h1 className="mt-3 text-3xl font-black italic text-white">{detail.name}</h1>
          {detail.description && <p className="mt-2 text-white/60">{detail.description}</p>}
          {detail.rounds.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {detail.rounds.map((r, i) => (
                <span key={i} className="rounded-md border border-white/10 px-2 py-1 text-xs text-white/50">
                  {r.name}
                </span>
              ))}
            </div>
          )}
        </div>

        {closed ? (
          <div className="mt-6 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6 text-amber-300">
            Registration is currently closed for this event.
          </div>
        ) : fields.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.02] p-6 text-white/50">
            The registration form for this event is not published yet. Please check back soon.
          </div>
        ) : (
          <div className="mt-6 space-y-6">
            {isTeam && (
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                <label className="mb-1.5 block text-sm font-medium text-white/80">
                  Team name <span className="text-[#e8503a]">*</span>
                </label>
                <input
                  className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white outline-none focus:border-[#e8503a]/50"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  placeholder="e.g. The Innovators"
                />
                <p className="mt-2 text-xs text-white/40">
                  As team leader, fill in each member&apos;s details and resume ({detail.min_team_size}–
                  {detail.max_team_size} members).
                </p>
              </div>
            )}

            {persons.map((p, idx) => (
              <div key={idx} className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-semibold text-white">
                    {isTeam ? (idx === 0 ? "Team Leader" : `Member ${idx + 1}`) : "Your details"}
                  </h3>
                  {isTeam && persons.length > (detail.min_team_size || 1) && (
                    <button
                      onClick={() => removeMember(idx)}
                      className="flex items-center gap-1 text-xs text-white/40 hover:text-red-400"
                    >
                      <Trash2 size={12} /> Remove
                    </button>
                  )}
                </div>

                {/* Resume-first: upload drives auto-fill */}
                <div className="mb-4">
                  <label className="mb-1.5 block text-sm font-medium text-white/80">
                    Resume (PDF) <span className="text-[#e8503a]">*</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-white/20 bg-white/[0.02] px-3 py-3 text-sm text-white/60 hover:border-[#e8503a]/40">
                    {p.uploading ? (
                      <Loader2 size={16} className="animate-spin text-[#e8503a]" />
                    ) : (
                      <FileUp size={16} className="text-[#e8503a]" />
                    )}
                    <span>
                      {p.uploading
                        ? "Parsing resume…"
                        : p.resumeName
                        ? `${p.resumeName} — replace`
                        : "Upload resume to auto-fill the form"}
                    </span>
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleResume(idx, f);
                      }}
                    />
                  </label>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {fields.map((f) => (
                    <div key={f.field_id} className={f.type === "textarea" ? "sm:col-span-2" : ""}>
                      <DynamicField
                        field={f}
                        value={p.answers[f.field_id]}
                        prefilled={p.prefilled.has(f.field_id)}
                        onChange={(v) => setAnswer(idx, f.field_id, v)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {isTeam && persons.length < (detail.max_team_size || 4) && (
              <button
                onClick={addMember}
                className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-white/20 py-3 text-sm text-white/60 hover:border-[#e8503a]/40 hover:text-white"
              >
                <Plus size={16} /> Add member
              </button>
            )}

            {SITE_KEY && <TurnstileWidget onToken={setCaptchaToken} />}

            <button
              onClick={submit}
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#e8503a] py-3.5 text-base font-semibold text-white transition-all hover:shadow-[0_0_30px_rgba(232,80,58,0.4)] disabled:opacity-50"
            >
              {submitting && <Loader2 size={18} className="animate-spin" />}
              {submitting ? "Registering…" : "Complete Registration"}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
