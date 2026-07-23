"use client";

import Card from "@/components/Card";
import { EmptyState } from "@/components/States";
import { useT } from "@/i18n/useT";

// Placeholder state for module surfaces whose backend slice hasn't shipped yet
// (intake/journey/community/reports land in slices 06–09). Renders the "not
// available yet" empty state inside a card so the surface still designs a real
// state rather than a blank screen.
export default function ComingSoon() {
  const t = useT("console");

  return (
    <Card>
      <EmptyState headline={t("states.comingSoonTitle")} description={t("states.comingSoonBody")} />
    </Card>
  );
}
