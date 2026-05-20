"use client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion, useInView } from "framer-motion";
import { useRef, useState } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Zap, Users, Shield, BarChart3, Mail, AlertTriangle, FileText, GitBranch,
  ChevronDown, ChevronUp, ArrowRight, Sparkles, Calendar, Gavel, UserCheck,
  LayoutDashboard, Trophy, Clock, CheckCircle2, Star
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } },
};

function Section({ children, className = "", id }: { children: React.ReactNode; className?: string; id?: string }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.section
      ref={ref}
      id={id}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      variants={stagger}
      className={className}
    >
      {children}
    </motion.section>
  );
}

const features = [
  { icon: Shield, title: "Role-Based Access", desc: "Granular permissions for organizers, judges, and participants with smart routing and contextual dashboards." },
  { icon: Calendar, title: "Event Creation", desc: "AI-assisted event setup with conversational wizards, schema generation, and multi-stage pipeline configuration." },
  { icon: Users, title: "Team Formation", desc: "Smart team matching, skill-based grouping, and dynamic roster management across events." },
  { icon: Gavel, title: "Judge Grading", desc: "Rubric-based evaluation with anomaly detection, score divergence alerts, and panel consensus tracking." },
  { icon: UserCheck, title: "Participant Tracking", desc: "Real-time participant pipeline from registration through screening, assessment, and final results." },
  { icon: Mail, title: "Automated Comms", desc: "Triggered email campaigns, WhatsApp notifications, and Discord integrations at every pipeline stage." },
  { icon: AlertTriangle, title: "Anomaly Detection", desc: "Automatic flagging of score divergences, suspicious patterns, and grading inconsistencies." },
  { icon: FileText, title: "Report Generation", desc: "One-click reports with score breakdowns, leaderboards, round comparisons, and exportable analytics." },
];

const steps = [
  { icon: Sparkles, title: "Configure Event", desc: "Set up your event with our intelligent wizard" },
  { icon: Users, title: "Onboard Teams", desc: "Registration, screening, and team formation" },
  { icon: GitBranch, title: "Run Rounds", desc: "Multi-stage competition with live tracking" },
  { icon: Gavel, title: "Evaluate", desc: "Judges grade with rubrics and anomaly checks" },
  { icon: Trophy, title: "Generate Results", desc: "Reports, leaderboards, and certificates" },
];

const stats = [
  { value: "50K+", label: "Participants Managed" },
  { value: "200+", label: "Events Orchestrated" },
  { value: "99.9%", label: "Uptime SLA" },
  { value: "4.9★", label: "Organizer Rating" },
];

const faqs = [
  { q: "What types of events does Ekam support?", a: "Ekam supports hackathons, case competitions, coding contests, ideathons, and any team-based competitive event with multi-stage workflows." },
  { q: "Is there a limit on participants?", a: "No hard limits. Ekam scales from 10-person workshops to 10,000+ participant hackathons with the same infrastructure." },
  { q: "How does anomaly detection work?", a: "Our system compares individual judge scores against the panel average. Significant divergences are automatically flagged for review, ensuring fair evaluation." },
  { q: "Can I customize the evaluation rubric?", a: "Yes. Define custom criteria, weights, scoring scales, and feedback templates for each round of your event." },
  { q: "Does Ekam integrate with external tools?", a: "Ekam connects with HackerRank, Discord, WhatsApp, Slack, Google Sheets, and custom APIs for seamless workflow automation." },
];

