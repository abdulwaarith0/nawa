import { IntakeShortlistWrapper } from "@/libs";

interface PageProps {
  params: Promise<{ id: string }>;
}

// Ranked shortlist for one cycle (surface map §8, `/intake/cycles/[id]`).
export default async function IntakeCycleShortlistPage({ params }: PageProps) {
  const { id } = await params;
  return <IntakeShortlistWrapper cycleId={id} />;
}
