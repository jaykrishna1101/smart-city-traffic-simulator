"use client";

import { useEffect, useState, useRef } from "react";
import { Siren, Route, Radio, ShieldCheck, CheckCircle2, RotateCcw } from "lucide-react";

const securityFeatures = [
  {
    icon: Siren,
    title: "Vehicle detected",
    description: "An emergency vehicle transponder is picked up approaching the network.",
  },
  {
    icon: Route,
    title: "Route identified",
    description: "The vehicle's path through the network is projected in real time.",
  },
  {
    icon: Radio,
    title: "Priority intersection selected",
    description: "Every signal along the projected route is flagged for preemption.",
  },
  {
    icon: ShieldCheck,
    title: "Signal priority activated",
    description: "Green phases shift to clear the corridor ahead of the vehicle.",
  },
  {
    icon: CheckCircle2,
    title: "Vehicle passes",
    description: "The emergency vehicle clears the intersection without stopping.",
  },
  {
    icon: RotateCcw,
    title: "Normal operation restored",
    description: "Adaptive control resumes standard signal timing immediately after.",
  },
];

const tags = ["SUMO", "TraCI", "Priority Routing", "Real-time"];

export function SecuritySection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);
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

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveFeature((prev) => (prev + 1) % securityFeatures.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="emergency-priority" ref={sectionRef} className="relative py-32 lg:py-40 overflow-hidden">
      {/* Background accent removed */}
      
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-20">
          <span className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-8 transition-all duration-700 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}>
            <span className="w-12 h-px bg-foreground/20" />
            Emergency Priority
          </span>
          
          {/* Title — full width */}
          <h2 className={`text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9] mb-12 transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}>
            Clears a path,
            <br />
            <span className="text-muted-foreground">automatically.</span>
          </h2>
          
          {/* Description — below title */}
          <div className={`transition-all duration-1000 delay-100 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}>
            <p className="text-xl text-muted-foreground leading-relaxed max-w-2xl">
              Ambulances and fire trucks trigger signal preemption the moment they're detected — every light ahead of them turns green, in sequence.
            </p>
          </div>
        </div>

        {/* Main content */}
        <div className="grid lg:grid-cols-12 gap-6">
          {/* Large visual card */}
          <div className={`lg:col-span-7 relative p-8 lg:p-12 border border-foreground/10 min-h-[400px] overflow-hidden flex flex-col justify-between transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}>
            {/* Live step indicator — desktop only */}
            <div className="absolute inset-0 pointer-events-none items-center justify-end pr-12 hidden lg:flex">
              {securityFeatures.map((feature, index) => (
                <feature.icon
                  key={feature.title}
                  className="absolute w-48 h-48 text-foreground transition-opacity duration-500"
                  style={{ opacity: activeFeature === index ? 0.08 : 0 }}
                />
              ))}
            </div>
            
            <div className="relative z-10">
              <span className="font-mono text-sm text-muted-foreground">Step {activeFeature + 1} of {securityFeatures.length}</span>
              <div className="mt-8">
                <span className="text-7xl lg:text-8xl font-display">{"<3s"}</span>
                <span className="block text-muted-foreground mt-2">Signal preemption response time</span>
              </div>
            </div>
            
            {/* Tags */}
            <div className="relative z-10 flex flex-wrap gap-2 mt-8">
              {tags.map((tag, index) => (
                <span
                  key={tag}
                  className={`px-3 py-1 border border-foreground/10 text-xs font-mono text-muted-foreground transition-all duration-500 ${
                    isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                  }`}
                  style={{ transitionDelay: `${index * 100 + 300}ms` }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* Feature cards stack */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            {securityFeatures.map((feature, index) => (
              <div
                key={feature.title}
                className={`p-6 border transition-all duration-500 cursor-default ${
                  activeFeature === index 
                    ? "border-foreground/30 bg-foreground/[0.04]" 
                    : "border-foreground/10"
                } ${isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"}`}
                style={{ transitionDelay: `${index * 80}ms` }}
                onClick={() => setActiveFeature(index)}
                onMouseEnter={() => setActiveFeature(index)}
              >
                <div className="flex items-start gap-4">
                  <div className={`shrink-0 w-10 h-10 flex items-center justify-center border transition-colors ${
                    activeFeature === index 
                      ? "border-foreground bg-foreground text-background" 
                      : "border-foreground/40 bg-foreground/5 text-foreground/70"
                  }`}>
                    <feature.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium mb-1">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
