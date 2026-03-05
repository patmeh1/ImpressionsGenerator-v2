import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ReviewScoreCard from '@/components/agents/ReviewScoreCard';
import type { ReviewInfo } from '@/lib/types';

describe('ReviewScoreCard', () => {
  it('shows overall quality score', () => {
    const review: ReviewInfo = {
      overall_quality: 0.92,
      medical_accuracy: 0.94,
      terminology_correctness: 0.93,
      completeness: 0.90,
      style_adherence: 0.91,
      critical_issues: [],
      suggestions: ['Consider adding comparison.'],
    };
    render(<ReviewScoreCard review={review} />);
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('Clinical Review')).toBeInTheDocument();
  });

  it('shows critical issues', () => {
    const review: ReviewInfo = {
      overall_quality: 0.45,
      medical_accuracy: 0.30,
      terminology_correctness: 0.50,
      completeness: 0.40,
      style_adherence: 0.60,
      critical_issues: ['Incorrect terminology used'],
      suggestions: [],
    };
    render(<ReviewScoreCard review={review} />);
    expect(screen.getByText('Incorrect terminology used')).toBeInTheDocument();
    expect(screen.getByText('Critical Issues')).toBeInTheDocument();
  });

  it('shows dimension scores', () => {
    const review: ReviewInfo = {
      overall_quality: 0.90,
      medical_accuracy: 0.95,
      terminology_correctness: 0.90,
      completeness: 0.85,
      style_adherence: 0.88,
      critical_issues: [],
      suggestions: [],
    };
    render(<ReviewScoreCard review={review} />);
    expect(screen.getByText('Medical Accuracy')).toBeInTheDocument();
    expect(screen.getByText('Terminology')).toBeInTheDocument();
    expect(screen.getByText('Completeness')).toBeInTheDocument();
    expect(screen.getByText('Style Adherence')).toBeInTheDocument();
  });
});
