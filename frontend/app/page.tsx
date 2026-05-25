import { LandingNav } from "@/components/landing/LandingNav";
import { LandingHero } from "@/components/landing/LandingHero";
import { IntroSection } from "@/components/landing/IntroSection";

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-on-surface">
      <LandingNav />
      <LandingHero />
      <IntroSection />
    </main>
  );
}
