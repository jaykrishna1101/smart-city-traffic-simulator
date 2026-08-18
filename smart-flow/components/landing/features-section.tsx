"use client";

import { useEffect, useRef, useState } from "react";

const feature = {
  number: "01",
  title: "Adaptive Signal Control",
  description:
    "Fixed-time signals split green time evenly, no matter how empty or full each approach is. SmartFlow measures queue length on every arm of the intersection in real time and reallocates green time to the direction that needs it most.",
  stats: { value: "MORE TRAFFIC", label: "= more green time" },
};

const approaches = [
  { direction: "North", vehicles: 42 },
  { direction: "South", vehicles: 31 },
  { direction: "East", vehicles: 18 },
  { direction: "West", vehicles: 9 },
];

const maxVehicles = Math.max(...approaches.map((a) => a.vehicles));

// Intersection diagram: 4 approach arms with vehicle counts and proportional green-time bars.
// Laid out on a 3x3 grid so each arm has its own cell and can never overlap another,
// regardless of the container's width.
function IntersectionDiagram({ active }: { active: boolean }) {
  const [north, south, east, west] = approaches;

  return (
    <div className="w-full h-full min-h-[420px] p-6 lg:p-8">
      <div className="grid grid-cols-[1fr_auto_1fr] grid-rows-[1fr_auto_1fr] w-full h-full min-h-[370px] gap-2">
        {/* Row 1 */}
        <div />
        <div className="flex flex-col items-center gap-2 justify-end pb-2">
          <span className="font-mono text-[10px] text-muted-foreground">NORTH</span>
          <span className="text-xl lg:text-2xl font-display tabular-nums leading-none">{north.vehicles}</span>
          <div className="w-1.5 h-14 bg-foreground/10 overflow-hidden flex flex-col-reverse">
            <div
              className="w-full bg-[#3b82f6] transition-all duration-1000 ease-out"
              style={{ height: active ? `${(north.vehicles / maxVehicles) * 100}%` : "0%" }}
            />
          </div>
        </div>
        <div />

        {/* Row 2 */}
        <div className="flex items-center justify-end gap-2 pr-2">
          <div className="flex flex-col items-center gap-1">
            <span className="font-mono text-[10px] text-muted-foreground">WEST</span>
            <span className="text-xl lg:text-2xl font-display tabular-nums leading-none">{west.vehicles}</span>
          </div>
          <div className="h-1.5 w-10 lg:w-14 bg-foreground/10 overflow-hidden flex flex-row-reverse">
            <div
              className="h-full bg-[#3b82f6] transition-all duration-1000 ease-out delay-300"
              style={{ width: active ? `${(west.vehicles / maxVehicles) * 100}%` : "0%" }}
            />
          </div>
        </div>
        <div className="flex items-center justify-center">
          <div className="w-16 h-16 bg-background border border-foreground/15" />
        </div>
        <div className="flex items-center justify-start gap-2 pl-2">
          <div className="h-1.5 w-10 lg:w-14 bg-foreground/10 overflow-hidden flex">
            <div
              className="h-full bg-[#3b82f6] transition-all duration-1000 ease-out delay-200"
              style={{ width: active ? `${(east.vehicles / maxVehicles) * 100}%` : "0%" }}
            />
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="font-mono text-[10px] text-muted-foreground">EAST</span>
            <span className="text-xl lg:text-2xl font-display tabular-nums leading-none">{east.vehicles}</span>
          </div>
        </div>

        {/* Row 3 */}
        <div />
        <div className="flex flex-col-reverse items-center gap-2 justify-start pt-2">
          <span className="font-mono text-[10px] text-muted-foreground">SOUTH</span>
          <span className="text-xl lg:text-2xl font-display tabular-nums leading-none">{south.vehicles}</span>
          <div className="w-1.5 h-14 bg-foreground/10 overflow-hidden flex flex-col">
            <div
              className="w-full bg-[#3b82f6] transition-all duration-1000 ease-out delay-100"
              style={{ height: active ? `${(south.vehicles / maxVehicles) * 100}%` : "0%" }}
            />
          </div>
        </div>
        <div />
      </div>
    </div>
  );
}

export function FeaturesSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="adaptive-control"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header - Full width with diagonal layout */}
        <div className="relative mb-24 lg:mb-32">
          <div className="grid lg:grid-cols-12 gap-8 items-end">
            <div className="lg:col-span-7">
              <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
                <span className="w-12 h-px bg-foreground/30" />
                Adaptive Control
              </span>
              <h2
                className={`text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9] transition-all duration-1000 ${
                  isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                }`}
              >
                Signals that
                <br />
                <span className="text-muted-foreground">think ahead.</span>
              </h2>
            </div>
            <div className="lg:col-span-5 lg:pb-4">
              <p className={`text-xl text-muted-foreground leading-relaxed transition-all duration-1000 delay-200 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}>
                No fixed timers. Every intersection reallocates green time to wherever the traffic actually is.
              </p>
            </div>
          </div>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid lg:grid-cols-12 gap-4 lg:gap-6">
          {/* Large feature card */}
          <div 
            className={`lg:col-span-12 relative bg-black border border-foreground/10 min-h-[500px] overflow-hidden group transition-all duration-700 flex flex-col lg:flex-row ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
            }`}
          >
            {/* Left: text content */}
            <div className="relative flex-1 p-8 lg:p-12 bg-black">
              <div className="relative z-10">
                <span className="font-mono text-sm text-muted-foreground">{feature.number}</span>
                <h3 className="text-3xl lg:text-4xl font-display mt-4 mb-6 group-hover:translate-x-2 transition-transform duration-500">
                  {feature.title}
                </h3>
                <p className="text-lg text-muted-foreground leading-relaxed max-w-md mb-8">
                  {feature.description}
                </p>
                <div>
                  <span className="text-3xl lg:text-4xl font-display">{feature.stats.value}</span>
                  <span className="block text-sm text-muted-foreground font-mono mt-2">{feature.stats.label}</span>
                </div>
              </div>
            </div>

            {/* Right: intersection diagram, full height */}
            <div className="relative lg:w-[46%] shrink-0 overflow-hidden border-t lg:border-t-0 lg:border-l border-foreground/10">
              <IntersectionDiagram active={isVisible} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
