import { TopNav } from "../src/components/shells/TopNav";
import { MarketingHome } from "../src/features/marketing/MarketingHome";

// Thin shell — TopNav + the marketing feature module.
export default function HomePage() {
  return (
    <>
      <TopNav />
      <MarketingHome />
    </>
  );
}
