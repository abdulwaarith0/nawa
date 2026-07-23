import { AuthShell } from "@/layouts";
import { LoginWrapper } from "@/libs";

// Thin shell — renders the auth shell + the login feature module.
export default function LoginPage() {
  return (
    <AuthShell>
      <LoginWrapper />
    </AuthShell>
  );
}
