"use client";

import { useParams } from "next/navigation";
import ApprovalsPanel from "@/components/ui/ApprovalsPanel";

export default function EventLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { id } = useParams<{ id: string }>();

  return (
    <>
      {children}
      {id && <ApprovalsPanel eventId={id} />}
    </>
  );
}
