import { AuthShell } from "../../src/components/shells/AuthShell";
import { LoginForm } from "../../src/features/auth/LoginForm";

// Thin shell — renders the auth shell + the login feature module.
export default function LoginPage() {
  return (
    <AuthShell>
      <LoginForm />
    </AuthShell>
  );
}
