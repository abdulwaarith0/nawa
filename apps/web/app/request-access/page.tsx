import { AuthShell } from "@/layouts";
import { RequestAccessWrapper } from "@/libs";

// Thin shell — renders the auth shell + the request-access feature module.
export default function RequestAccessPage() {
  return (
    <AuthShell storyKey="requestAccess">
      <RequestAccessWrapper />
    </AuthShell>
  );
}
