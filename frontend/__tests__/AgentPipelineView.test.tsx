import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import AgentPipelineView from '@/components/agents/AgentPipelineView';
import type { AgentTraceEntry } from '@/lib/types';

describe('AgentPipelineView', () => {
  const mockTrace: AgentTraceEntry[] = [
    { agent: 'style_analyst', success: true, confidence: 0.95 },
    { agent: 'clinical_rag', success: true, confidence: 0.84 },
    { agent: 'report_writer', success: true, confidence: 0.90, revision: 0 },
    { agent: 'grounding_validator', success: true, confidence: 0.92 },
    { agent: 'clinical_reviewer', success: true, confidence: 0.88 },
  ];

  it('renders all agent names', () => {
    render(<AgentPipelineView trace={mockTrace} />);
    expect(screen.getByText('Style Analyst')).toBeInTheDocument();
    expect(screen.getByText('Clinical RAG')).toBeInTheDocument();
    expect(screen.getByText('Report Writer')).toBeInTheDocument();
    expect(screen.getByText('Grounding Validator')).toBeInTheDocument();
    expect(screen.getByText('Clinical Reviewer')).toBeInTheDocument();
  });

  it('shows confidence percentages', () => {
    render(<AgentPipelineView trace={mockTrace} />);
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('84%')).toBeInTheDocument();
  });

  it('renders empty state without trace', () => {
    render(<AgentPipelineView trace={[]} />);
    expect(screen.getByText('Multi-Agent Pipeline')).toBeInTheDocument();
  });

  it('shows revision badge for revised agents', () => {
    const traceWithRevision: AgentTraceEntry[] = [
      { agent: 'report_writer', success: true, confidence: 0.90, revision: 1 },
    ];
    render(<AgentPipelineView trace={traceWithRevision} />);
    expect(screen.getByText('Rev 1')).toBeInTheDocument();
  });
});
