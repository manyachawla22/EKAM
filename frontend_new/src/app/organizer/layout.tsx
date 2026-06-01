import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";

export default function OrganizerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a" }}>
      <Navbar />
      <Sidebar />
      <main
        style={{
          paddingTop: "5rem",
          paddingLeft: "1.5rem",
          paddingRight: "1.5rem",
          paddingBottom: "3rem",
          minHeight: "100vh",
          // The Sidebar writes its open width (15rem or 0) to this variable
          // on the <html> element so the main content shifts instead of
          // being covered.
          marginLeft: "var(--ekam-sb-width, 0px)",
          transition: "margin-left 0.25s",
        }}
      >
        {children}
      </main>
    </div>
  );
}
