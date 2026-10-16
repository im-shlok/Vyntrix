'use client';

import React, { useState, useEffect, useRef } from 'react';
import Image from 'next/image';

export default function Preloader() {
  const [progress, setProgress] = useState<number>(0);
  const [isVisible, setIsVisible] = useState<boolean>(true);
  const [isFading, setIsFading] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string>("Getting your farm ready...");
  
  // Matrix-style compilation log array for background scrolling (No Emojis!)
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const LOG_DATA = [
    "[BOOT] COMPILING: Agriva Core OS v2.1",
    "[CONN] Establishing socket telemetry link to sub-district...",
    "[ALLOC] IoT Telemetry Buffer: allocating 1024kb SRAM [OK]",
    "[DB] Connecting to local Qdrant Vector database...",
    "[DB] Qdrant DB: loading index kisaan_kb [OK]",
    "[RAG] Seeding 4 RAG knowledge bulletins (KVK + ICAR manuals)...",
    "[AI] Compiling LangGraph workflow graph: 12 agents initialized",
    "[VISION] loading YOLOv11 pathogen scanner weights...",
    "[VISION] parsing SAM2 segmented coordinates maps...",
    "[SYS] MCP Server: exposing tools: fetch_weather, locate_mandis",
    "[GEO] Geocoding: resolving Noida GPS coordinates [28.5355, 77.3910] [GEO_SYNC]",
    "[CLIMATE] Weather Agent: fetching satellite climate telemetry for Noida...",
    "[MARKET] Mandi Agent: fetching current commodity indices [OK]",
    "[MITIGATION] Disaster Node: calibrating flood level warning meters...",
    "[SYS] System status: 100% healthy, databases connected [OK]"
  ];

  useEffect(() => {
    // Speed-based progress bar
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        const increment = Math.floor(Math.random() * 8) + 5;
        const next = prev + increment;
        return next > 100 ? 100 : next;
      });
    }, 45);

    return () => clearInterval(interval);
  }, []);

  // Sync logs adding dynamically based on progress
  useEffect(() => {
    const logIndex = Math.floor((progress / 100) * LOG_DATA.length);
    const loadedLogs = LOG_DATA.slice(0, logIndex + 1);
    setConsoleLogs(loadedLogs);
    
    // Auto-scroll logs
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }

    if (progress < 25) {
       setStatusText("Getting your farm details ready...");
    } else if (progress < 50) {
       setStatusText("Checking your local weather...");
    } else if (progress < 75) {
       setStatusText("Preparing helpful crop advice...");
    } else if (progress < 95) {
       setStatusText("Loading market and soil information...");
    } else {
       setStatusText("Your farm assistant is ready.");
    }
  }, [progress]);

  useEffect(() => {
    if (progress === 100) {
      const fadeTimeout = setTimeout(() => {
        setIsFading(true);
      }, 350);

      const hideTimeout = setTimeout(() => {
        setIsVisible(false);
      }, 1050);

      return () => {
        clearTimeout(fadeTimeout);
        clearTimeout(hideTimeout);
      };
    }
  }, [progress]);

  useEffect(() => {
    if (isVisible) {
      document.body.style.overflow = 'hidden';
      document.body.style.height = '100vh';
    }
    return () => {
      document.body.style.overflow = '';
      document.body.style.height = '';
    };
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div 
      className={`preloader-shell fixed inset-0 w-screen h-screen flex items-center justify-center overflow-hidden z-[99999] transition-all duration-[750ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
        isFading 
          ? 'opacity-0 scale-95 pointer-events-none' 
          : 'opacity-100 scale-100'
      }`}
    >
      {/* Background Matrix/Telemetry logs stream */}
      <div 
        ref={logContainerRef}
        className="absolute inset-0 p-6 font-mono text-[9px] text-emerald-200/[0.08] leading-relaxed overflow-hidden select-none pointer-events-none z-0 flex flex-col justify-end text-left"
      >
        {consoleLogs.map((log, i) => (
          <div key={i} className="truncate">
            {log}
          </div>
        ))}
      </div>

      {/* Cyber Grid background layout */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(110,231,183,0.025)_1px,transparent_1px),linear-gradient(to_bottom,rgba(110,231,183,0.025)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none z-0" />

      {/* Ambient background glows */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-cyan-400/8 rounded-full blur-[120px] pointer-events-none z-0" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[250px] h-[250px] bg-amber-300/6 rounded-full blur-[90px] pointer-events-none z-0" />

      {/* Centered Glass Capsule Card */}
       <div className="preloader-card glass-panel p-8 border rounded-3xl w-full max-w-[460px] flex flex-col gap-6 relative z-10 backdrop-blur-3xl mx-4 select-none">
        
        {/* Animated tracing border corner glows */}
         <div className="absolute inset-0 rounded-3xl pointer-events-none border border-cyan-200/20 opacity-70" />

        <div className="flex items-center gap-6">
          {/* Left Side: Orbit Indicator containing logo */}
          <div className="relative w-18 h-18 shrink-0 flex items-center justify-center">
            
            {/* Spinning Neon Gradient Dashboard ring */}
            <svg className="absolute inset-0 w-full h-full animate-spin" style={{ animationDuration: '2.5s' }} viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
              <circle 
                cx="40" 
                cy="40" 
                r="36" 
                fill="none" 
                stroke="url(#preloader-spinner-gradient)" 
                strokeWidth="2.5" 
                strokeDasharray="100 25" 
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="preloader-spinner-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#d946ef" />
                  <stop offset="50%" stopColor="#06b6d4" />
                  <stop offset="100%" stopColor="#10b981" />
                </linearGradient>
              </defs>
            </svg>

            {/* Central Agriva logo in active orbital ring */}
            <div className="w-11 h-11 rounded-full bg-[#020402] border border-white/10 flex items-center justify-center shadow-[inset_0_0_12px_rgba(16,185,129,0.15)] z-10 relative">
              <Image
                src="/logo.png"
                alt="Agriva logo"
                width={36}
                height={36}
                className="h-9 w-9 rounded-full object-cover"
              />
            </div>
          </div>

          {/* Right Side: Text branding details */}
          <div className="flex-1 text-left space-y-1">
             <span className="text-[10px] font-bold text-cyan-100 border border-cyan-200/30 bg-cyan-950/45 px-2.5 py-1 rounded-full w-max block tracking-wide">
               YOUR FARM ASSISTANT
            </span>
             <h2 className="text-xl font-black text-white leading-none tracking-tight flex items-center gap-1.5 font-sans">
              Agriva
            </h2>
             <p className="text-xs text-emerald-100/85 font-semibold font-sans italic">
              "खेती होगी स्मार्ट, भविष्य होगा मजबूत।"
            </p>
          </div>
        </div>

        {/* Dynamic Tagline Logger and Thin Progress Bar */}
         <div className="space-y-3.5 pt-4 border-t border-cyan-100/15 font-mono text-[9px]">
           <div className="flex justify-between items-center text-emerald-100 font-bold">
             <span className="flex items-center gap-1.5 text-left truncate max-w-[270px]">
               <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_10px_rgba(253,224,71,0.8)] animate-pulse"></span>
               <span className="text-emerald-100">{statusText}</span>
             </span>
             <span className="text-cyan-200 font-black shrink-0">{progress}%</span>
          </div>

          {/* Sleek, neon gradient loading bar */}
           <div className="w-full h-1.5 bg-slate-950/80 rounded-full overflow-hidden border border-cyan-100/15 p-[0.5px]">
             <div
               className="h-full bg-gradient-to-r from-amber-300 via-cyan-300 to-emerald-300 rounded-full transition-all duration-100 ease-out shadow-[0_0_14px_rgba(45,212,191,0.8)]"
              style={{ width: `${progress}%` }}
            />
          </div>

           <div className="flex justify-between text-[7.5px] text-emerald-100/55 font-semibold select-none pt-0.5">
             <span>Preparing your farm dashboard</span>
             <span className="text-emerald-200/80 font-black animate-pulse">SAFE &amp; READY</span>
          </div>
        </div>

      </div>

    </div>
  );
}
