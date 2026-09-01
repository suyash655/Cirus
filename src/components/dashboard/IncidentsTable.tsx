"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";

export function IncidentsTable({ incidents }: { incidents: any[] }) {
  const router = useRouter();

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
      case "P1":
        return <Badge className="bg-white border border-zinc-200 text-rose-600">{severity}</Badge>;
      case "HIGH":
      case "P2":
        return <Badge className="bg-white border border-zinc-200 text-amber-600">{severity}</Badge>;
      case "MEDIUM":
      case "P3":
        return <Badge className="bg-white border border-zinc-200 text-sky-600">{severity}</Badge>;
      default:
        return <Badge className="bg-white border border-zinc-200 text-zinc-700">{severity}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "ready":
      case "completed":
        return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">{status}</Badge>;
      case "processing":
      case "running":
        return <Badge className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20">{status}</Badge>;
      default:
        return <Badge className="bg-zinc-500/10 text-zinc-400 border-zinc-500/20">{status}</Badge>;
    }
  };

  return (
    <Card className="bg-white rounded-md border border-zinc-200 shadow-sm">
      <CardHeader className="px-4 pt-4">
        <CardTitle className="text-zinc-900">Recent Incidents</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-zinc-100">
              <TableHead className="text-zinc-600">Title</TableHead>
              <TableHead className="text-zinc-600">Provider</TableHead>
              <TableHead className="text-zinc-600">Severity</TableHead>
              <TableHead className="text-zinc-600">Root Cause</TableHead>
              <TableHead className="text-zinc-600 text-right">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {incidents.map((incident) => (
              <TableRow 
                key={incident.id}
                className="hover:bg-zinc-50 transition-colors cursor-pointer border-b border-zinc-100"
                onClick={() => router.push(`/incidents/${incident.id}`)}
              >
                <TableCell className="font-medium text-zinc-900">{incident.title}</TableCell>
                <TableCell>
                  <Badge className="bg-white border border-zinc-200 text-zinc-700">
                    {incident.provider}
                  </Badge>
                </TableCell>
                <TableCell>{getSeverityBadge(incident.severity)}</TableCell>
                <TableCell className="text-zinc-700">{incident.rootCause || '-'}</TableCell>
                <TableCell className="text-right">
                  {getStatusBadge(incident.status)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
