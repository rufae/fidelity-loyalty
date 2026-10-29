import { PlatformSupportThreadDetailView } from "@/components/platform-support-thread-detail-view";

export default async function PlatformSupportThreadPage({
  params,
}: {
  params: Promise<{ threadId: string }>;
}) {
  const { threadId } = await params;
  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-10">
      <PlatformSupportThreadDetailView threadId={threadId} />
    </main>
  );
}
