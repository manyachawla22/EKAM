// ── Mock Data for Ekam ──

export interface Event {
  id: string;
  hash: string;
  name: string;
  type: string;
  status: "draft" | "active" | "completed" | "archived";
  stage: string;
  participantCount: number;
  judgeCount: number;
  teamCount: number;
  maxParticipants: number;
  approvalStatus: "approved" | "pending" | "rejected";
  progress: number;
  createdAt: string;
  updatedAt: string;
  description: string;
  stages: EventStage[];
  rounds: Round[];
}

export interface EventStage {
  id: string;
  name: string;
  status: "completed" | "active" | "upcoming" | "skipped";
  owner: string;
  completionPct: number;
  lastUpdated: string;
  description: string;
}

export interface Participant {
  id: string;
  name: string;
  email: string;
  phone: string;
  institution: string;
  skills: string[];
  registrationStatus: "confirmed" | "pending" | "waitlisted" | "rejected";
  team: string;
  stage: string;
  avatar: string;
  gender: string;
  age: number;
  notes: string;
  atsScore: number;
}

export interface Judge {
  id: string;
  name: string;
  email: string;
  expertise: string[];
  assignedEvents: string[];
  avatar: string;
  institution: string;
  rating: number;
}

export interface Submission {
  id: string;
  teamName: string;
  eventHash: string;
  round: string;
  submittedAt: string;
  status: "pending" | "reviewed" | "flagged" | "finalised";
  score: number | null;
  panelAvg: number | null;
  feedback: string;
  attachments: string[];
  members: string[];
}

export interface Round {
  id: string;
  name: string;
  status: "completed" | "active" | "upcoming";
  startDate: string;
  endDate: string;
  participantsAdvanced: number;
  totalParticipants: number;
}

export interface Activity {
  id: string;
  action: string;
  actor: string;
  timestamp: string;
  type: "event" | "participant" | "judge" | "system" | "communication";
}

// ── Seed Data ──

export const mockEvents: Event[] = [
  {
    id: "evt-001", hash: "EF-7X9K2M", name: "HackSphere 2026", type: "Hackathon",
    status: "active", stage: "Hacking Phase", participantCount: 342, judgeCount: 12,
    teamCount: 68, maxParticipants: 500, approvalStatus: "approved", progress: 65,
    createdAt: "2026-04-15", updatedAt: "2026-05-18",
    description: "A 48-hour hackathon bringing together innovators to solve real-world challenges using AI, blockchain, and IoT.",
    stages: [
      { id: "s1", name: "Registration", status: "completed", owner: "Organizer", completionPct: 100, lastUpdated: "2026-04-20", description: "Open registration and collect participant details" },
      { id: "s2", name: "Resume Screening", status: "completed", owner: "System", completionPct: 100, lastUpdated: "2026-04-25", description: "Automated ATS scoring of applications" },
      { id: "s3", name: "Online Assessment", status: "completed", owner: "System", completionPct: 100, lastUpdated: "2026-05-01", description: "Technical assessment via HackerRank" },
      { id: "s4", name: "Team Formation", status: "completed", owner: "Participant", completionPct: 100, lastUpdated: "2026-05-05", description: "Participants form or join teams" },
      { id: "s5", name: "Theme Selection", status: "completed", owner: "Organizer", completionPct: 100, lastUpdated: "2026-05-08", description: "Teams select their problem statement" },
      { id: "s6", name: "Hacking Phase", status: "active", owner: "Participant", completionPct: 45, lastUpdated: "2026-05-18", description: "48-hour development sprint" },
      { id: "s7", name: "Submission", status: "upcoming", owner: "Participant", completionPct: 0, lastUpdated: "-", description: "Final project submission" },
      { id: "s8", name: "Judging", status: "upcoming", owner: "Judge", completionPct: 0, lastUpdated: "-", description: "Expert panel evaluation" },
      { id: "s9", name: "Results", status: "upcoming", owner: "Organizer", completionPct: 0, lastUpdated: "-", description: "Winner announcement and prizes" },
    ],
    rounds: [
      { id: "r1", name: "Screening Round", status: "completed", startDate: "2026-04-20", endDate: "2026-04-25", participantsAdvanced: 400, totalParticipants: 500 },
      { id: "r2", name: "Online Assessment", status: "completed", startDate: "2026-04-26", endDate: "2026-05-01", participantsAdvanced: 342, totalParticipants: 400 },
      { id: "r3", name: "Hackathon", status: "active", startDate: "2026-05-17", endDate: "2026-05-19", participantsAdvanced: 0, totalParticipants: 342 },
    ],
  },
  {
    id: "evt-002", hash: "EF-3P8N5Q", name: "CaseStorm Nationals", type: "Case Competition",
    status: "active", stage: "Preliminary Round", participantCount: 180, judgeCount: 8,
    teamCount: 36, maxParticipants: 200, approvalStatus: "approved", progress: 40,
    createdAt: "2026-03-10", updatedAt: "2026-05-17",
    description: "National-level case competition for MBA students tackling industry challenges from Fortune 500 companies.",
    stages: [
      { id: "s1", name: "Registration", status: "completed", owner: "Organizer", completionPct: 100, lastUpdated: "2026-03-20", description: "Open registration" },
      { id: "s2", name: "Screening", status: "completed", owner: "System", completionPct: 100, lastUpdated: "2026-04-01", description: "Application review" },
      { id: "s3", name: "Preliminary Round", status: "active", owner: "Judge", completionPct: 60, lastUpdated: "2026-05-17", description: "First round of case presentations" },
      { id: "s4", name: "Semi-Finals", status: "upcoming", owner: "Judge", completionPct: 0, lastUpdated: "-", description: "Top 12 teams compete" },
      { id: "s5", name: "Finals", status: "upcoming", owner: "Judge", completionPct: 0, lastUpdated: "-", description: "Grand finale" },
    ],
    rounds: [
      { id: "r1", name: "Screening", status: "completed", startDate: "2026-03-20", endDate: "2026-04-01", participantsAdvanced: 180, totalParticipants: 200 },
      { id: "r2", name: "Preliminary", status: "active", startDate: "2026-05-10", endDate: "2026-05-20", participantsAdvanced: 0, totalParticipants: 180 },
    ],
  },
  {
    id: "evt-003", hash: "EF-9W2L7R", name: "CodeArena Championship", type: "Coding Contest",
    status: "draft", stage: "Setup", participantCount: 0, judgeCount: 5,
    teamCount: 0, maxParticipants: 1000, approvalStatus: "pending", progress: 10,
    createdAt: "2026-05-10", updatedAt: "2026-05-18",
    description: "A competitive programming championship with algorithmic problem-solving across multiple difficulty tiers.",
    stages: [
      { id: "s1", name: "Setup", status: "active", owner: "Organizer", completionPct: 30, lastUpdated: "2026-05-18", description: "Event configuration" },
      { id: "s2", name: "Registration", status: "upcoming", owner: "Organizer", completionPct: 0, lastUpdated: "-", description: "Open registration" },
    ],
    rounds: [],
  },
];

