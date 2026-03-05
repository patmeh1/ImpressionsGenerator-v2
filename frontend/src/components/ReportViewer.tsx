'use client';

import React from 'react';
import type { Report } from '@/lib/types';
import AgentPipelineView from '@/components/agents/AgentPipelineView';
import GroundingScoreCard from '@/components/agents/GroundingScoreCard';
import ReviewScoreCard from '@/components/agents/ReviewScoreCard';
import { FileText, RefreshCw, CheckCircle } from 'lucide-react';

interface ReportViewerProps {
  report: Report;
}

export default function ReportViewer({ report }: ReportViewerProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            Generated Report
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {report.report_type} — {report.body_region}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {report.revisions > 0 && (
            <span className="text-xs text-orange-600 flex items-center gap-1 bg-orange-50 px-2 py-1 rounded-full">
              <RefreshCw className="w-3 h-3" />
              {report.revisions} revision{report.revisions > 1 ? 's' : ''}
            </span>
          )}
          <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${
            report.decision === 'accepted'
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            <CheckCircle className="w-3 h-3" />
            {report.decision}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report content */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Findings</h3>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.findings}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Impressions</h3>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.impressions}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Recommendations</h3>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.recommendations}</p>
          </div>
        </div>

        {/* Agent pipeline & scores sidebar */}
        <div className="space-y-4">
          <AgentPipelineView trace={report.pipeline_trace || []} />
          {report.grounding && <GroundingScoreCard grounding={report.grounding} />}
          {report.review && <ReviewScoreCard review={report.review} />}
        </div>
      </div>
    </div>
  );
}
