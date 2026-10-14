// KAIO pitch deck as an editable PowerPoint (for Canva import). Run: node docs/build_pptx.js
const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');
const { applyTheme } = require(process.env.PPTX_SKILL + '/scripts/apply_theme.js');
const A = p => path.join(__dirname, 'pptx_assets', p);
const V = JSON.parse(fs.readFileSync(A('values.json')));

const THEME = { name: 'KAIO', headFontFace: 'Space Grotesk', bodyFontFace: 'Space Grotesk',
  colors: { dk1: '0A0F1E', lt1: 'FFFFFF', dk2: '121A2B', lt2: 'E9EDF6', accent1: '5AA2F0', accent2: 'E9A23B',
            accent3: 'A1487A', accent4: '3FC0B0', accent5: '9AA6C2', accent6: 'EE6A57', hlink: '5AA2F0', folHlink: 'A497EC' } };

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.title = 'KAIO: which images deserve the downlink?';
pres.author = V.team;
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const INK = C.background2, MUTED = C.accent5, BLUE = C.accent1, AMBER = C.accent2;

pres.defineSlideMaster({ title: 'KAIO_COVER', background: { path: A('bg_cover.jpg') },
  objects: [], slideNumber: { x: 9.2, y: 5.25, w: 0.5, h: 0.25, fontSize: 9, color: '6B7899' } });
pres.defineSlideMaster({ title: 'KAIO_CONTENT', background: { path: A('bg_dark.jpg') },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.32, w: 9.0, h: 0.6, fontSize: 26, bold: true, color: INK, valign: 'middle', align: 'left', margin: 0 }, text: '' } },
    { text: { text: 'KAIO', options: { x: 0.5, y: 5.22, w: 2, h: 0.25, fontSize: 9, color: '6B7899', margin: 0 } } },
  ],
  slideNumber: { x: 9.2, y: 5.22, w: 0.5, h: 0.25, fontSize: 9, color: '6B7899' } });

const card = (s, x, y, w, h, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08,
  fill: { color: '111A30', transparency: 15 }, line: { color: '26324F', width: 0.75 }, objectName: name });
const stat = (s, x, y, w, big, small, name) => {
  card(s, x, y, w, 1.15, name + ' card');
  s.addText(big, { x: x + 0.18, y: y + 0.1, w: w - 0.3, h: 0.55, fontSize: 30, bold: true, color: '7DB6F5', margin: 0, isTextBox: true, objectName: name + ' value' });
  s.addText(small, { x: x + 0.18, y: y + 0.63, w: w - 0.3, h: 0.45, fontSize: 11, color: 'B3BDD3', margin: 0, valign: 'top', isTextBox: true, objectName: name + ' label' });
};
const white = (s, x, y, w, h, img, iw, ih, name) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF' }, objectName: name + ' panel' });
  const pad = 0.12, aw = w - 2 * pad, ah = h - 2 * pad, r = Math.min(aw / iw, ah / ih);
  s.addImage({ path: A(img), x: x + pad + (aw - iw * r) / 2, y: y + pad + (ah - ih * r) / 2, w: iw * r, h: ih * r, objectName: name });
};
const bullets = (s, items, x, y, w, h, size = 13) => s.addText(
  items.map((t, i) => ({ text: t[0], options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 8 } , runs: t })).map(o => o),
  { x, y, w, h, fontSize: size, color: 'D3DAEA', valign: 'top', margin: 0, isTextBox: true });
function richBullets(s, items, x, y, w, h, size = 13, name = 'bullets') {
  const runs = [];
  items.forEach((it, i) => {
    runs.push({ text: it[0], options: { bold: true, color: 'E9EDF6', bullet: true } });
    runs.push({ text: it[1], options: { color: 'C5CDE0', breakLine: i < items.length - 1, paraSpaceAfter: 9 } });
  });
  s.addText(runs, { x, y, w, h, fontSize: size, valign: 'top', margin: 0, isTextBox: true, objectName: name });
}

