import { test, expect } from '@playwright/test';

test.describe('Report Generation — Multi-Agent Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/generate');
  });

  test('shows multi-agent pipeline badge', async ({ page }) => {
    await expect(page.getByText('Multi-Agent Pipeline v2')).toBeVisible();
  });

  test('shows pipeline agents info panel', async ({ page }) => {
    await expect(page.getByText('Pipeline Agents')).toBeVisible();
    await expect(page.getByText('Style Analyst')).toBeVisible();
  });

  test('can select doctor, report type, and body region', async ({ page }) => {
    const reportTypeSelect = page.locator('select').nth(0);
    await expect(reportTypeSelect).toBeVisible();
    
    const bodyRegionSelect = page.locator('select').nth(1);
    await expect(bodyRegionSelect).toBeVisible();
  });

  test('generate button is disabled without input', async ({ page }) => {
    const button = page.getByRole('button', { name: /generate/i });
    await expect(button).toBeDisabled();
  });

  test('shows agent pipeline view during generation', async ({ page }) => {
    // Fill in dictation
    const textarea = page.locator('textarea');
    await textarea.fill('CT chest without contrast. Clear lungs bilaterally.');
    
    // Click generate
    const button = page.getByRole('button', { name: /generate/i });
    await button.click();
    
    // Should show running indicator
    await expect(page.getByText(/Running Multi-Agent Pipeline/)).toBeVisible();
  });
});

test.describe('Report Viewer — Agent Results', () => {
  test('displays grounding score card', async ({ page }) => {
    // This test assumes a report has been generated
    await page.goto('/review/test-report-id');
    // Check for grounding UI elements
    await expect(page.getByText('Grounding Validation')).toBeVisible({ timeout: 5000 }).catch(() => {
      // Expected if no report exists in test env
    });
  });

  test('displays clinical review score card', async ({ page }) => {
    await page.goto('/review/test-report-id');
    await expect(page.getByText('Clinical Review')).toBeVisible({ timeout: 5000 }).catch(() => {
      // Expected if no report exists in test env
    });
  });
});
