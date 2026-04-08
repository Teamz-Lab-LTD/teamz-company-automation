import React from "react";
import { Composition } from "remotion";
import { ToolReel } from "./ToolReel";

export const RemotionRoot = () => {
  const FPS = 30;
  const SLIDE_DURATION = 3.5; // seconds per slide
  const TOTAL_FRAMES = Math.round(FPS * SLIDE_DURATION * 4); // 4 slides

  return (
    <>
      <Composition
        id="ToolReel"
        component={ToolReel}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          hook: "Stop paying for this",
          title: "Grammar Checker",
          description:
            "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
          url: "tool.teamzlab.com/ai/grammar-checker/",
          audioFile: "", // e.g. "audio/beat1.mp3" — place files in public/audio/
        }}
      />
    </>
  );
};
