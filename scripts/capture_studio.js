const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');
const puppeteer = require('B:/workgit/voiceforge/web/node_modules/puppeteer');

async function run() {
  const imagesDir = path.resolve(__dirname, '../docs/images');
  if (!fs.existsSync(imagesDir)) {
    fs.mkdirSync(imagesDir, { recursive: true });
  }

  const framesDir = path.resolve(__dirname, '../temp_frames');
  if (fs.existsSync(framesDir)) {
    fs.rmSync(framesDir, { recursive: true, force: true });
  }
  fs.mkdirSync(framesDir, { recursive: true });

  console.log('Launching headless browser...');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--use-fake-ui-for-media-stream']
  });

  const page = await browser.newPage();

  // 1. Desktop full dashboard (1440x900)
  console.log('Capturing Desktop full view (1440x900)...');
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await page.goto('http://127.0.0.1:8765', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));

  await page.screenshot({ path: path.join(imagesDir, 'voiceforge-1.png') });
  console.log('✓ Saved docs/images/voiceforge-1.png');

  // 2. Open Settings Modal & capture Engine & Audio settings
  console.log('Opening Settings Modal (Engine & Audio)...');
  const settingsBtn = await page.$('button[title="Engine & Voice Settings"]');
  if (settingsBtn) {
    await settingsBtn.click();
    await new Promise(r => setTimeout(r, 600));
    await page.screenshot({ path: path.join(imagesDir, 'voiceforge-2.png') });
    console.log('✓ Saved docs/images/voiceforge-2.png');

    // 3. Switch to Persona Presets tab
    console.log('Switching to Persona Presets tab...');
    const personaTab = await page.evaluateHandle(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.find(b => b.textContent && b.textContent.includes('Persona Presets'));
    });
    if (personaTab) {
      await personaTab.click();
      await new Promise(r => setTimeout(r, 500));
      await page.screenshot({ path: path.join(imagesDir, 'voiceforge-3.png') });
      console.log('✓ Saved docs/images/voiceforge-3.png');
    }

    // Close modal
    const closeBtn = await page.evaluateHandle(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.find(b => b.querySelector('svg.lucide-x'));
    });
    if (closeBtn) {
      await closeBtn.click();
      await new Promise(r => setTimeout(r, 500));
    }
  }

  // 4. Tablet layout (768x1024)
  console.log('Capturing Tablet layout (768x1024)...');
  await page.setViewport({ width: 768, height: 1024, deviceScaleFactor: 2 });
  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: path.join(imagesDir, 'voiceforge-tablet.png') });
  console.log('✓ Saved docs/images/voiceforge-tablet.png');

  // 5. Mobile layout (390x844)
  console.log('Capturing Mobile layout (390x844)...');
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: path.join(imagesDir, 'voiceforge-mobile.png') });
  console.log('✓ Saved docs/images/voiceforge-mobile.png');

  // 6. Capture animated demo sequence on desktop (1280x760)
  console.log('Capturing frames for animated demo GIF...');
  await page.setViewport({ width: 1280, height: 760, deviceScaleFactor: 1 });
  await new Promise(r => setTimeout(r, 600));

  let frameIdx = 0;
  for (let i = 0; i < 20; i++) {
    const frameFile = path.join(framesDir, `frame_${String(frameIdx++).padStart(3, '0')}.png`);
    await page.screenshot({ path: frameFile });
    await new Promise(r => setTimeout(r, 100));
  }

  await browser.close();
  console.log(`Captured ${frameIdx} frames. Compiling demo GIF with ffmpeg...`);

  const gifPath = path.join(imagesDir, 'voiceforge_demo.gif');
  const palettePath = path.join(framesDir, 'palette.png');

  // Generate optimal GIF palette
  execSync(`ffmpeg -y -framerate 10 -i "${framesDir}/frame_%03d.png" -vf "fps=10,scale=1280:-1:flags=lanczos,palettegen" "${palettePath}"`, { stdio: 'ignore' });
  // Render high-fidelity GIF
  execSync(`ffmpeg -y -framerate 10 -i "${framesDir}/frame_%03d.png" -i "${palettePath}" -lavfi "fps=10,scale=1280:-1:flags=lanczos [x]; [x][1:v] paletteuse" "${gifPath}"`, { stdio: 'ignore' });

  console.log('✓ Compiled docs/images/voiceforge_demo.gif');

  // Cleanup temp frames
  fs.rmSync(framesDir, { recursive: true, force: true });
  console.log('✓ Cleaned up temporary frames.');
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