const firstNames = ["Arjun", "Priya", "Kiran", "Sneha", "Rahul", "Ananya", "Vikram", "Meera", "Sahil", "Isha", "Aditya", "Riya", "Dev", "Tanya", "Nikhil", "Pooja", "Rohan", "Nisha", "Kartik", "Simran"];
const lastNames = ["Sharma", "Patel", "Singh", "Reddy", "Kumar", "Gupta", "Joshi", "Nair", "Mehta", "Rao", "Verma", "Das", "Chatterjee", "Iyer", "Bose", "Malik", "Shah", "Pandey", "Chopra", "Kapoor"];
const institutions = ["IIT Bombay", "IIT Delhi", "BITS Pilani", "NIT Trichy", "IIIT Hyderabad", "DTU", "NSUT", "VIT", "SRM University", "KIIT"];
const skillPool = ["React", "Python", "ML", "Node.js", "Rust", "Go", "TypeScript", "Flutter", "Docker", "AWS", "Solidity", "Figma", "Java", "C++", "TensorFlow"];
const teamNames = ["ByteForce", "Neural Ninjas", "CodeCrafters", "DataDragons", "PixelPioneers", "QuantumLeap", "AlgoAces", "CyberSamurai", "TechTitans", "InnoVentures", "CloudChasers", "DevDynamos", "HackHeroes", "LogicLords", "StackStorm"];

export const mockParticipants: Participant[] = Array.from({ length: 20 }, (_, i) => {
  const fn = firstNames[i % firstNames.length];
  const ln = lastNames[i % lastNames.length];
  return {
    id: `P-${String(i + 1).padStart(3, "0")}`,
    name: `${fn} ${ln}`,
    email: `${fn.toLowerCase()}.${ln.toLowerCase()}@email.com`,
    phone: `+91 ${Math.floor(7000000000 + Math.random() * 3000000000)}`,
    institution: institutions[i % institutions.length],
    skills: [skillPool[i % skillPool.length], skillPool[(i + 3) % skillPool.length], skillPool[(i + 7) % skillPool.length]],
    registrationStatus: (["confirmed", "confirmed", "confirmed", "pending", "waitlisted"] as const)[i % 5],
    team: teamNames[Math.floor(i / 3) % teamNames.length],
    stage: "Hacking Phase",
    avatar: "",
    gender: i % 3 === 0 ? "Female" : "Male",
    age: 19 + (i % 8),
    notes: i % 4 === 0 ? "Strong leadership potential" : "",
    atsScore: 60 + Math.floor(Math.random() * 40),
  };
});

