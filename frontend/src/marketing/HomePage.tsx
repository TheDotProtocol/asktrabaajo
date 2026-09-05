"use client";

import { useEffect } from "react";
import { useLocation } from "@/marketing/compat/router";
import { scrollToId } from "@/marketing/config/site";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import Hero from "@/marketing/components/Hero";
import Marquee from "@/marketing/components/common/Marquee";
import BigIdea from "@/marketing/sections/BigIdea";
import WorkId from "@/marketing/sections/WorkId";
import TalentGraph from "@/marketing/sections/TalentGraph";
import CompanyOS from "@/marketing/sections/CompanyOS";
import Athena from "@/marketing/sections/Athena";
import Interviewer from "@/marketing/sections/Interviewer";
import CareerAdvisor from "@/marketing/sections/CareerAdvisor";
import Government from "@/marketing/sections/Government";
import WorldMap from "@/marketing/sections/WorldMap";
import Credentials from "@/marketing/sections/Credentials";
import Communication from "@/marketing/sections/Communication";
import Governance from "@/marketing/sections/Governance";
import Ecosystem from "@/marketing/sections/Ecosystem";
import Audiences from "@/marketing/sections/Audiences";
import Philosophy from "@/marketing/sections/Philosophy";
import Platform from "@/marketing/sections/Vision";
import FinalCTA from "@/marketing/sections/FinalCTA";

export default function HomePage() {
  const { hash } = useLocation();
  usePageMeta();

  useEffect(() => {
    if (!hash) return;
    const t = setTimeout(() => scrollToId(hash), 120);
    return () => clearTimeout(t);
  }, [hash]);

  return (
    <main id="main-content">
      <Hero />
      <Marquee />
      <BigIdea />
      <WorkId />
      <TalentGraph />
      <CompanyOS />
      <Athena />
      <Interviewer />
      <CareerAdvisor />
      <Government />
      <WorldMap />
      <Credentials />
      <Communication />
      <Governance />
      <Ecosystem />
      <Audiences />
      <Philosophy />
      <Platform />
      <FinalCTA />
    </main>
  );
}
