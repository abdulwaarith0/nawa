import { TopNav } from "@/layouts";
import { MarketingWrapper } from "@/libs";

// Thin shell — TopNav + the marketing feature module.
export default function HomePage() {
  return (
    <>
      <TopNav />
      <MarketingWrapper />
    </>
  );
}