// 1 cover
pres.addSection({ title: 'Opening' });
let s = pres.addSlide({ masterName: 'KAIO_COVER', sectionTitle: 'Opening' });
s.addText(V.event, { x: 0.6, y: 0.55, w: 5.2, h: 0.3, fontSize: 10, color: '9AA6C2', margin: 0, isTextBox: true, objectName: 'event' });
s.addImage({ path: A('logo_dark.png'), x: 0.6, y: 1.0, w: 1.58, h: 0.55, objectName: 'KAIO logo', altText: 'KAIO logo' });
s.addText('Which images deserve the downlink?', { x: 0.6, y: 1.6, w: 4.7, h: 1.6, fontSize: 32, bold: true, color: INK, margin: 0, valign: 'top', isTextBox: true, objectName: 'headline' });
s.addText('Onboard decisions for an Earth-observation satellite, flown on the real orbit of Φsat-2 with real NASA data.', { x: 0.6, y: 3.4, w: 4.4, h: 0.8, fontSize: 14, color: 'C5CDE0', margin: 0, valign: 'top', isTextBox: true, objectName: 'lead' });
s.addText(`${V.team} · ${V.members}`, { x: 0.6, y: 4.35, w: 4.6, h: 0.3, fontSize: 12, color: '9AA6C2', margin: 0, isTextBox: true, objectName: 'team' });
s.addImage({ path: A('../figures/dash_hero_dark.jpg'), x: 5.45, y: 0.95, w: 4.9, h: 2.93, rounding: false, objectName: 'dashboard screenshot' });
s.addNotes('Hook: real orbit of Phi-sat-2; far more images than downlink; KAIO decides which ones matter.');

// 2 problem
pres.addSection({ title: 'Problem and data' });
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Problem and data' });
s.addText('Far more data than downlink', { placeholder: 'title' });
stat(s, 0.5, 1.1, 2.85, '≈ 80 GB', 'of images produced per day', 'produced');
stat(s, 3.575, 1.1, 2.85, '≈ 6 GB', `can be sent in ${V.contact} min of ground contact per day`, 'downlink');
stat(s, 6.65, 1.1, 2.85, '35 min', 'of eclipse every 94-min orbit: no solar power', 'eclipse');
s.addText('Every 10 seconds, for every image, within battery, heat, memory and contact limits:', { x: 0.5, y: 2.5, w: 9, h: 0.35, fontSize: 14, color: 'C5CDE0', margin: 0, isTextBox: true, objectName: 'question' });
[['Process', 'onboard AI: 50 MB → 1.5 MB; costs energy and heat'], ['Keep', 'store for later; costs memory'], ['Transmit', 'during a ground pass'], ['Offload', 'laser link to a neighbour in sunlight']].forEach((a, i) => {
  const x = 0.5 + i * 2.3; card(s, x, 3.0, 2.15, 1.55, a[0] + ' card');
  s.addText(a[0], { x: x + 0.16, y: 3.12, w: 1.9, h: 0.4, fontSize: 17, bold: true, color: i === 0 ? '7DB6F5' : INK, margin: 0, isTextBox: true, objectName: a[0] });
  s.addText(a[1], { x: x + 0.16, y: 3.55, w: 1.85, h: 0.9, fontSize: 11.5, color: 'B3BDD3', margin: 0, valign: 'top', isTextBox: true, objectName: a[0] + ' text' });
});
s.addNotes('Problem 1: process, keep, transmit or offload, under energy, thermal, storage and contact constraints.');

// 3 real data
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Problem and data' });
s.addText('Real orbit, real NASA data', { placeholder: 'title' });
richBullets(s, [
  ['Orbit: ', 'Φsat-2 (NORAD 60470) from its CelesTrak TLE, SGP4; RK4 + J2 cross-check within 25 km'],
  ['Ground stations: ', 'KSAT Svalbard and ASI Matera, 10° elevation mask'],
  ['Earth data: ', 'NASA GIBS, 20 days under the real track: VIIRS images, MODIS clouds, FIRMS fires, land mask'],
  ['57,600 real footprints: ', 'each simulated picture is the real scene Φsat-2 flew over at that moment'],
  ['Simulated: ', 'battery, thermal, GPU, radio; every assumption in one file'],
], 0.5, 1.15, 4.3, 3.8, 13, 'data bullets');
s.addImage({ path: A('../figures/dash_replay_dark.jpg'), x: 5.1, y: 1.2, w: 4.4, h: 2.63, objectName: 'replay screenshot' });

