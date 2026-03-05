'use client';

import React from 'react';
import type { StyleProfile } from '@/lib/types';
import { Sparkles, MessageSquare, ListOrdered } from 'lucide-react';

interface StylePreviewProps {
  styleProfile: StyleProfile;
}

export default function StylePreview({ styleProfile }: StylePreviewProps) {
  const abbreviations = Object.entries(styleProfile.abbreviation_map || {});

  return (
    <div className="card p-5 space-y-4">
      <h3 className="section-heading flex items-center gap-2">
        <Sparkles size={20} className="text-teal-500" />
        Style Profile
      </h3>

      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 mb-2">
          <MessageSquare size={14} />
          Common Abbreviations
        </div>
        <div className="flex flex-wrap gap-1.5">
          {abbreviations.length === 0 ? (
            <span className="text-xs text-slate-400">None detected</span>
          ) : (
            abbreviations.map(([abbr, full], i) => (
              <span
                key={i}
                className="inline-block px-2 py-0.5 bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 text-xs rounded-md font-mono"
              >
                {abbr} = {full}
              </span>
            ))
          )}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 mb-2">
          <Sparkles size={14} />
          Sample Phrases
        </div>
        <ul className="space-y-1">
          {(styleProfile.sample_phrases || []).length === 0 ? (
            <li className="text-xs text-slate-400">None detected</li>
          ) : (
            styleProfile.sample_phrases.map((phrase, i) => (
              <li
                key={i}
                className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 rounded px-2 py-1 font-mono"
              >
                &ldquo;{phrase}&rdquo;
              </li>
            ))
          )}
        </ul>
      </div>

      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 mb-2">
          <ListOrdered size={14} />
          Section Order
        </div>
        <ol className="list-decimal list-inside text-xs text-slate-600 dark:text-slate-400 space-y-0.5">
          {(styleProfile.section_ordering || []).map((section, i) => (
            <li key={i}>{section}</li>
          ))}
        </ol>
      </div>

      <div className="pt-2 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500">
        <span>Vocabulary: <strong className="text-slate-700 dark:text-slate-300">{(styleProfile.vocabulary_patterns || []).slice(0, 5).join(', ') || 'None'}</strong></span>
      </div>
    </div>
  );
}
