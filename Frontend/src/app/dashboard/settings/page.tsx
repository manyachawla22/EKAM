"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { Shield, Eye, EyeOff, Moon, Sun, Bell, Lock, Users, LayoutDashboard, Gavel, BarChart3, FileText, Calendar, Layers, Settings as SettingsIcon } from "lucide-react";

const rolePermissions = {
  organizer: ["Dashboard", "Create Event", "Events", "Participants", "Judges", "Rounds", "Reports", "Settings"],
  judge: ["Events (assigned)", "Submission Review", "Grading", "Anomaly Detection"],
  participant: ["Participant Portal", "Team View", "Submission"],
};

const permissionIcons: Record<string, React.ElementType> = {
  Dashboard: LayoutDashboard, "Create Event": Calendar, Events: Calendar, "Events (assigned)": Calendar,
  Participants: Users, Judges: Gavel, Rounds: Layers, Reports: BarChart3, Settings: SettingsIcon,
  "Submission Review": FileText, Grading: Gavel, "Anomaly Detection": Shield,
  "Participant Portal": Users, "Team View": Users, Submission: FileText,
};

export default function SettingsPage() {
  const { theme, toggleTheme } = useAppStore();

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your account and platform preferences.</p>
      </div>

      {/* Appearance */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader><CardTitle className="text-base">Appearance</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              <div>
                <Label>Dark Mode</Label>
                <p className="text-xs text-muted-foreground">Toggle between dark and light themes</p>
              </div>
            </div>
            <Switch checked={theme === "dark"} onCheckedChange={toggleTheme} />
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader><CardTitle className="text-base">Notifications</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: "Email Notifications", desc: "Receive event updates via email", defaultOn: true },
            { label: "Push Notifications", desc: "Browser push notifications", defaultOn: false },
            { label: "Anomaly Alerts", desc: "Instant alerts for score anomalies", defaultOn: true },
          ].map((n) => (
            <div key={n.label} className="flex items-center justify-between">
              <div>
                <Label>{n.label}</Label>
                <p className="text-xs text-muted-foreground">{n.desc}</p>
              </div>
              <Switch defaultChecked={n.defaultOn} onCheckedChange={() => toast.success(`${n.label} updated`)} />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Role Access */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Role-Based Access Control</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {(Object.entries(rolePermissions) as [string, string[]][]).map(([role, perms]) => (
            <div key={role}>
              <div className="flex items-center gap-2 mb-3">
                <Badge variant="outline" className="capitalize bg-primary/10 text-primary border-primary/20">{role}</Badge>
                <span className="text-xs text-muted-foreground">{perms.length} permissions</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {perms.map((p) => {
                  const Icon = permissionIcons[p] || Eye;
                  return (
                    <div key={p} className="flex items-center gap-2 p-2 rounded-lg bg-muted/20 border border-border/20">
                      <Icon className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs">{p}</span>
                    </div>
                  );
                })}
              </div>
              <Separator className="mt-4" />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-red-500/20 bg-card/80 backdrop-blur-sm">
        <CardHeader><CardTitle className="text-base text-red-400">Danger Zone</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <Label>Delete Account</Label>
              <p className="text-xs text-muted-foreground">Permanently delete your account and all data</p>
            </div>
            <Button variant="outline" size="sm" className="text-red-400 border-red-500/30 hover:bg-red-500/10" onClick={() => toast.error("This is a demo — no data will be deleted")}>
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