// 4 clouds
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Problem and data' });
s.addText('Clouds fool raw entropy', { placeholder: 'title' });
white(s, 0.5, 1.1, 4.4, 1.95, 'fig_entropy.png', 1340, 526, 'entropy chart');
white(s, 5.1, 1.1, 4.4, 1.95, 'fig_triage.png', 1316, 495, 'triage chart');
s.addText([
  { text: `Clouds are the most textured scenes and ${V.cloud} % of all scenes. Ranking by texture keeps ` },
  { text: `${V.tri['raw entropy']} %`, options: { bold: true, color: 'EE6A57' } },
  { text: ` of the value, worse than random (${V.tri.random} %). Texture × onboard land mask gives ` },
  { text: `${V.tri['E-LOTUS']} %`, options: { bold: true, color: '7DB6F5' } },
  { text: `, close to a perfect oracle (${V.tri.oracle} %).` }],
  { x: 0.5, y: 3.35, w: 9, h: 1.0, fontSize: 15, color: 'D3DAEA', margin: 0, valign: 'top', isTextBox: true, objectName: 'finding' });

// 5 architecture
pres.addSection({ title: 'Solution' });
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Solution' });
s.addText('System architecture', { placeholder: 'title' });
white(s, 0.5, 1.05, 9.0, 3.95, 'arch.png', 3080, 1349, 'architecture diagram');

// 6 how it decides
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Solution' });
s.addText('How E-LOTUS decides, every 10 seconds', { placeholder: 'title' });
[['1', 'Value', 'texture × onboard land mask, × 4 for fire alerts', 'p·(0.1+0.9·land)·(H/8)³'],
 ['2', 'Score', 'growth of 3 debts (memory, battery, heat) minus V × value, per second', '(ΔL − V·U) / τ'],
 ['3', 'Safety guard', 'independent veto: survive the next eclipse, stay under 45 °C', 'fire alerts: up to 60 °C'],
 ['4', 'Explain', 'every decision logs a reason from onboard data', 'auditable by operators']].forEach((st, i) => {
  const x = 0.5 + i * 2.3; card(s, x, 1.1, 2.15, 2.5, 'step ' + st[0]);
  s.addText('Step ' + st[0], { x: x + 0.16, y: 1.2, w: 1.8, h: 0.28, fontSize: 11, bold: true, color: AMBER, margin: 0, isTextBox: true, objectName: 'step number ' + st[0] });
  s.addText(st[1], { x: x + 0.16, y: 1.48, w: 1.9, h: 0.4, fontSize: 17, bold: true, color: INK, margin: 0, isTextBox: true, objectName: 'step title ' + st[0] });
  s.addText(st[2], { x: x + 0.16, y: 1.92, w: 1.85, h: 1.05, fontSize: 11.5, color: 'B3BDD3', margin: 0, valign: 'top', isTextBox: true, objectName: 'step text ' + st[0] });
  s.addText(st[3], { x: x + 0.16, y: 3.1, w: 1.85, h: 0.35, fontSize: 10.5, color: '7DB6F5', margin: 0, isTextBox: true, objectName: 'step formula ' + st[0] });
});
s.addText('“Process now: est. value 0.68 (optical H 7.5, land 79 %). 20 MB raw → 0.6 MB product, next pass in 476 min; battery 69 Wh after (floor 20), 9.3 °C.”',
  { x: 0.5, y: 3.85, w: 9, h: 0.6, fontSize: 12, italic: true, color: 'D3DAEA', margin: 0, isTextBox: true, objectName: 'example decision' });
s.addText('Drift-plus-penalty from Lyapunov optimisation, used as a principled scoring rule; performance is measured, not claimed as proven.',
  { x: 0.5, y: 4.6, w: 9, h: 0.3, fontSize: 10, color: '8E9AB8', margin: 0, isTextBox: true, objectName: 'caveat' });

