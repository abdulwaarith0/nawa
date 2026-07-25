import { ComingSoon } from "@/components";
import { OnboardingShell } from "@/layouts";

// Thin shell — the Founder Profile stepper (design-system §1.5) isn't built
// yet; this keeps homeForPermissions' fallback target from 404ing for a
// freshly signed-up member with no console/community permissions.
export default function OnboardingPage() {
  return (
    <OnboardingShell step={1} total={1}>
      <ComingSoon />
    </OnboardingShell>
  );
}
