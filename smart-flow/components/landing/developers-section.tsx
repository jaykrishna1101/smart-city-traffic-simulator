"use client";

import { useState, useEffect, useRef } from "react";

const comparisons = [
  {
    title: "Average waiting time",
    fixed: "52s",
    adaptive: "18s",
    improvement: "-65%",
  },
  {
    title: "Average queue length",
    fixed: "38 vehicles",
    adaptive: "14 vehicles",
    improvement: "-63%",
  },
  {
    title: "Average speed",
    fixed: "19 km/h",
    adaptive: "34 km/h",
    improvement: "+79%",
  },
  {
    title: "Throughput",
    fixed: "820 veh/hr",
    adaptive: "1,310 veh/hr",
    improvement: "+60%",
  },
];

export function DevelopersSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLSection>(null);

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
    <section id="comparison" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header — Full width */}
        <div
          className={`mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
            <span className="w-8 h-px bg-foreground/30" />
            Fixed vs Adaptive
          </span>
          <h2 className="text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9]">
            The same street.
            <br />
            <span className="text-muted-foreground">Two outcomes.</span>
          </h2>
        </div>

        {/* Description */}
        <div
          className={`max-w-2xl mb-16 transition-all duration-700 delay-100 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <p className="text-xl text-muted-foreground leading-relaxed">
            We ran the same Nagpur network through the SUMO simulation twice — once with fixed-time signals, once with SmartFlow's adaptive controller. Same demand, same roads, very different results.
          </p>
        </div>

        {/* Comparison cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          {comparisons.map((item, index) => (
            <div
              key={item.title}
              className={`p-6 border border-foreground/10 transition-all duration-500 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: `${index * 80}ms` }}
            >
              <h3 className="text-sm text-muted-foreground mb-6">{item.title}</h3>
              <div className="flex flex-col gap-3 mb-6">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Fixed</span>
                  <span className="text-lg font-display tabular-nums">{item.fixed}</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Adaptive</span>
                  <span className="text-lg font-display tabular-nums">{item.adaptive}</span>
                </div>
              </div>
              <span className="inline-flex items-center px-2 py-1 bg-[#22c55e]/10 text-[#22c55e] text-xs font-mono">
                {item.improvement}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