// 7 demo
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Solution' });
s.addText('Live demo', { placeholder: 'title' });
s.addImage({ path: A('../figures/dash_bench_light.jpg'), x: 0.5, y: 1.15, w: 4.6, h: 2.75, objectName: 'dashboard benchmark screenshot' });
richBullets(s, [
  ['Mission-control dashboard: ', '3D Earth with the real orbit, 80 what-if orbits, 270 pre-computed missions, one offline file'],
  ['Raspberry Pi: ', 'the same flight code runs live, printing each decision, its reason and its compute time'],
  ['Reproducible: ', 'every number is regenerated by scripts from the benchmark'],
], 5.4, 1.2, 4.1, 3.5, 13, 'demo bullets');

// 8 results
pres.addSection({ title: 'Results' });
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Results' });
s.addText(`Results: ${V.el} % of the reachable value`, { placeholder: 'title' });
white(s, 0.5, 1.1, 5.4, 2.4, 'fig_value.png', 1445, 576, 'value chart');
stat(s, 6.15, 1.1, 3.35, `+${V.gain} pts`, `over tuned rules with the same information; better on ${V.wins}/${V.days} days`, 'gain');
stat(s, 6.15, 2.35, 3.35, `+${V.compgain} pts`, `more images delivered or triaged (${V.comp} % vs ${V.comprb} %)`, 'completion');
stat(s, 0.5, 3.75, 2.6, '0', `load-sheds or throttles; battery ≥ ${V.socmin} %`, 'safety');
stat(s, 3.3, 3.75, 2.6, `${V.lat} min`, `mean latency (rules: ${V.latrb} min)`, 'latency');
s.addText(`${V.days} real days, independent 24-h runs; mean ± 95 % CI. Greedy processing drains the battery to ${V.gpsoc} % and sheds the payload ${V.gpshed} % of the time.`,
  { x: 6.15, y: 3.75, w: 3.35, h: 1.15, fontSize: 11, color: 'B3BDD3', margin: 0, valign: 'top', isTextBox: true, objectName: 'results note' });

// 9 stress
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Results' });
s.addText('Stress tests: where we win and where we don’t', { placeholder: 'title' });
white(s, 0.5, 1.05, 5.6, 3.95, 'fig_stress.png', 1500, 860, 'stress chart');
richBullets(s, [
  [`Wins ${V.nwin}/8: `, 'weaker solar array, half the downlink, fire season, less storage; E-LOTUS wins every day'],
  ['Small battery: ', `the rules' fixed threshold hits the shutdown floor (${V.rbbatt} %); E-LOTUS adapts from the orbit (${V.elbatt} %)`],
  ['Losses 2/8: ', `slower GPU, weaker radiator; the rules only win by running above 45 °C for ${V.hot1}–${V.hot2} % of the day`],
], 6.35, 1.15, 3.15, 3.8, 12, 'stress bullets');

// 10 feasibility
pres.addSection({ title: 'Feasibility and plan' });
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Feasibility and plan' });
s.addText('Feasible on real hardware', { placeholder: 'title' });
stat(s, 0.5, 1.1, 2.85, `${V.pims.toFixed(2)} ms`, `median decision time (${V.hw})`, 'decision time');
stat(s, 3.575, 1.1, 2.85, `${V.picpu.toFixed(3)} %`, 'of one CPU core over a full real day', 'cpu');
stat(s, 6.65, 1.1, 2.85, '2 libraries', 'numpy and sgp4; no GPU, no training', 'deps');
s.addText('Every input already exists on a satellite:', { x: 0.5, y: 2.5, w: 9, h: 0.35, fontSize: 14, color: 'C5CDE0', margin: 0, isTextBox: true, objectName: 'inputs title' });
[['Battery and temperature', 'housekeeping sensors'], ['Pass schedule', 'computed on the ground, uplinked'], ['Land mask', 'static map, indexed by GNSS position'], ['Thumbnail entropy', `${V.pient} µs per image`]].forEach((a, i) => {
  const x = 0.5 + i * 2.3; card(s, x, 3.0, 2.15, 1.25, a[0] + ' card');
  s.addText(a[0], { x: x + 0.16, y: 3.1, w: 1.9, h: 0.55, fontSize: 14, bold: true, color: INK, margin: 0, valign: 'top', isTextBox: true, objectName: a[0] });
  s.addText(a[1], { x: x + 0.16, y: 3.65, w: 1.85, h: 0.5, fontSize: 11.5, color: 'B3BDD3', margin: 0, valign: 'top', isTextBox: true, objectName: a[0] + ' text' });
});
s.addText('Precedent: ESA’s Φsat-1 already discarded cloudy images onboard. KAIO flies the real orbit of its successor.', { x: 0.5, y: 4.5, w: 9, h: 0.3, fontSize: 11, color: '8E9AB8', margin: 0, isTextBox: true, objectName: 'precedent' });

