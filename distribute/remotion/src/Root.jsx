import React from "react";
import { Composition } from "remotion";
import { ToolReel } from "./ToolReel";
import { InstantFix } from "./templates/InstantFix";
import { BeforeAfter } from "./templates/BeforeAfter";
import { CompareThree } from "./templates/CompareThree";
import { ProofCase } from "./templates/ProofCase";
import { Tutorial } from "./templates/Tutorial";

export const RemotionRoot = () => {
  const FPS = 30;

  // Duration varies per template to avoid identical-length spam detection.
  // Templates internally use durationInFrames prop to adjust slide timing.
  // render-batch.js randomizes within each template's range.
  const DURATIONS = {
    InstantFix: 540,    // 18s default (range: 15-22s)
    BeforeAfter: 660,   // 22s default (range: 18-26s)
    CompareThree: 750,  // 25s default (range: 22-28s)
    ProofCase: 600,     // 20s default (range: 17-24s)
  };

  return (
    <>
      {/* V2 Templates — variable duration per template type */}
      <Composition
        id="InstantFix"
        component={InstantFix}
        durationInFrames={DURATIONS.InstantFix}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || DURATIONS.InstantFix,
        })}
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
          durationInFrames: DURATIONS.InstantFix,
        }}
      />

      <Composition
        id="BeforeAfter"
        component={BeforeAfter}
        durationInFrames={DURATIONS.BeforeAfter}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || DURATIONS.BeforeAfter,
        })}
        defaultProps={{
          hook: "This turned 2 hours into 2 minutes",
          title: "PDF Compressor",
          description: "Compress PDFs without losing quality.",
          url: "tool.teamzlab.com/pdf/pdf-compressor/",
          audioFile: "",
          themeIndex: 1,
          beforeState: "Manual work, paid tools, privacy concerns",
          afterState: "One click, free, 100% private",
          durationInFrames: DURATIONS.BeforeAfter,
        }}
      />

      <Composition
        id="CompareThree"
        component={CompareThree}
        durationInFrames={DURATIONS.CompareThree}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || DURATIONS.CompareThree,
        })}
        defaultProps={{
          hook: "Which grammar tool is actually the best?",
          title: "Grammar Checker",
          url: "tool.teamzlab.com/ai/grammar-checker/",
          audioFile: "",
          themeIndex: 2,
          option1: { name: "Grammarly", price: "$12/mo", features: ["Cloud-based", "Tracks data"] },
          option2: { name: "ProWritingAid", price: "$20/mo", features: ["Desktop only", "Subscription"] },
          optionWinner: { name: "Teamz Lab", price: "FREE", features: ["Browser-based", "100% private"] },
          durationInFrames: DURATIONS.CompareThree,
        }}
      />

      <Composition
        id="ProofCase"
        component={ProofCase}
        durationInFrames={DURATIONS.ProofCase}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || DURATIONS.ProofCase,
        })}
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
          durationInFrames: DURATIONS.ProofCase,
        }}
      />

      {/* Tutorial — "How To" long-form videos (3-7 minutes) */}
      <Composition
        id="Tutorial"
        component={Tutorial}
        durationInFrames={5400}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || 5400,
        })}
        defaultProps={{
          hook: "How to create free invoices online",
          title: "Invoice Generator",
          problem: "Most invoice tools charge $10-20/month",
          steps: [
            { label: "Open the tool", description: "Visit the free invoice generator in your browser", screenshot: "" },
            { label: "Enter your details", description: "Fill in your business name, client info, and line items", screenshot: "" },
            { label: "Customize the look", description: "Pick a professional template and add your logo", screenshot: "" },
            { label: "Download your invoice", description: "Click generate — your invoice is ready in seconds", screenshot: "" },
          ],
          resultText: "Professional invoice — completely free, no signup",
          url: "tool.teamzlab.com/finance/invoice-generator/",
          audioFile: "",
          ctaText: "Try it free",
          ctaBadge: "LINK IN DESCRIPTION",
          brandName: "tool.teamzlab.com",
          themeIndex: 0,
          durationInFrames: 5400,
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
