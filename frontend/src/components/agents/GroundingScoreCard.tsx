'use client';

import React from 'react';
import { Shield, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import type { GroundingInfo } from '@/lib/types';

interface GroundingScoreCardProps {
  grounding: GroundingInfo;
}

export default function GroundingScoreCard({ grounding }: GroundingScoreCardProps) {
  const pct = Math.round(grounding.overall_confidence * 100);
  const isGrounded = grounding.is_grounded;

  return (
    <div className={`rounded-lg border p-4 ${isGrounded ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          {isGrounded ? (
            <ShieldCheck className="w-4 h-4 text-green-600" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-red-600" />
          )}
          Grounding Validation
        </h4>
        <span className={`text-lg font-bold ${isGrounded ? 'text-green-700' : 'text-red-700'}`}>
          {pct}%
        </span>
      </div>

      {/* Section scores */}
      {grounding.section_scores && Object.keys(grounding.section_scores).length > 0 && (
        <div className="space-y-1 mb-3">
          {Object.entries(grounding.section_scores).map(([section, score]) => (
            <div key={section} className="flex items-center justify-between text-xs">
              <span className="text-gray-600 capitalize">{section}</span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${score >= 0.85 ? 'bg-green-500' : score >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${score * 100}%` }}
                  />
                </div>
                <span className="text-gray-700 w-8 text-right">{Math.round(score * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Hallucinated claims */}
      {grounding.hallucinated_claims.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-red-700 mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Hallucinated Claims
          </p>
          <ul className="text-xs text-red-600 space-y-0.5">
            {grounding.hallucinated_claims.map((claim, i) => (
              <li key={i} className="pl-3 border-l-2 border-red-300">{claim}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Issues */}
      {grounding.issues.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-yellow-700 mb-1">Issues</p>
          <ul className="text-xs text-yellow-600 space-y-0.5">
            {grounding.issues.map((issue, i) => (
              <li key={i} className="pl-3 border-l-2 border-yellow-300">{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
