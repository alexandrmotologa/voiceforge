const fs = require('fs');
const path = require('path');
const { Resvg } = require('B:/workgit/voiceforge/web/node_modules/@resvg/resvg-js');

function buildLogoSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-clip">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <!-- Optics Gradients -->
    <linearGradient id="cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5ff"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>

    <linearGradient id="cyan-core" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>

    <linearGradient id="amber-beak" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>

    <linearGradient id="slate-chest" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>

    <filter id="subtle-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#000000" flood-opacity="0.18" />
    </filter>
  </defs>

  <!-- Luxury White Squircle Container -->
  <rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />

  <g clip-path="url(#squircle-clip)">
    <g transform="translate(512, 512)" filter="url(#subtle-shadow)">

      <!-- Hexagonal Architectural Gateway -->
      <polygon points="
        0,-390
        338,-195
        338,195
        0,390
        -338,195
        -338,-195
      " fill="none" stroke="#0f172a" stroke-width="40" stroke-linejoin="round" />

      <!-- Inner Hexagonal Telemetry Ring (Dashed Cyan) -->
      <polygon points="
        0,-355
        307,-177
        307,177
        0,355
        -307,177
        -307,-177
      " fill="none" stroke="#00f5ff" stroke-width="4" opacity="0.45" stroke-dasharray="16, 12" />

      <!-- Concentric Acoustic Sound-Ring Radii Behind Mascot -->
      <circle cx="0" cy="-40" r="160" fill="none" stroke="#0284c7" stroke-width="2" opacity="0.25" stroke-dasharray="8, 8" />
      <circle cx="0" cy="-40" r="230" fill="none" stroke="#00f5ff" stroke-width="2" opacity="0.20" stroke-dasharray="12, 12" />

      <!-- ============================================================== -->
      <!-- THE ACOUSTIC OWL MASCOT (Symmetrical Origami Geometry, x=0)    -->
      <!-- ============================================================== -->

      <!-- 1. Watertight Solid Silhouette Base (Zero-Leak Rule) -->
      <path d="
        M 0, -230
        L 55, -240
        L 125, -330
        L 155, -220
        L 210, -110
        L 245, 10
        L 220, 140
        L 160, 240
        L 90, 310
        L 0, 335
        L -90, 310
        L -160, 240
        L -220, 140
        L -245, 10
        L -210, -110
        L -155, -220
        L -125, -330
        L -55, -240
        Z
      " fill="#0b0f19" />

      <!-- 2. Acoustic Ear Tufts (Prominent Angular Horns) -->
      <!-- Left Ear Horn -->
      <polygon points="0,-230 -55,-240 -125,-330 -90,-210" fill="#1e293b" />
      <polygon points="-125,-330 -155,-220 -90,-210" fill="#0f172a" />
      <polygon points="-55,-240 -90,-210 0,-185" fill="#334155" />

      <!-- Right Ear Horn (Mirrored) -->
      <polygon points="0,-230 55,-240 125,-330 90,-210" fill="#334155" />
      <polygon points="125,-330 155,-220 90,-210" fill="#1e293b" />
      <polygon points="55,-240 90,-210 0,-185" fill="#475569" />

      <!-- Crown Center Brow -->
      <polygon points="0,-230 -55,-240 0,-185" fill="#1e293b" />
      <polygon points="0,-230 55,-240 0,-185" fill="#334155" />

      <!-- 3. Parabolic Facial Discs (Left & Right Acoustic Dishes) -->
      <!-- Left Upper Disc -->
      <polygon points="0,-185 -90,-210 -155,-220 -130,-120" fill="#1e293b" />
      <polygon points="0,-185 -130,-120 -60,-100" fill="#334155" />
      <polygon points="-155,-220 -210,-110 -130,-120" fill="#0f172a" />

      <!-- Right Upper Disc -->
      <polygon points="0,-185 90,-210 155,-220 130,-120" fill="#334155" />
      <polygon points="0,-185 130,-120 60,-100" fill="#475569" />
      <polygon points="155,-220 210,-110 130,-120" fill="#1e293b" />

      <!-- Left Lateral Cheek Flank -->
      <polygon points="-130,-120 -210,-110 -245,10 -140,-15" fill="#0b0f19" />
      <polygon points="-60,-100 -130,-120 -140,-15 -55,-20" fill="#1e293b" />
      <polygon points="-140,-15 -245,10 -220,140 -120,85" fill="#0f172a" />

      <!-- Right Lateral Cheek Flank (Mirrored) -->
      <polygon points="130,-120 210,-110 245,10 140,-15" fill="#1e293b" />
      <polygon points="60,-100 130,-120 140,-15 55,-20" fill="#334155" />
      <polygon points="140,-15 245,10 220,140 120,85" fill="#1e293b" />

      <!-- Forehead Keystone Bridge -->
      <polygon points="0,-185 -60,-100 0,-70" fill="#0f172a" />
      <polygon points="0,-185 60,-100 0,-70" fill="#1e293b" />
      <polygon points="0,-70 -60,-100 -55,-20 0,-15" fill="#1e293b" />
      <polygon points="0,-70 60,-100 55,-20 0,-15" fill="#334155" />

      <!-- 4. Electric Predatory Optics (Sharp Upward Predatory Cant) -->
      <!-- Left Eye Socket -->
      <polygon points="-35,-15 -130,-35 -115,25 -35,15" fill="#050811" />
      <!-- Left Cyan Iris (Sleek Almond Jewel Slanted Upward Toward Ear) -->
      <polygon points="-45,-10 -115,-25 -100,18 -45,10" fill="url(#cyan-glow)" />
      <!-- Left Slit Pupil (Vertical Precision Bar) -->
      <polygon points="-78,-16 -82,6 -74,6" fill="#050811" />
      <circle cx="-95" cy="-8" r="3" fill="#ffffff" opacity="0.95" />

      <!-- Right Eye Socket (Mirrored) -->
      <polygon points="35,-15 130,-35 115,25 35,15" fill="#050811" />
      <!-- Right Cyan Iris (Sleek Almond Jewel Slanted Upward Toward Ear) -->
      <polygon points="45,-10 115,-25 100,18 45,10" fill="url(#cyan-glow)" />
      <!-- Right Slit Pupil (Vertical Precision Bar) -->
      <polygon points="78,-16 82,6 74,6" fill="#050811" />
      <circle cx="95" cy="-8" r="3" fill="#ffffff" opacity="0.95" />

      <!-- Eye Socket Precision Eyebrows (Cyan Trim) -->
      <line x1="-35" y1="-18" x2="-130" y2="-38" stroke="#00f5ff" stroke-width="3" opacity="0.85" />
      <line x1="35" y1="-18" x2="130" y2="-38" stroke="#00f5ff" stroke-width="3" opacity="0.85" />

      <!-- 5. Acoustic Nasal Bridge & Amber Titanium Beak -->
      <polygon points="0,-15 -35,15 0,35" fill="#1e293b" />
      <polygon points="0,-15 35,15 0,35" fill="#334155" />

      <!-- Amber Titanium Beak Facets (5% Contrast Accent) -->
      <polygon points="0,35 -20,20 -15,80 0,105" fill="url(#amber-beak)" />
      <polygon points="0,35 20,20 15,80 0,105" fill="#d97706" />
      <polygon points="0,105 -15,80 0,75" fill="#b45309" />
      <polygon points="0,105 15,80 0,75" fill="#92400e" />

      <!-- 6. Lower Facial Disc & Throat Armor -->
      <polygon points="-35,15 -115,25 -120,85 -35,95" fill="#0f172a" />
      <polygon points="35,15 115,25 120,85 35,95" fill="#1e293b" />

      <polygon points="0,115 -35,95 -60,150 0,165" fill="#1e293b" />
      <polygon points="0,115 35,95 60,150 0,165" fill="#334155" />

      <polygon points="-35,95 -120,85 -160,240 -60,150" fill="#0b0f19" />
      <polygon points="35,95 120,85 160,240 60,150" fill="#0f172a" />

      <!-- 7. Origami Breastplate & Sternum Plates -->
      <polygon points="0,165 -60,150 -50,230 0,250" fill="#0f172a" />
      <polygon points="0,165 60,150 50,230 0,250" fill="#1e293b" />

      <polygon points="-60,150 -160,240 -110,285 -50,230" fill="#0b0f19" />
      <polygon points="60,150 160,240 110,285 50,230" fill="#0f172a" />

      <polygon points="0,250 -50,230 -110,285 -70,315 0,335" fill="#1e293b" />
      <polygon points="0,250 50,230 110,285 70,315 0,335" fill="#334155" />

      <!-- Cyan Telemetry Pips on Sternum Center -->
      <circle cx="0" cy="190" r="4" fill="#00f5ff" />
      <circle cx="0" cy="255" r="3.5" fill="#00f5ff" opacity="0.8" />
      <circle cx="0" cy="305" r="3" fill="#00f5ff" opacity="0.6" />

    </g>
  </g>
</svg>`;
}

async function run() {
  const outputDir = path.resolve(__dirname, '../docs/images');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const svg = buildLogoSvg();
  const svgPath = path.join(outputDir, 'logo.svg');
  const pngPath = path.join(outputDir, 'logo.png');

  fs.writeFileSync(svgPath, svg, 'utf-8');
  console.log('✓ Written', svgPath);

  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: 1024 }
  });
  const pngData = resvg.render();
  const pngBuffer = pngData.asPng();
  fs.writeFileSync(pngPath, pngBuffer);
  console.log('✓ Rendered', pngPath, `(${pngBuffer.length} bytes, 1024x1024)`);
}

run().catch(console.error);
