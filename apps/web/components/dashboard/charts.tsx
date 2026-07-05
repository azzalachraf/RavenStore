"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const salesData = [
  { day: "Mon", sales: 420, profit: 170 },
  { day: "Tue", sales: 620, profit: 260 },
  { day: "Wed", sales: 520, profit: 210 },
  { day: "Thu", sales: 880, profit: 410 },
  { day: "Fri", sales: 760, profit: 340 },
  { day: "Sat", sales: 980, profit: 510 },
  { day: "Sun", sales: 830, profit: 420 }
];

export function RevenueChart() {
  return (
    <Card className="min-h-[320px]">
      <CardHeader>
        <CardTitle>Revenue Flow</CardTitle>
      </CardHeader>
      <CardContent className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={salesData}>
            <defs>
              <linearGradient id="sales" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="day" stroke="rgba(255,255,255,0.45)" />
            <YAxis stroke="rgba(255,255,255,0.45)" />
            <Tooltip contentStyle={{ background: "#10131c", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            <Area type="monotone" dataKey="sales" stroke="#a78bfa" fill="url(#sales)" strokeWidth={2} />
            <Area type="monotone" dataKey="profit" stroke="#22d3ee" fill="transparent" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function PaymentChart({ stats }: { stats: Record<string, number> }) {
  const data = Object.entries(stats).map(([status, count]) => ({ status, count }));
  return (
    <Card className="min-h-[320px]">
      <CardHeader>
        <CardTitle>Payment Statistics</CardTitle>
      </CardHeader>
      <CardContent className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.length ? data : [{ status: "none", count: 0 }]}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="status" stroke="rgba(255,255,255,0.45)" />
            <YAxis stroke="rgba(255,255,255,0.45)" />
            <Tooltip contentStyle={{ background: "#10131c", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