// 11 roadmap
s = pres.addSlide({ masterName: 'KAIO_CONTENT', sectionTitle: 'Feasibility and plan' });
s.addText('Method and roadmap', { placeholder: 'title' });
s.addText('How we built it', { x: 0.5, y: 1.1, w: 4.2, h: 0.35, fontSize: 15, bold: true, color: MUTED, margin: 0, isTextBox: true, objectName: 'method title' });
s.addText(['Two Phase-2 prototypes merged into one tested package', 'Review found the old engine above 45 °C 10 % of the time; the safety guard fixed it',
  '18 automated tests, incl. “the engine never reads the ground truth”', '1,360 simulations: 8 scenarios × 6 strategies × 20 real days', 'Same code on a Raspberry Pi']
  .map((t, i, a) => ({ text: t, options: { bullet: { type: 'number' }, breakLine: i < a.length - 1, paraSpaceAfter: 8 } })),
  { x: 0.5, y: 1.55, w: 4.2, h: 3.3, fontSize: 13, color: 'D3DAEA', margin: 0, valign: 'top', isTextBox: true, objectName: 'method list' });
[['Done', 'engine, safety guard, real-data simulation, benchmark, dashboard, embedded run'], ['+3 mo', 'hardware-in-the-loop on a flight-like computer; imperfect forecasts'],
 ['+6 mo', 'onboard cloud-screening network replacing the static land map'], ['+12 mo', 'constellation coordination; CubeSat flight-test partnership']].forEach((r, i) => {
  const y = 1.1 + i * 0.95; card(s, 5.0, y, 4.5, 0.8, 'milestone ' + r[0]);
  s.addText(r[0], { x: 5.15, y: y + 0.12, w: 0.8, h: 0.55, fontSize: 14, bold: true, color: AMBER, margin: 0, valign: 'top', isTextBox: true, objectName: 'milestone time ' + i });
  s.addText(r[1], { x: 6.0, y: y + 0.12, w: 3.35, h: 0.6, fontSize: 11.5, color: 'D3DAEA', margin: 0, valign: 'top', isTextBox: true, objectName: 'milestone text ' + i });
});

// 12 close
pres.addSection({ title: 'Close' });
s = pres.addSlide({ masterName: 'KAIO_COVER', sectionTitle: 'Close' });
s.addText('KAIO decides which images deserve the downlink, explains why, and never breaks the spacecraft to do it.', { x: 0.6, y: 0.9, w: 8.6, h: 1.7, fontSize: 30, bold: true, color: INK, margin: 0, valign: 'top', isTextBox: true, objectName: 'closing line' });
stat(s, 0.6, 2.9, 2.75, `${V.el} %`, 'of the reachable value', 'close value');
stat(s, 3.6, 2.9, 2.75, `${V.wins}/${V.days}`, 'days better than tuned rules', 'close days');
stat(s, 6.6, 2.9, 2.75, '0', 'load-sheds or throttles', 'close safety');
s.addText(`Thank you · questions welcome · ${V.repo}`, { x: 0.6, y: 4.5, w: 8.6, h: 0.3, fontSize: 13, color: '9AA6C2', margin: 0, isTextBox: true, objectName: 'thanks' });

(async () => {
  const out = path.join(__dirname, 'KAIO_Pitch.pptx');
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log('wrote', out);
})();
