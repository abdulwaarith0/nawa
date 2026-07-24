import { IntakeScorecardWrapper } from "@/libs";

interface PageProps {
  params: Promise<{ id: string }>;
}

// Full scorecard + decision panel for one application (surface map §8,
// `/intake/applications/[id]`).
export default async function IntakeApplicationScorecardPage({ params }: PageProps) {
  const { id } = await params;
  return <IntakeScorecardWrapper applicationId={id} />;
}