export const mockJudges: Judge[] = [
  { id: "J-001", name: "Dr. Rajesh Iyer", email: "rajesh.iyer@judge.com", expertise: ["AI/ML", "Data Science"], assignedEvents: ["EF-7X9K2M", "EF-3P8N5Q"], avatar: "", institution: "IISc Bangalore", rating: 4.8 },
  { id: "J-002", name: "Prof. Meenakshi Rao", email: "meenakshi.rao@judge.com", expertise: ["Systems Design", "Cloud"], assignedEvents: ["EF-7X9K2M"], avatar: "", institution: "IIT Madras", rating: 4.9 },
  { id: "J-003", name: "Amit Deshmukh", email: "amit.d@judge.com", expertise: ["Product", "UX"], assignedEvents: ["EF-7X9K2M", "EF-3P8N5Q"], avatar: "", institution: "Flipkart", rating: 4.5 },
  { id: "J-004", name: "Sanya Kapoor", email: "sanya.k@judge.com", expertise: ["Blockchain", "FinTech"], assignedEvents: ["EF-3P8N5Q"], avatar: "", institution: "Razorpay", rating: 4.7 },
  { id: "J-005", name: "Dr. Vikram Nath", email: "vikram.n@judge.com", expertise: ["Algorithms", "Security"], assignedEvents: ["EF-7X9K2M"], avatar: "", institution: "Microsoft Research", rating: 4.6 },
];

export const mockSubmissions: Submission[] = [
  { id: "SUB-001", teamName: "ByteForce", eventHash: "EF-7X9K2M", round: "Hackathon", submittedAt: "2026-05-18T14:30:00", status: "pending", score: null, panelAvg: null, feedback: "", attachments: ["project-demo.mp4", "pitch-deck.pdf"], members: ["Arjun Sharma", "Priya Patel", "Kiran Singh"] },
  { id: "SUB-002", teamName: "Neural Ninjas", eventHash: "EF-7X9K2M", round: "Hackathon", submittedAt: "2026-05-18T15:00:00", status: "reviewed", score: 87, panelAvg: 82, feedback: "Excellent innovation in NLP. Minor UI issues noted.", attachments: ["demo-video.mp4", "docs.pdf"], members: ["Sneha Reddy", "Rahul Kumar", "Ananya Gupta"] },
  { id: "SUB-003", teamName: "CodeCrafters", eventHash: "EF-7X9K2M", round: "Hackathon", submittedAt: "2026-05-18T13:45:00", status: "flagged", score: 91, panelAvg: 74, feedback: "Score divergence flagged — 17 points above panel average.", attachments: ["app-build.zip"], members: ["Vikram Joshi", "Meera Nair", "Sahil Mehta"] },
  { id: "SUB-004", teamName: "DataDragons", eventHash: "EF-7X9K2M", round: "Hackathon", submittedAt: "2026-05-18T16:10:00", status: "reviewed", score: 78, panelAvg: 80, feedback: "Good concept but needs more technical depth.", attachments: ["presentation.pptx", "code-repo.zip"], members: ["Isha Rao", "Aditya Verma", "Riya Das"] },
  { id: "SUB-005", teamName: "PixelPioneers", eventHash: "EF-3P8N5Q", round: "Preliminary", submittedAt: "2026-05-17T10:00:00", status: "finalised", score: 92, panelAvg: 90, feedback: "Outstanding case analysis and presentation skills.", attachments: ["case-deck.pdf"], members: ["Dev Chatterjee", "Tanya Iyer"] },
];

export const mockActivities: Activity[] = [
  { id: "a1", action: "New team \"QuantumLeap\" registered for HackSphere 2026", actor: "System", timestamp: "2 min ago", type: "participant" },
  { id: "a2", action: "Judge Dr. Rajesh Iyer submitted evaluation for ByteForce", actor: "Dr. Rajesh Iyer", timestamp: "15 min ago", type: "judge" },
  { id: "a3", action: "Email campaign \"Round 3 Reminder\" sent to 342 participants", actor: "Ekam", timestamp: "1 hour ago", type: "communication" },
  { id: "a4", action: "Score anomaly detected: CodeCrafters (91 vs panel avg 74)", actor: "System", timestamp: "2 hours ago", type: "system" },
  { id: "a5", action: "CaseStorm Nationals moved to Preliminary Round", actor: "Organizer", timestamp: "3 hours ago", type: "event" },
  { id: "a6", action: "5 new participant registrations approved", actor: "System", timestamp: "5 hours ago", type: "participant" },
  { id: "a7", action: "Judge assignment updated for HackSphere 2026", actor: "Organizer", timestamp: "Yesterday", type: "judge" },
  { id: "a8", action: "Report generated: Round 2 Performance Summary", actor: "System", timestamp: "Yesterday", type: "system" },
];

export const scoreDistribution = [
  { range: "0-20", count: 2 }, { range: "21-40", count: 5 }, { range: "41-60", count: 12 },
  { range: "61-80", count: 28 }, { range: "81-100", count: 21 },
];

export const roundComparison = [
  { round: "Screening", advanced: 400, eliminated: 100 },
  { round: "OA", advanced: 342, eliminated: 58 },
  { round: "Hackathon", advanced: 0, eliminated: 0 },
];

export const teamBalanceData = [
  { skill: "Frontend", count: 45 }, { skill: "Backend", count: 52 }, { skill: "ML/AI", count: 38 },
  { skill: "Design", count: 22 }, { skill: "DevOps", count: 18 }, { skill: "Mobile", count: 28 },
];
