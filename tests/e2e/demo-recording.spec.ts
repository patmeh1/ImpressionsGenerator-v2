import { test, chromium } from '@playwright/test';

/**
 * Impressions Generator v2 — Browser Demo Recording
 *
 * Records a full walkthrough of the multi-agent pipeline as an mp4 file.
 *
 * Usage:
 *   npx playwright test tests/e2e/demo-recording.spec.ts
 *
 * Prerequisites:
 *   - Application deployed and accessible
 *   - Set DEMO_BASE_URL environment variable (or defaults to http://localhost:3000)
 *
 * Output:
 *   - demo-recording.webm in the test-results directory
 *   - Convert to mp4: ffmpeg -i demo-recording.webm -c:v libx264 demo.mp4
 */

const BASE_URL = process.env.DEMO_BASE_URL || 'http://localhost:3000';
const DEMO_DICTATION = `CT chest without contrast performed on a 58-year-old male with history of cough.

Lungs: Clear bilaterally. No focal consolidation, pleural effusion, or pneumothorax.
Heart: Normal cardiac silhouette. No pericardial effusion.
Mediastinum: No mediastinal lymphadenopathy. Thoracic aorta is normal in caliber.
Bones: No acute osseous abnormality. Mild degenerative changes in the thoracic spine.
Soft tissues: Unremarkable.

3.2 cm nodule identified in the right lower lobe, unchanged from prior CT dated January 15, 2026.
1.8 cm left adrenal nodule, stable.`;

test.describe('Demo Recording — Multi-Agent Pipeline', () => {
  test('full pipeline walkthrough', async () => {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      recordVideo: {
        dir: './test-results/',
        size: { width: 1920, height: 1080 },
      },
    });
    const page = await context.newPage();

    // ── Scene 1: Landing Page ──
    await page.goto(BASE_URL);
    await page.waitForTimeout(2000);

    // ── Scene 2: Navigate to Dashboard ──
    await page.click('text=Dashboard');
    await page.waitForTimeout(2000);

    // ── Scene 3: Navigate to Generate page ──
    await page.click('text=Generate');
    await page.waitForTimeout(1500);

    // Verify multi-agent badge is visible
    await page.waitForSelector('text=Multi-Agent Pipeline v2');
    await page.waitForTimeout(1000);

    // ── Scene 4: Select Doctor ──
    const doctorSelector = page.locator('select').first();
    if (await doctorSelector.isVisible()) {
      await doctorSelector.selectOption({ index: 1 });
      await page.waitForTimeout(1000);
    }

    // ── Scene 5: Select Report Type ──
    const reportTypeSelect = page.locator('select').nth(1);
    if (await reportTypeSelect.isVisible()) {
      await reportTypeSelect.selectOption('CT');
      await page.waitForTimeout(500);
    }

    // ── Scene 6: Select Body Region ──
    const bodyRegionSelect = page.locator('select').nth(2);
    if (await bodyRegionSelect.isVisible()) {
      await bodyRegionSelect.selectOption('Chest');
      await page.waitForTimeout(500);
    }

    // ── Scene 7: Enter Dictation ──
    const textarea = page.locator('textarea');
    if (await textarea.isVisible()) {
      await textarea.click();
      await page.waitForTimeout(500);

      // Type slowly for demo effect
      for (const char of DEMO_DICTATION) {
        await textarea.press(char === '\n' ? 'Enter' : char);
        await page.waitForTimeout(10); // Typing speed
      }
      await page.waitForTimeout(1500);
    }

    // ── Scene 8: Click Generate ──
    const generateButton = page.getByRole('button', { name: /generate/i });
    if (await generateButton.isVisible()) {
      await generateButton.click();
      await page.waitForTimeout(1000);

      // Wait for pipeline to show progress
      try {
        await page.waitForSelector('text=Running Multi-Agent Pipeline', { timeout: 5000 });
        await page.waitForTimeout(2000);
      } catch {
        // Button text may differ
      }

      // Wait for generation to complete (up to 60 seconds)
      try {
        await page.waitForSelector('text=accepted', { timeout: 60000 });
        await page.waitForTimeout(2000);
      } catch {
        // Generation may take longer or timeout
        await page.waitForTimeout(5000);
      }
    }

    // ── Scene 9: Review Generated Report ──
    // Scroll to see the full report
    await page.evaluate(() => window.scrollTo({ top: 500, behavior: 'smooth' }));
    await page.waitForTimeout(2000);

    // Scroll to see grounding and review scores
    await page.evaluate(() => window.scrollTo({ top: 1000, behavior: 'smooth' }));
    await page.waitForTimeout(2000);

    // ── Scene 10: Show Pipeline Trace ──
    // Look for the pipeline view
    try {
      const pipelineSection = page.locator('text=Multi-Agent Pipeline').first();
      if (await pipelineSection.isVisible()) {
        await pipelineSection.scrollIntoViewIfNeeded();
        await page.waitForTimeout(3000);
      }
    } catch {
      // Pipeline view may not be visible
    }

    // ── Scene 11: Navigate to History ──
    try {
      await page.click('text=History');
      await page.waitForTimeout(2000);
    } catch {
      // History link may not exist
    }

    // ── Scene 12: Navigate to Admin ──
    try {
      await page.click('text=Admin');
      await page.waitForTimeout(2000);
    } catch {
      // Admin link may not exist
    }

    // ── End: Scroll back to top ──
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await page.waitForTimeout(2000);

    // Close context to save the video
    await context.close();
    await browser.close();
  });
});
