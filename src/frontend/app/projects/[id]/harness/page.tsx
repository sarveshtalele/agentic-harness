"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProjectHarnessRedirect() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/harness?project=${id}`);
  }, [id, router]);

  return null;
}
