'use client';

import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

export function MTTGGauge({ hours, maxHours = 72 }: { hours: number; maxHours?: number }) {
  return (
    <div className="relative w-[120px] h-[78px] mx-auto -mt-3">
      <RadialBarChart
        width={120}
        height={120}
        cx={60}
        cy={70}
        innerRadius={44}
        outerRadius={58}
        startAngle={180}
        endAngle={0}
        data={[{ value: hours }]}
      >
        <PolarAngleAxis
          type="number"
          domain={[0, maxHours]}
          angleAxisId={0}
          tick={false}
        />
        <RadialBar
          background={{ fill: 'var(--color-border)' }}
          dataKey="value"
          cornerRadius={6}
          fill="var(--color-accent)"
          isAnimationActive
          animationDuration={800}
          animationEasing="ease-out"
        />
      </RadialBarChart>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <span
          className="text-2xl font-medium tabular-nums"
          style={{ color: 'var(--color-text-primary)' }}
        >
          {hours}h
        </span>
      </div>
    </div>
  );
}
