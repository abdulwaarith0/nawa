import { ProfileWrapper } from "@/libs";

interface PageProps {
  params: Promise<{ handle: string }>;
}

// The living Founder Profile page (surface map §8, `/profile/[handle]`).
export default async function ProfilePage({ params }: PageProps) {
  const { handle } = await params;
  return <ProfileWrapper handle={handle} />;
}
