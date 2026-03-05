/**
 * Demo recording for Impressions Generator v2
 * Records a walkthrough of the multi-agent pipeline UI and API
 */
const { chromium } = require('@playwright/test');

const BASE_URL = process.env.DEMO_BASE_URL || 'http://localhost:3000';
const API_URL = 'https://impgen2-api-dev.agreeableglacier-0822af48.swedencentral.azurecontainerapps.io';

(async () => {
  console.log('Starting demo recording...');
  console.log(`Frontend: ${BASE_URL}`);
  console.log(`API: ${API_URL}`);

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: './recordings/',
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();

  // Scene 1: Landing page
  console.log('Scene 1: Landing page');
  await page.goto(BASE_URL);
  await page.waitForTimeout(3000);

  // Scene 2: Navigate to Generate page
  console.log('Scene 2: Generate page');
  try {
    await page.click('text=Generate', { timeout: 5000 });
  } catch {
    await page.goto(`${BASE_URL}/generate`);
  }
  await page.waitForTimeout(3000);

  // Scene 3: Show the multi-agent pipeline badge and form
  console.log('Scene 3: Pipeline UI overview');
  await page.waitForTimeout(2000);

  // Scene 4: Navigate to Dashboard
  console.log('Scene 4: Dashboard');
  try {
    await page.click('text=Dashboard', { timeout: 3000 });
  } catch {
    await page.goto(`${BASE_URL}/dashboard`);
  }
  await page.waitForTimeout(3000);

  // Scene 5: Navigate to History
  console.log('Scene 5: History');
  try {
    await page.click('text=History', { timeout: 3000 });
  } catch {
    await page.goto(`${BASE_URL}/history`);
  }
  await page.waitForTimeout(3000);

  // Scene 6: Show API health check
  console.log('Scene 6: API health check');
  await page.goto(`${API_URL}/health`);
  await page.waitForTimeout(3000);

  // Scene 7: Show pipeline info (6 agents)
  console.log('Scene 7: Pipeline info (6 agents)');
  await page.goto(`${API_URL}/api/generate/pipeline-info`);
  await page.waitForTimeout(4000);

  // Scene 8: Show API docs (Swagger)
  console.log('Scene 8: API documentation');
  await page.goto(`${API_URL}/docs`);
  await page.waitForTimeout(4000);

  // Scroll through API docs
  await page.evaluate(() => window.scrollTo({ top: 300, behavior: 'smooth' }));
  await page.waitForTimeout(2000);
  await page.evaluate(() => window.scrollTo({ top: 600, behavior: 'smooth' }));
  await page.waitForTimeout(2000);

  // Scene 9: Back to frontend landing
  console.log('Scene 9: Back to frontend');
  await page.goto(BASE_URL);
  await page.waitForTimeout(3000);

  // Close to save video
  console.log('Closing browser and saving recording...');
  const videoPath = await page.video().path();
  await context.close();
  await browser.close();

  console.log(`\nRecording saved to: ${videoPath}`);
  console.log('Done!');
})();
