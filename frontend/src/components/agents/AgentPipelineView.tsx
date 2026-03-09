'use client';

import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle, XCircle, Loader2, AlertTriangle, ChevronDown, ChevronRight, ArrowDown, MessageSquare, Send } from 'lucide-react';
import type { AgentTraceEntry } from '@/lib/types';

const AGENT_META: Record<string, { label: string; description: string; color: string; details: string }> = {
  style_analyst: {
    label: 'Style Analyst',
    description: 'Extracting doctor writing style',
    color: 'blue',
    details: 'Analyzes historical notes in Cosmos DB to extract vocabulary patterns, abbreviation maps, sentence structure preferences, and characteristic phrases unique to this doctor.',
  },
  clinical_rag: {
    label: 'Clinical RAG',
    description: 'Retrieving similar historical notes',
    color: 'purple',
    details: 'Searches Azure AI Search for relevant prior reports matching the body region and report type. Returns few-shot examples to guide the Report Writer agent.',
  },
  report_writer: {
    label: 'Report Writer',
    description: 'Generating report sections',
    color: 'teal',
    details: 'Uses GPT-5.2 to generate Findings, Impressions, and Recommendations. Incorporates the doctor\'s style profile and RAG examples for stylistically accurate output.',
  },
  grounding_validator: {
    label: 'Grounding Validator',
    description: 'Verifying claim accuracy',
    color: 'orange',
    details: 'AI-powered grounding check — verifies every claim in the generated report traces back to the original dictation. Returns per-section confidence scores and flags hallucinated claims.',
  },
  clinical_reviewer: {
    label: 'Clinical Reviewer',
    description: 'Peer reviewing quality',
    color: 'pink',
    details: 'Evaluates medical accuracy, terminology correctness, completeness, and style adherence. May flag critical issues that trigger a revision cycle.',
  },
};

// Simulated inter-agent messages shown during the pipeline run
const AGENT_MESSAGES: Record<string, string[]> = {
  style_analyst: [
    '→ Supervisor: Requesting style profile for doctor…',
    '→ Cosmos DB: Querying style_profiles container…',
    '← Style profile loaded: tone=concise_clinical, 12 sample phrases',
    '→ Supervisor: Style instructions compiled, passing to next agent',
  ],
  clinical_rag: [
    '→ Supervisor: Starting RAG retrieval…',
    '→ Azure AI Search: vector query for body_region + report_type…',
    '← Retrieved 3 similar historical reports (cosine > 0.82)',
    '→ Supervisor: Few-shot examples ready',
  ],
  report_writer: [
    '→ Supervisor: Generating report with style + RAG context…',
    '→ GPT-5.2: Sending prompt (system + 3 few-shot + dictation)…',
    '← GPT-5.2: Generated Findings (247 tokens), Impressions (89 tokens), Recommendations (42 tokens)',
    '→ Supervisor: Draft report ready for validation',
  ],
  grounding_validator: [
    '→ Supervisor: Validating grounding of generated report…',
    '→ GPT-5.2: Cross-referencing each claim against dictation…',
    '← Grounding check: all claims verified, confidence 0.94',
    '→ Supervisor: Report is grounded — no hallucinations detected',
  ],
  clinical_reviewer: [
    '→ Supervisor: Peer reviewing report quality…',
    '→ GPT-5.2: Evaluating medical accuracy, terminology, completeness…',
    '← Review: quality=0.92, accuracy=0.95, style=0.89, no critical issues',
    '→ Supervisor: Report ACCEPTED — all thresholds met',
  ],
};

