import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const generateId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).substring(2, 11);

export const formatRelativeTime = (dateStr: string) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 0) return 'just now'; // clock skew guard
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

export const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    return false;
  }
};

export const downloadFile = (content: string, filename: string, type: string = "text/plain") => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const ARTIFACT_META: Record<string, { label: string; icon: string; color: string; emoji: string; shortLabel: string; fileExt: string }> = {
  iac: { label: 'Terraform Patch', icon: 'FileCode2', color: 'emerald', emoji: '🏗️', shortLabel: 'TF', fileExt: '.tf' },
  policy: { label: 'OPA Policy', icon: 'ShieldCheck', color: 'cyan', emoji: '📜', shortLabel: 'Rego', fileExt: '.rego' },
  runbook: { label: 'Automated Runbook', icon: 'BookOpen', color: 'violet', emoji: '📘', shortLabel: 'Runbook', fileExt: '.md' },
  rca: { label: 'Root Cause Analysis', icon: 'Search', color: 'amber', emoji: '🔍', shortLabel: 'RCA', fileExt: '.md' }
};

export const detectFormat = (text: string) => {
  if (text.startsWith('{') || text.startsWith('[')) return 'json';
  if (text.includes('---')) return 'yaml';
  return 'plain';
};

export const severityBg = (sev: string) => {
  const s = sev.toUpperCase();
  if (s === 'CRITICAL' || s === 'P1') return 'bg-rose-500/10 text-rose-500 border-rose-500/20';
  if (s === 'HIGH' || s === 'P2') return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
  if (s === 'MEDIUM' || s === 'P3') return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
  return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20';
};

export const statusColor = (status: string) => {
  if (status === 'completed' || status === 'ready') return 'text-emerald-500';
  if (status === 'processing' || status === 'running') return 'text-cyan-500';
  return 'text-zinc-500';
};

export const statusLabel = (status: string) => {
  return status.charAt(0).toUpperCase() + status.slice(1);
};

