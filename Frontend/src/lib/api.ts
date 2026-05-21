const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem("auth_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "API request failed");
  }

  return response.json();
}

export const authApi = {
  login: async (firebaseToken: string, role?: string, name?: string) => {
    localStorage.setItem("auth_token", firebaseToken);
    return apiCall("/auth/login", {
      method: "POST",
      body: JSON.stringify({ name, role }),
    });
  },
  getMe: async () => {
    return apiCall("/auth/me");
  },
  logout: () => {
    localStorage.removeItem("auth_token");
  }
};

export const eventsApi = {
  getAll: async () => {
    return apiCall("/events");
  },
  getById: async (id: string) => {
    return apiCall(`/events/${id}`);
  },
  create: async (data: any) => {
    return apiCall("/events/create", {
      method: "POST",
      body: JSON.stringify(data)
    });
  },
  update: async (id: string, data: any) => {
    return apiCall(`/events/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  },
  delete: async (id: string) => {
    return apiCall(`/events/${id}`, {
      method: "DELETE"
    });
  }
};

export const roundsApi = {
  create: async (data: any) => apiCall("/rounds/create", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/rounds/${eventId}`)
};

export const participantsApi = {
  register: async (data: any) => apiCall("/participants/register", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/participants/${eventId}`)
};

export const teamsApi = {
  create: async (data: any) => apiCall("/teams/create", { method: "POST", body: JSON.stringify(data) }),
  assign: async (data: any) => apiCall("/teams/assign", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/teams/${eventId}`)
};

export const submissionsApi = {
  upload: async (data: any) => apiCall("/submissions/upload", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/submissions/${eventId}`)
};

export const judgesApi = {
  assign: async (data: any) => apiCall("/judges/assign", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/judges/${eventId}`)
};

export const evaluationsApi = {
  submit: async (data: any) => apiCall("/evaluations/submit", { method: "POST", body: JSON.stringify(data) }),
  getBySubmission: async (submissionId: string) => apiCall(`/evaluations/${submissionId}`)
};

export const reportsApi = {
  generate: async (data: any) => apiCall("/reports/generate", { method: "POST", body: JSON.stringify(data) }),
  getByEvent: async (eventId: string) => apiCall(`/reports/${eventId}`)
};

export const aiApi = {
  chat: async (messages: { role: string; content: string }[], event_id?: string | null) =>
    apiCall("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ messages, event_id: event_id || undefined }),
    }),
  saveConfig: async (event_config: Record<string, any>, event_id?: string | null) =>
    apiCall("/ai/save-config", {
      method: "POST",
      body: JSON.stringify({ event_config, event_id: event_id || undefined }),
    }),
  deploy: async (event_config: Record<string, any>, event_id?: string | null) =>
    apiCall("/ai/deploy", {
      method: "POST",
      body: JSON.stringify({ event_config, event_id: event_id || undefined }),
    }),
  getDeployedEvents: async () => apiCall("/ai/events"),
  getEventByHash: async (hash: string) => apiCall(`/ai/events/${hash}`),
};
