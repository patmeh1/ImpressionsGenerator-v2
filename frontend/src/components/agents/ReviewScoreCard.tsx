'use client';

import React from 'react';
import { Star, AlertCircle, Lightbulb } from 'lucide-react';
import type { ReviewInfo } from '@/lib/types';

interface ReviewScoreCardProps {
  review: ReviewInfo;
}

const DIMENSIONS = [
  { key: 'medical_accuracy', label: 'Medical Accuracy' },
  { key: 'terminology_correctness', label: 'Terminology' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'style_adherence', label: 'Style Adherence' },
] as const;

export default function ReviewScoreCard({ review }: ReviewScoreCardProps) {
  const pct = Math.round(review.overall_quality * 100);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <Star className="w-4 h-4 text-blue-600" />
          Clinical Review
        </h4>
        <span className={`text-lg font-bold ${pct >= 85 ? 'text-green-700' : pct >= 70 ? 'text-yellow-700' : 'text-red-700'}`}>
          {pct}%
        </span>
      </div>

      {/* Dimension scores */}
      <div className="space-y-1 mb-3">
        {DIMENSIONS.map(({ key, label }) => {
          const score = review[key] || 0;
          return (
            <div key={key} className="flex items-center justify-between text-xs">
              <span className="text-gray-600">{label}</span>
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
          );
        })}
      </div>

      {/* Critical issues */}
      {review.critical_issues.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-red-700 mb-1 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Critical Issues
          </p>
          <ul className="text-xs text-red-600 space-y-0.5">
            {review.critical_issues.map((issue, i) => (
              <li key={i} className="pl-3 border-l-2 border-red-300">{issue}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions */}
      {review.suggestions.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-blue-700 mb-1 flex items-center gap-1">
            <Lightbulb className="w-3 h-3" />
            Suggestions
          </p>
          <ul className="text-xs text-blue-600 space-y-0.5">
            {review.suggestions.map((s, i) => (
              <li key={i} className="pl-3 border-l-2 border-blue-300">{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
