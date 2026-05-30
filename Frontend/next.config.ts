import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    domains: [],
  },
  // Allow Firebase Google Sign-In popup to communicate with the opener window.
  // Without this override Next.js dev server sends COOP: same-origin which
  // blocks window.closed polling inside the Firebase popup flow, producing the
  // "Cross-Origin-Opener-Policy policy would block the window.closed call" warning
  // and causing signInWithPopup to silently hang or fail.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
