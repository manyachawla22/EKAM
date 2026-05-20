"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppStore, Role } from "@/lib/store";
import { ThemeToggle } from "@/components/theme-toggle";
import { motion } from "framer-motion";
import { Zap, Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

export default function AuthPage() {
  const router = useRouter();
  const { login } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [role, setRole] = useState<Role>("organizer");

  // Login state
  const [loginEmail, setLoginEmail] = useState("demo@ekam.io");
  const [loginPass, setLoginPass] = useState("password123");

  // Signup state
  const [signupData, setSignupData] = useState({
    name: "", email: "", password: "", organization: "", gender: "", age: "", phone: "",
  });

  const roleRoutes: Record<Role, string> = {
    organizer: "/dashboard",
    judge: "/judge",
    participant: "/portal/P-001",
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPass) { toast.error("Please fill in all fields"); return; }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1200));
    login({ name: "Demo User", email: loginEmail, role, organization: "Ekam Inc." });
    toast.success(`Welcome back! Redirecting to ${role} dashboard...`);
    setTimeout(() => router.push(roleRoutes[role]), 500);
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signupData.name || !signupData.email || !signupData.password) {
      toast.error("Please fill in required fields"); return;
    }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1500));
    login({ name: signupData.name, email: signupData.email, role, organization: signupData.organization });
    toast.success("Account created! Redirecting...");
    setTimeout(() => router.push(roleRoutes[role]), 500);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden px-4">
      {/* Theme Toggle */}
      <div className="absolute top-4 right-4 z-50">
        <ThemeToggle />
      </div>
      {/* Background effects */}
      <div className="absolute inset-0 bg-muted/10" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/8 blur-[120px]" />
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-chart-4/8 blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="font-bold text-2xl">Ekam</span>
        </Link>

        <Card className="border-border/50 bg-card/80 backdrop-blur-xl shadow-2xl shadow-primary/5">
          <CardHeader className="text-center pb-4">
            <CardTitle className="text-xl">Welcome to Ekam</CardTitle>
            <CardDescription>Sign in to your account or create a new one</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Role Selector */}
            <div className="mb-6">
              <Label className="text-xs text-muted-foreground mb-2 block">I am a...</Label>
              <div className="grid grid-cols-3 gap-2">
                {(["organizer", "judge", "participant"] as Role[]).map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`py-2.5 px-3 rounded-xl text-xs font-medium border transition-all ${
                      role === r
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-muted/30 text-muted-foreground hover:border-primary/30"
                    }`}
                  >
                    {r === "organizer" ? "Organizer" : r === "judge" ? "Judge" : "Participant"}
                  </button>
                ))}
              </div>
            </div>

            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login">Login</TabsTrigger>
                <TabsTrigger value="signup">Sign Up</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <Input id="login-email" type="email" placeholder="you@example.com" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Password</Label>
                    <div className="relative">
                      <Input id="login-password" type={showPass ? "text" : "password"} value={loginPass} onChange={(e) => setLoginPass(e.target.value)} />
                      <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                        {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground">Demo credentials are pre-filled</p>
                  </div>
                  <Button type="submit" disabled={loading} className="w-full bg-primary hover:bg-primary/90">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Sign In as {role.charAt(0).toUpperCase() + role.slice(1)}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="signup">
                <form onSubmit={handleSignup} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="name" className="text-xs">Full Name *</Label>
                      <Input id="name" placeholder="Jane Doe" value={signupData.name} onChange={(e) => setSignupData({ ...signupData, name: e.target.value })} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="org" className="text-xs">Organization</Label>
                      <Input id="org" placeholder="Acme Inc." value={signupData.organization} onChange={(e) => setSignupData({ ...signupData, organization: e.target.value })} />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="signup-email" className="text-xs">Email *</Label>
                    <Input id="signup-email" type="email" placeholder="you@example.com" value={signupData.email} onChange={(e) => setSignupData({ ...signupData, email: e.target.value })} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="signup-pass" className="text-xs">Password *</Label>
                    <div className="relative">
                      <Input id="signup-pass" type={showPass ? "text" : "password"} placeholder="Min 8 characters" value={signupData.password} onChange={(e) => setSignupData({ ...signupData, password: e.target.value })} />
                      <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                        {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Gender</Label>
                      <Select value={signupData.gender} onValueChange={(v) => setSignupData({ ...signupData, gender: v ?? "" })}>
                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="male">Male</SelectItem>
                          <SelectItem value="female">Female</SelectItem>
                          <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="age" className="text-xs">Age</Label>
                      <Input id="age" type="number" placeholder="21" value={signupData.age} onChange={(e) => setSignupData({ ...signupData, age: e.target.value })} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="phone" className="text-xs">Phone</Label>
                      <Input id="phone" placeholder="+91..." value={signupData.phone} onChange={(e) => setSignupData({ ...signupData, phone: e.target.value })} />
                    </div>
                  </div>
                  <Button type="submit" disabled={loading} className="w-full bg-primary hover:bg-primary/90 mt-2">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Create Account
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground mt-6">
          By continuing, you agree to Ekam&apos;s Terms of Service and Privacy Policy.
        </p>
      </motion.div>
    </div>
  );
}
