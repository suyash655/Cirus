"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RiskChart({ data }: { data?: any[] }) {
  const chartData = data && data.length > 0 ? data : [
    { name: "Mon", incidents: 12, guardrails: 5 },
    { name: "Tue", incidents: 9, guardrails: 6 },
    { name: "Wed", incidents: 15, guardrails: 8 },
    { name: "Thu", incidents: 10, guardrails: 7 },
    { name: "Fri", incidents: 8, guardrails: 9 },
    { name: "Sat", incidents: 6, guardrails: 4 },
    { name: "Sun", incidents: 4, guardrails: 2 },
  ];

  return (
    <Card className="rounded-md border border-zinc-200 bg-white shadow-sm">
      <CardHeader className="px-4 pt-4">
        <CardTitle className="text-zinc-900">Incidents vs Guardrails Shipped</CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="incidents" stroke="#111827" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="guardrails" stroke="#0ea5e9" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
