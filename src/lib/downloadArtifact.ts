import JSZip from 'jszip';
import type { Artifact, ArtifactType } from './types';

export function artifactText(artifact: Artifact): string {
  if (artifact.type === 'rca') {
    return [
      `# Root Cause Analysis`,
      artifact.executiveSummary,
      `## Root Cause`,
      artifact.rootCause,
      `## Contributing Factors`,
      artifact.contributingFactors?.map((factor) => `- ${factor}`).join('\n') ?? '',
      `## Lessons Learned`,
      artifact.lessonsLearned?.map((lesson) => `- ${lesson}`).join('\n') ?? '',
    ].filter(Boolean).join('\n\n');
  }
  if (artifact.type === 'policy') return artifact.code;
  if (artifact.type === 'iac') return typeof artifact.fullPatch === 'string' ? artifact.fullPatch : JSON.stringify(artifact.fullPatch, null, 2);
  if (artifact.type === 'runbook') return artifact.steps.map((step) => `${step.id}. ${step.title}\n${step.description}${step.command ? `\n${step.command}` : ''}`).join('\n\n');
  if (artifact.type === 'alerts') return artifact.rules.map((rule) => `${rule.name}: ${rule.expression}\nfor: ${rule.duration}`).join('\n\n');
  if (artifact.type === 'regression') return artifact.testCases.map((test) => `${test.name}\n${test.description}\n\n${test.code}\n\nExpected: ${test.expectedResult}`).join('\n\n---\n\n');
  return JSON.stringify(artifact, null, 2);
}

export function downloadArtifact(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  // Must be in DOM for Firefox/Safari to trigger the download
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export async function downloadAllArtifacts(entries: Array<[ArtifactType, Artifact]>) {
  const zip = new JSZip();
  const extension: Record<string, string> = { policy: 'rego', iac: 'tf', alerts: 'yaml', runbook: 'md', rca: 'md', regression: 'txt' };
  entries.forEach(([type, artifact]) => zip.file(`${type}.${extension[type]}`, artifactText(artifact)));
  const blob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'cirus-guardrails.zip';
  // Must be in DOM for Firefox/Safari to trigger the download
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