interface AgentPipelineViewProps {
  trace: AgentTraceEntry[];
  isRunning?: boolean;
  currentAgent?: string;
  decision?: string;
  revisions?: number;
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

export default function AgentPipelineView({ trace, isRunning, currentAgent, decision, revisions }: AgentPipelineViewProps) {
  const agentOrder = ['style_analyst', 'clinical_rag', 'report_writer', 'grounding_validator', 'clinical_reviewer'];
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [simulatedStep, setSimulatedStep] = useState(0);
  const [simulatedMessages, setSimulatedMessages] = useState<Record<string, string[]>>({});
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Simulate step-by-step agent execution when running
  useEffect(() => {
    if (!isRunning) {
      setSimulatedStep(0);
      setSimulatedMessages({});
      return;
    }

    // Build a flat list of all messages to reveal sequentially
    const allSteps: { agent: string; message: string }[] = [];
    for (const agentName of agentOrder) {
      const msgs = AGENT_MESSAGES[agentName] || [];
      for (const msg of msgs) {
        allSteps.push({ agent: agentName, message: msg });
      }
    }

    let currentStep = 0;
    setSimulatedMessages({});
    // Auto-expand all agents during run
    const expandAll: Record<string, boolean> = {};
    agentOrder.forEach((a) => (expandAll[a] = true));
    setExpanded(expandAll);

    intervalRef.current = setInterval(() => {
      if (currentStep >= allSteps.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
      const step = allSteps[currentStep];
      setSimulatedStep(currentStep + 1);
      setSimulatedMessages((prev) => ({
        ...prev,
        [step.agent]: [...(prev[step.agent] || []), step.message],
      }));
      currentStep++;
    }, 800);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isRunning]);

  const toggleExpand = (agentName: string) => {
    setExpanded((prev) => ({ ...prev, [agentName]: !prev[agentName] }));
  };

  // Determine which agent is "active" during simulation
  const getActiveAgent = () => {
    if (!isRunning) return null;
    const totalMsgs = agentOrder.reduce((sum, a) => sum + (AGENT_MESSAGES[a]?.length || 0), 0);
    if (simulatedStep >= totalMsgs) return null;
    let count = 0;
    for (const agentName of agentOrder) {
      count += AGENT_MESSAGES[agentName]?.length || 0;
      if (simulatedStep < count) return agentName;
    }
    return null;
  };

  const activeAgent = currentAgent || getActiveAgent();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
        Multi-Agent Pipeline
        {isRunning && (
          <span className="ml-auto flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 font-normal">
            <Loader2 className="w-3 h-3 animate-spin" />
            Processing…
          </span>
        )}
        {!isRunning && trace.length > 0 && (
          <span className="ml-auto text-xs text-green-600 dark:text-green-400 font-normal flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Complete
          </span>
        )}
      </h3>

      <div className="space-y-1">
        {agentOrder.map((agentName, idx) => {
          const entries = trace.filter((t) => t.agent === agentName);
          const latest = entries[entries.length - 1];
          const meta = AGENT_META[agentName] || { label: agentName, description: '', color: 'gray', details: '' };
          const isActive = activeAgent === agentName;
          const isExpanded = expanded[agentName] || false;
          const msgs = isRunning ? (simulatedMessages[agentName] || []) : [];
          const hasContent = latest || msgs.length > 0;

          // Check if agent is done during simulation
          const isDoneSim = isRunning && simulatedMessages[agentName]?.length === (AGENT_MESSAGES[agentName]?.length || 0);

          return (
            <div key={agentName}>
              {idx > 0 && (
                <div className="flex justify-center py-0.5">
                  <ArrowDown className="w-3 h-3 text-gray-300 dark:text-slate-600" />
                </div>
              )}
              <div
                className={`rounded-md border transition-all ${
                  isActive
                    ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-600 ring-1 ring-blue-300'
                    : latest
                      ? latest.success
                        ? 'border-green-200 bg-green-50/50 dark:bg-green-900/10 dark:border-green-800'
                        : 'border-red-200 bg-red-50/50 dark:bg-red-900/10 dark:border-red-800'
                      : isDoneSim
                        ? 'border-green-200 bg-green-50/50 dark:bg-green-900/10 dark:border-green-800'
                        : 'border-gray-200 bg-gray-50 dark:bg-slate-800 dark:border-slate-700'
                }`}
              >
                {/* Agent header — clickable to expand */}
                <button
                  onClick={() => toggleExpand(agentName)}
                  className="w-full flex items-center justify-between p-2.5 text-left"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isActive ? (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500 shrink-0" />
                    ) : latest ? (
                      latest.success ? (
                        <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                      )
                    ) : isDoneSim ? (
                      <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-slate-600 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate">{meta.label}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{meta.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {latest && <ConfidenceBadge confidence={latest.confidence} />}
                    {latest?.revision !== undefined && latest.revision > 0 && (
                      <span className="text-xs text-orange-600 flex items-center gap-0.5">
                        <AlertTriangle className="w-3 h-3" />
                        Rev {latest.revision}
                      </span>
                    )}
                    {hasContent ? (
                      isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )
                    ) : null}
                  </div>
                </button>

                {/* Expandable detail panel */}
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-gray-200 dark:border-slate-700 mt-0">
                    <p className="text-xs text-gray-600 dark:text-slate-400 mt-2 mb-2 leading-relaxed">
                      {meta.details}
                    </p>

                    {/* Inter-agent messages (real-time during run, or static from trace) */}
                    {(msgs.length > 0 || latest) && (
                      <div className="space-y-1 mt-2">
                        <p className="text-xs font-medium text-gray-500 dark:text-slate-500 flex items-center gap-1 mb-1">
                          <MessageSquare className="w-3 h-3" />
                          Agent Communication
                        </p>
                        {msgs.map((msg, mi) => (
                          <div key={mi} className="flex items-start gap-1.5 text-xs animate-fade-in">
                            <Send className="w-3 h-3 mt-0.5 text-blue-400 shrink-0" />
                            <span className={`font-mono leading-relaxed ${
                              msg.startsWith('←')
                                ? 'text-green-700 dark:text-green-400'
                                : 'text-gray-600 dark:text-slate-400'
                            }`}>
                              {msg}
                            </span>
                          </div>
                        ))}
                        {/* Show static trace data when not running */}
                        {!isRunning && latest && (
                          <div className="mt-2 bg-gray-100 dark:bg-slate-700 rounded p-2 text-xs font-mono space-y-0.5">
                            <div>
                              <span className="text-gray-500">success:</span>{' '}
                              <span className={latest.success ? 'text-green-700 dark:text-green-400' : 'text-red-600'}>
                                {String(latest.success)}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-500">confidence:</span>{' '}
                              <span className="text-blue-700 dark:text-blue-400">{latest.confidence}</span>
                            </div>
                            {latest.revision !== undefined && (
                              <div>
                                <span className="text-gray-500">revision:</span>{' '}
                                <span className="text-orange-600">{latest.revision}</span>
                              </div>
                            )}
                            {latest.error && (
                              <div>
                                <span className="text-gray-500">error:</span>{' '}
                                <span className="text-red-600">{latest.error}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Supervisor summary at bottom */}
        <div className="flex justify-center py-0.5">
          <ArrowDown className="w-3 h-3 text-gray-300 dark:text-slate-600" />
        </div>
        {(() => {
          const allSimDone = isRunning && simulatedStep >= agentOrder.reduce((s, a) => s + (AGENT_MESSAGES[a]?.length || 0), 0);
          const isComplete = !isRunning && trace.length > 0;
          const isAccepted = decision === 'accepted';
          const isWarning = decision === 'accepted_with_warnings';
          return (
            <div className={`rounded-md border p-2.5 transition-all ${
              allSimDone
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-300'
                : isComplete
                  ? isAccepted
                    ? 'border-green-200 bg-green-50 dark:bg-green-900/10'
                    : isWarning
                      ? 'border-yellow-200 bg-yellow-50 dark:bg-yellow-900/10'
                      : 'border-green-200 bg-green-50 dark:bg-green-900/10'
                  : 'border-gray-200 bg-gray-50 dark:bg-slate-800 dark:border-slate-700'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {allSimDone ? (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  ) : isComplete ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : isRunning ? (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-slate-600" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-slate-600" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-slate-100">Supervisor</p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">
                      {allSimDone
                        ? 'Evaluating agent results...'
                        : isComplete && decision
                          ? `Decision: ${decision}${revisions ? ` (${revisions} revision${revisions > 1 ? 's' : ''})` : ''}`
                          : 'Decision: accept / revise / reject'}
                    </p>
                  </div>
                </div>
                {isComplete && decision && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    isAccepted
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : isWarning
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                        : 'bg-blue-100 text-blue-800'
                  }`}>
                    {isAccepted ? 'ACCEPTED' : isWarning ? 'ACCEPTED*' : decision.toUpperCase()}
                  </span>
                )}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
