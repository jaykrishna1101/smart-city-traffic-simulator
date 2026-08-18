"use client";

import { useEffect, useState, useRef } from "react";
import { Map, Cpu, Radio, Activity, SlidersHorizontal, Siren, LayoutDashboard, ArrowRight } from "lucide-react";

const pipeline = [
  { name: "OpenStreetMap", description: "Real road network data for Nagpur", icon: Map },
  { name: "SUMO", description: "Microscopic traffic simulation engine", icon: Cpu },
  { name: "TraCI", description: "Live control interface into the simulation", icon: Radio },
  { name: "Traffic State", description: "Queue length and speed per approach", icon: Activity },
  { name: "Adaptive Controller", description: "Recalculates signal timing per cycle", icon: SlidersHorizontal },
  { name: "Emergency Priority", description: "Preempts signals for priority vehicles", icon: Siren },
  { name: "Live Dashboard", description: "Streams state to the web interface", icon: LayoutDashboard },
];

export function IntegrationsSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const sectionRef = useRef<HTMLElement>(null);

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
    <section id="architecture" ref={sectionRef} className="relative overflow-hidden py-32 lg:py-40">
      {/* Header — centered */}
      <div className="relative z-10 text-center">
        <span className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-8 transition-all duration-700 justify-center ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}>
          <span className="w-12 h-px bg-foreground/20" />
          System Architecture
          <span className="w-12 h-px bg-foreground/20" />
        </span>

        <h2 className={`text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9] transition-all duration-1000 ${
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}>
          One pipeline,
          <br />
          <span className="text-muted-foreground">start to signal.</span>
        </h2>

        <p className={`mt-8 text-xl text-muted-foreground leading-relaxed max-w-lg mx-auto transition-all duration-1000 delay-100 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}>
          Real map data flows through a live simulation and a control layer, out to the signals and onto the dashboard — every stage running continuously.
        </p>
      </div>

      {/* Pipeline grid */}
      <div className="relative z-10 mt-24 max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-16">
          {pipeline.map((stage, index) => (
            <div key={stage.name} className="relative flex items-center">
              <div
                className={`group relative overflow-hidden p-6 border transition-all duration-500 cursor-default flex-1 ${
                  hoveredIndex === index
                    ? "border-foreground bg-foreground/[0.04]"
                    : "border-foreground/10 hover:border-foreground/30"
                } ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
                style={{ transitionDelay: `${index * 60 + 200}ms` }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <span className="text-[10px] font-mono text-muted-foreground">{`0${index + 1}`}</span>
                <div className={`w-10 h-10 mt-4 mb-6 flex items-center justify-center transition-colors ${
                  hoveredIndex === index ? "text-foreground" : "text-foreground/60"
                }`}>
                  <stage.icon className="w-6 h-6" />
                </div>
                <span className="font-medium block mb-1">{stage.name}</span>
                <span className="text-xs text-muted-foreground leading-relaxed">{stage.description}</span>
              </div>

              {/* Connector arrow */}
              {index < pipeline.length - 1 && (
                <div className="hidden lg:flex items-center justify-center w-4 shrink-0">
                  <ArrowRight className="w-4 h-4 text-foreground/20" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Bottom stats row */}
        <div className={`flex flex-wrap items-center gap-12 pt-12 border-t border-foreground/10 transition-all duration-1000 delay-500 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}>
          {[
            { value: "7", label: "Pipeline stages" },
            { value: "Real OSM", label: "Map data source" },
            { value: "Live", label: "TraCI connection" },
          ].map((stat) => (
            <div key={stat.label} className="flex items-baseline gap-3">
              <span className="text-3xl font-display">{stat.value}</span>
              <span className="text-sm text-muted-foreground">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
