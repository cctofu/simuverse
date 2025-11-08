import { useEffect, useState } from "react";

const frames = [
  "/banana_stage1.png",
  "/banana_stage2.png",
  "/banana_stage3.png",
];

type Props = {
  width?: number;
  height?: number;
  speed?: number;
};

export default function BananaDropImageLoop({
  width = 400,
  height = 300,
  speed = 650,
}: Props) {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % frames.length);
    }, speed);
    return () => clearInterval(timer);
  }, [speed]);

  return (
    <div
      style={{
        width,
        height,
        position: "relative",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-end",
        overflow: "hidden",
        margin: "0 auto",
      }}
    >
      <img
        src={frames[frameIndex]}
        alt="banana"
        style={{
            height: "450px",
            width: "auto",
            objectFit: "contain",
            position: "absolute",
            bottom: 0,
             transform:
      frameIndex === 0
            ? "translateX(-1.5px)"       // stage 1 → move left
            : frameIndex === 2
            ? "translateX(0.3px)"        // stage 3 → move right
            : "translateX(0)", 
        }}
       />


    </div>
  );
}