export default function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg">Ekam</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">How it Works</a>
            <a href="#previews" className="hover:text-foreground transition-colors">Previews</a>
            <a href="#faq" className="hover:text-foreground transition-colors">FAQ</a>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" render={<Link href="/auth" />}>Login</Button>
            <Button size="sm" render={<Link href="/auth" />} className="bg-primary hover:bg-primary/90">
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <Section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-primary/3" />
        <div className="absolute top-20 left-1/4 w-96 h-96 rounded-full bg-primary/8 blur-[120px]" />
        <div className="absolute top-40 right-1/4 w-72 h-72 rounded-full bg-chart-2/8 blur-[100px]" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-24 pb-20 text-center relative">
          <motion.div variants={fadeUp}>
            <Badge variant="outline" className="mb-6 px-4 py-1.5 text-sm border-primary/30 bg-primary/5">
              <Sparkles className="h-3.5 w-3.5 mr-2" />
              Intelligent Event Orchestration
            </Badge>
          </motion.div>
          <motion.h1 variants={fadeUp} className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1] max-w-4xl mx-auto">
            Orchestrate Events{" "}
            <span className="gradient-text">Like Never Before</span>
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            The all-in-one platform for hackathons, case competitions, and coding contests.
            From registration to results — automated, intelligent, and beautiful.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" render={<Link href="/auth" />} className="bg-primary hover:bg-primary/90 text-base px-8">
              Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button size="lg" variant="outline" render={<Link href="/dashboard" />} className="text-base px-8">
              Explore Demo
            </Button>
          </motion.div>
          {/* Mini dashboard preview */}
          <motion.div variants={fadeUp} className="mt-16 max-w-5xl mx-auto">
            <div className="rounded-2xl border border-border/50 bg-card/50 backdrop-blur-sm p-4 shadow-2xl shadow-primary/5">
              <div className="rounded-xl bg-background/80 border border-border/30 p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Active Events", val: "3", icon: Calendar, color: "text-primary" },
                    { label: "Participants", val: "522", icon: Users, color: "text-emerald-500" },
                    { label: "Judges", val: "25", icon: Gavel, color: "text-amber-500" },
                    { label: "Reports", val: "12", icon: BarChart3, color: "text-blue-500" },
                  ].map((s) => (
                    <div key={s.label} className="text-center p-4 rounded-xl bg-muted/30">
                      <s.icon className={`h-5 w-5 mx-auto mb-2 ${s.color}`} />
                      <p className="text-2xl font-bold">{s.val}</p>
                      <p className="text-xs text-muted-foreground">{s.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* Stats Strip */}
      <Section className="border-y border-border/50 bg-muted/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <motion.div key={s.label} variants={fadeUp} className="text-center">
                <p className="text-3xl sm:text-4xl font-bold gradient-text">{s.value}</p>
                <p className="text-sm text-muted-foreground mt-1">{s.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* Features */}
      <Section className="py-24" id="features">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <motion.div variants={fadeUp} className="text-center mb-16">
            <Badge variant="outline" className="mb-4 px-3 py-1 text-xs border-primary/30 bg-primary/5">Features</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Everything You Need to Run World-Class Events</h2>
            <p className="text-muted-foreground mt-4 max-w-2xl mx-auto">Built for organizers who demand precision, judges who need clarity, and participants who deserve transparency.</p>
          </motion.div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map((f, i) => (
              <motion.div key={f.title} variants={fadeUp}>
                <Card className="h-full border-border/50 bg-card/50 backdrop-blur-sm hover:border-primary/30 hover:bg-card/80 transition-all duration-300 group">
                  <CardContent className="p-6">
                    <div className="rounded-xl bg-primary/10 w-10 h-10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                      <f.icon className="h-5 w-5 text-primary" />
                    </div>
                    <h3 className="font-semibold mb-2">{f.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* How it Works */}
      <Section className="py-24 bg-muted/10" id="how-it-works">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <motion.div variants={fadeUp} className="text-center mb-16">
            <Badge variant="outline" className="mb-4 px-3 py-1 text-xs border-primary/30 bg-primary/5">How It Works</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">The Event Pipeline, Simplified</h2>
          </motion.div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {steps.map((step, i) => (
              <motion.div key={step.title} variants={fadeUp} className="relative">
                <Card className="h-full border-border/50 bg-card/50 backdrop-blur-sm text-center">
                  <CardContent className="p-6">
                    <div className="mx-auto rounded-full bg-primary w-12 h-12 flex items-center justify-center mb-4 text-primary-foreground font-bold text-lg">
                      {i + 1}
                    </div>
                    <step.icon className="h-6 w-6 mx-auto text-primary mb-3" />
                    <h3 className="font-semibold mb-1">{step.title}</h3>
                    <p className="text-xs text-muted-foreground">{step.desc}</p>
                  </CardContent>
                </Card>
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 transform -translate-y-1/2 z-10">
                    <ArrowRight className="h-5 w-5 text-primary/40" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* Previews */}
      <Section className="py-24" id="previews">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <motion.div variants={fadeUp} className="text-center mb-16">
            <Badge variant="outline" className="mb-4 px-3 py-1 text-xs border-primary/30 bg-primary/5">Role Views</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Tailored for Every Role</h2>
          </motion.div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { role: "Organizer", icon: LayoutDashboard, desc: "Full event control — create, manage, and monitor all stages from a unified command center.", link: "/dashboard", features: ["Event creation wizard", "Participant database", "Pipeline management", "Report generation"] },
              { role: "Judge", icon: Gavel, desc: "Focused evaluation workspace with rubrics, score tracking, and anomaly detection.", link: "/judge", features: ["Submission review", "Rubric grading", "Feedback forms", "Score analytics"] },
              { role: "Participant", icon: Star, desc: "Clean status portal showing progression, team details, and key dates at a glance.", link: "/portal/P-001", features: ["Event status tracking", "Team dashboard", "Submission portal", "Activity timeline"] },
            ].map((v) => (
              <motion.div key={v.role} variants={fadeUp}>
                <Card className="h-full border-border/50 bg-card/50 backdrop-blur-sm group hover:border-primary/30 transition-all">
                  <CardContent className="p-6 flex flex-col h-full">
                    <div className="rounded-xl bg-primary/10 w-12 h-12 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                      <v.icon className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">{v.role} View</h3>
                    <p className="text-sm text-muted-foreground mb-4">{v.desc}</p>
                    <ul className="space-y-2 mb-6 flex-1">
                      {v.features.map((f) => (
                        <li key={f} className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                    <Button variant="outline" render={<Link href={v.link} />} className="w-full group/btn">
                      Explore {v.role} View
                      <ArrowRight className="ml-2 h-3.5 w-3.5 transition-transform group-hover/btn:translate-x-0.5" />
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* FAQ */}
      <Section className="py-24 bg-muted/10" id="faq">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <Badge variant="outline" className="mb-4 px-3 py-1 text-xs border-primary/30 bg-primary/5">FAQ</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Frequently Asked Questions</h2>
          </motion.div>
          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <motion.div key={i} variants={fadeUp}>
                <Card
                  className="border-border/50 bg-card/50 backdrop-blur-sm cursor-pointer hover:border-primary/20 transition-all"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium text-sm">{faq.q}</h3>
                      {openFaq === i ? <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" /> : <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />}
                    </div>
                    {openFaq === i && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="text-sm text-muted-foreground mt-3 leading-relaxed"
                      >
                        {faq.a}
                      </motion.p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* CTA */}
      <Section className="py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <motion.div variants={fadeUp}>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">Ready to Orchestrate Your Next Event?</h2>
            <p className="text-muted-foreground mb-8 max-w-xl mx-auto">Join hundreds of organizers who trust Ekam to deliver flawless events, every time.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" render={<Link href="/auth" />} className="bg-primary hover:bg-primary/90 text-base px-8">
                Start Free Today <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" render={<Link href="/dashboard" />} className="text-base px-8">
                View Live Demo
              </Button>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-muted/10 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
                  <Zap className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="font-bold">Ekam</span>
              </div>
              <p className="text-xs text-muted-foreground">Intelligent Event Orchestration for the modern era.</p>
            </div>
            {[
              { title: "Product", links: ["Features", "Pricing", "Integrations", "Changelog"] },
              { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
              { title: "Legal", links: ["Privacy", "Terms", "Security", "Status"] },
            ].map((col) => (
              <div key={col.title}>
                <h4 className="font-semibold text-sm mb-3">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((l) => (
                    <li key={l}><a href="#" className="text-xs text-muted-foreground hover:text-foreground transition-colors">{l}</a></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-border/50 mt-8 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">© 2026 Ekam. All rights reserved.</p>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Built for hackathons, by hackers</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
