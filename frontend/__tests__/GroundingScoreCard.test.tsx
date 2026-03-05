import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import GroundingScoreCard from '@/components/agents/GroundingScoreCard';
import type { GroundingInfo } from '@/lib/types';

describe('GroundingScoreCard', () => {
  it('shows grounded status for high confidence', () => {
    const grounding: GroundingInfo = {
      is_grounded: true,
      overall_confidence: 0.95,
      section_scores: { findings: 0.96, impressions: 0.94, recommendations: 0.95 },
      issues: [],
      hallucinated_claims: [],
    };
    render(<GroundingScoreCard grounding={grounding} />);
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('Grounding Validation')).toBeInTheDocument();
  });

  it('shows hallucinated claims', () => {
    const grounding: GroundingInfo = {
      is_grounded: false,
      overall_confidence: 0.40,
      section_scores: {},
      issues: ['Fabricated measurement'],
      hallucinated_claims: ['5mm nodule not in dictation'],
    };
    render(<GroundingScoreCard grounding={grounding} />);
    expect(screen.getByText('5mm nodule not in dictation')).toBeInTheDocument();
    expect(screen.getByText('Hallucinated Claims')).toBeInTheDocument();
  });

  it('shows section score bars', () => {
    const grounding: GroundingInfo = {
      is_grounded: true,
      overall_confidence: 0.90,
      section_scores: { findings: 0.95, impressions: 0.85 },
      issues: [],
      hallucinated_claims: [],
    };
    render(<GroundingScoreCard grounding={grounding} />);
    expect(screen.getByText('findings')).toBeInTheDocument();
    expect(screen.getByText('impressions')).toBeInTheDocument();
  });
});
