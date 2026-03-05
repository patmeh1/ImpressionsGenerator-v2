'use client';

import React from 'react';
import { CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import type { AgentTraceEntry } from '@/lib/types';

const AGENT_LABELS: Record<string, { label: string; description: string }> = {
  style_analyst: { label: 'Style Analyst', description: 'Extracting doctor writing style' },
  clinical_rag: { label: 'Clinical RAG', description: 'Retrieving similar historical notes' },
  report_writer: { label: 'Report Writer', description: 'Generating report sections' },
  grounding_validator: { label: 'Grounding Validator', description: 'Verifying claim accuracy' },
  clinical_reviewer: { label: 'Clinical Reviewer', description: 'Peer reviewing quality' },
  supervisor: { label: 'Supervisor', description: 'Orchestrating pipeline' },
};

interface AgentPipelineViewProps {
  trace: AgentTraceEntry[];
  isRunning?: boolean;
  currentAgent?: string;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  let color = 'bg-green-100 text-green-800';
  if (pct < 70) color = 'bg-red-100 text-red-800';
  else if (pct < 85) color = 'bg-yellow-100 text-yellow-800';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {pct}%
    </span>
  );
}

export default function AgentPipelineView({ trace, isRunning, currentAgent }: AgentPipelineViewProps) {
  const agentOrder = ['style_analyst', 'clinical_rag', 'report_writer', 'grounding_validator', 'clinical_reviewer'];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        Multi-Agent Pipeline
        {isRunning && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
      </h3>

      <div className="space-y-2">
        {agentOrder.map((agentName, idx) => {
          const entries = trace.filter((t) => t.agent === agentName);
          const latest = entries[entries.length - 1];
          const info = AGENT_LABELS[agentName] || { label: agentName, description: '' };
          const isActive = currentAgent === agentName;

          return (
            <div key={agentName}>
              {idx > 0 && (
                <div className="flex justify-center py-0.5">
                  <div className="w-0.5 h-3 bg-gray-300" />
                </div>
              )}
              <div
                className={`flex items-center justify-between p-2 rounded-md border ${
                  isActive
                    ? 'border-blue-400 bg-blue-50'
                    : latest
                    ? latest.success
                      ? 'border-green-200 bg-green-50'
                      : 'border-red-200 bg-red-50'
                    : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  {isActive ? (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  ) : latest ? (
                    latest.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">{info.label}</p>
                    <p className="text-xs text-gray-500">{info.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {latest && <ConfidenceBadge confidence={latest.confidence} />}
                  {latest?.revision !== undefined && latest.revision > 0 && (
                    <span className="text-xs text-orange-600 flex items-center gap-0.5">
                      <AlertTriangle className="w-3 h-3" />
                      Rev {latest.revision}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
