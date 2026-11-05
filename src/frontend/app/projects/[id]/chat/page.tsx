"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProjectChatRedirect() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/harness?project=${id}`);
  }, [id, router]);

  return null;
}
