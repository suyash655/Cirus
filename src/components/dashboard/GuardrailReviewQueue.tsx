'use client';

import { useState } from 'react';
import type { Incident } from '@/lib/types';
import { QueueRow } from './QueueRow';

export function GuardrailReviewQueue({ incidents }: { incidents: Incident[] }) {
  const [visible, setVisible] = useState(incidents);

  return (
    <section id="guardrail-review-queue" className="mt-8">
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2
            className="text-[16px] font-medium"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Guardrail review queue
          </h2>
          <p
            className="text-[13px] mt-1"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Review generated controls before they enter your codebase.
          </p>
        </div>
        <span
          className="text-[13px]"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {visible.length} awaiting approval
        </span>
      </div>

      <div className="space-y-3">
        {visible.map((incident) => (
          <QueueRow
            key={incident.id}
            incident={incident}
            onApprove={() =>
              setVisible((current) => current.filter((item) => item.id !== incident.id))
            }
          />
        ))}
      </div>

      {visible.length === 0 && (
        <div
          className="rounded-[12px] p-8 text-center text-[13px]"
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-muted)',
          }}
        >
          No guardrails are awaiting approval.
        </div>
      )}
    </section>
  );
}
