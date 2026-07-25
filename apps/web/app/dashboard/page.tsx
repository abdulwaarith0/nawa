import { DashboardWrapper } from "@/libs";

// Thin shell — ConsoleShell (inside DashboardWrapper) already provides chrome.
export default function DashboardPage() {
  return <DashboardWrapper />;
}
