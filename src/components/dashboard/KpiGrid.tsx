"use client";

import { Activity, Shield, TrendingDown, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useState } from 'react';

export function KpiGrid({ kpis: initialKpis }: { kpis?: any[] }) {
  const defaultKpis = [
    {
      title: "Total Incidents",
      value: "142",
      icon: Activity,
    },
    {
      title: "Active Guardrails",
      value: "48",
      icon: Shield,
    },
    {
      title: "Risk Reduction",
      value: "34%",
      icon: TrendingDown,
    },
    {
      title: "Avg. Resolution Time",
      value: "45m",
      icon: Clock,
    },
  ];
  
  const kpis = initialKpis || defaultKpis;

  const [animatedValues, setAnimatedValues] = useState<string[]>([] as string[]);

  useEffect(() => {
    // animate count up once
    const targets = kpis.map((k) => k.value);
    setAnimatedValues(targets.map(() => '0'));
    const durations = 600;
    kpis.forEach((k, i) => {
      const start = Date.now();
      const from = 0;
      const to = Number(String(k.value).replace(/[^0-9\.]/g, '')) || 0;
      const timer = setInterval(() => {
        const t = Math.min(1, (Date.now() - start) / durations);
        const v = Math.round(from + (to - from) * t);
        setAnimatedValues((prev) => {
          const next = [...prev];
          next[i] = String(v) + (String(k.value).includes('%') ? '%' : '');
          return next;
        });
        if (t === 1) clearInterval(timer);
      }, 16);
    });
  }, [kpis]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      {kpis.map((kpi, index) => {
        // Support either a React component (imported icon) or a string key.
        // Ensure final `Icon` is a callable component; fall back to `Activity`.
        const ICONS: Record<string, any> = {
          Activity,
          Shield,
          TrendingDown,
          Clock,
        };

        let Icon: any = kpi.icon;
        if (typeof Icon === 'string') {
          Icon = ICONS[Icon] ?? Activity;
        }
        if (!Icon || (typeof Icon !== 'function' && typeof Icon !== 'object')) {
          Icon = Activity;
        }
        return (
          <Card 
            key={index} 
            className="bg-white border border-zinc-200 shadow-sm hover:shadow-md transition-shadow duration-150 rounded-md"
          >
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0 px-4 pt-4">
              <CardTitle className="text-zinc-700 text-sm font-medium">
                {kpi.title}
              </CardTitle>
              <Icon className="h-4 w-4 text-sky-600" />
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="text-3xl font-bold text-zinc-900">{animatedValues[index] ?? kpi.value}</div>
              {kpi.subtitle && <div className="text-xs text-zinc-500 mt-1">{kpi.subtitle}</div>}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
