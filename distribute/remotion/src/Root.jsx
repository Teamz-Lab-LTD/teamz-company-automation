import React from "react";
import { Composition } from "remotion";
import { ToolReel } from "./ToolReel";
import { InstantFix } from "./templates/InstantFix";
import { BeforeAfter } from "./templates/BeforeAfter";
import { CompareThree } from "./templates/CompareThree";
import { ProofCase } from "./templates/ProofCase";

export const RemotionRoot = () => {
  const FPS = 30;

  return (
    <>
      {/* V2 Templates — 24 seconds each (6 slides × 4s) */}
      <Composition
        id="InstantFix"
        component={InstantFix}
        durationInFrames={720}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "Stop paying for this",
          title: "Grammar Checker",
          description: "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
          url: "tool.teamzlab.com/ai/grammar-checker/",
          audioFile: "",
          ctaText: "Try it now",
          ctaBadge: "LINK IN BIO",
          brandName: "tool.teamzlab.com",
          themeIndex: 0,
        }}
      />

      <Composition
        id="BeforeAfter"
        component={BeforeAfter}
        durationInFrames={720}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "This turned 2 hours into 2 minutes",
          title: "PDF Compressor",
          description: "Compress PDFs without losing quality.",
          url: "tool.teamzlab.com/pdf/pdf-compressor/",
          audioFile: "",
          themeIndex: 1,
          beforeState: "Manual work, paid tools, privacy concerns",
          afterState: "One click, free, 100% private",
        }}
      />

      <Composition
        id="CompareThree"
        component={CompareThree}
        durationInFrames={720}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "Which grammar tool is actually the best?",
          title: "Grammar Checker",
          url: "tool.teamzlab.com/ai/grammar-checker/",
          audioFile: "",
          themeIndex: 2,
          option1: { name: "Grammarly", price: "$12/mo", features: ["Cloud-based", "Tracks data"] },
          option2: { name: "ProWritingAid", price: "$20/mo", features: ["Desktop only", "Subscription"] },
          optionWinner: { name: "Teamz Lab", price: "FREE", features: ["Browser-based", "100% private"] },
        }}
      />

      <Composition
        id="ProofCase"
        component={ProofCase}
        durationInFrames={720}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "We saved this client $500/month",
          title: "Web Design Service",
          url: "teamzlab.com",
          audioFile: "",
          ctaText: "Get started",
          ctaBadge: "HIRE US",
          brandName: "teamzlab.com",
          themeIndex: 3,
          problemText: "Paying for 8 different tools",
          transformText: "We replaced them all with free alternatives",
        }}
      />

      {/* Legacy — keep backward compatible */}
      <Composition
        id="ToolReel"
        component={ToolReel}
        durationInFrames={420}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "Stop paying for this",
          title: "Grammar Checker",
          description: "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
          url: "tool.teamzlab.com/ai/grammar-checker/",
          audioFile: "",
        }}
      />
    </>
  );
};
