/* ═══════════════════════════════════════════════════════════════════════
   Fridge Manager — Landing 3D Fridge + Easter Egg Car Game
   ═══════════════════════════════════════════════════════════════════════ */

// ── REVEAL APP SHELL ──────────────────────────────────────────────────
function revealApp() {
  const landing  = document.getElementById('landing-screen');
  const appShell = document.getElementById('app-shell');

  landing.classList.add('landing-exit');

  setTimeout(() => {
    landing.style.display = 'none';
    appShell.style.display = 'block';
    appShell.style.opacity = '0';
    appShell.style.transform = 'scale(0.97)';
    appShell.style.transition = 'opacity 0.7s ease, transform 0.7s ease';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        appShell.style.opacity = '1';
        appShell.style.transform = 'scale(1)';
      });
    });
    // Stagger tab buttons in
    document.querySelectorAll('.tab-btn').forEach((btn, i) => {
      btn.style.opacity = '0';
      btn.style.transform = 'translateY(30px)';
      setTimeout(() => {
        btn.style.transition = 'opacity 0.5s ease, transform 0.5s cubic-bezier(.22,1,.36,1)';
        btn.style.opacity = '1';
        btn.style.transform = 'translateY(0)';
      }, 100 + i * 80);
    });
  }, 700);
}

// ── 3D FRIDGE (Three.js) ──────────────────────────────────────────────
function initHero3D() {
  const canvas = document.getElementById('hero-3d-canvas');
  if (!canvas) return;

  // Read dimensions from the parent container (canvas offsetWidth=0 before layout)
  const wrap = canvas.parentElement;
  const W = wrap ? wrap.offsetWidth  : Math.min(520, window.innerWidth  * 0.85);
  const H = wrap ? wrap.offsetHeight : Math.min(580, window.innerHeight * 0.72);

  const scene    = new THREE.Scene();
  const camera   = new THREE.PerspectiveCamera(42, W / H, 0.1, 100);
  camera.position.set(0, 0.3, 6.2);

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  // false = don't set canvas CSS size (let CSS width:100%/height:100% handle it)
  renderer.setSize(W, H, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);

  // ── Materials ─────────────────────────────────────────────────────
  const bodyMat    = new THREE.MeshLambertMaterial({ color: 0x04020c });
  const doorMat    = new THREE.MeshLambertMaterial({ color: 0x060318 });
  const cyanLine   = new THREE.LineBasicMaterial({ color: 0x00f2ff });
  const magLine    = new THREE.LineBasicMaterial({ color: 0xff00ff });
  const handleMat  = new THREE.MeshLambertMaterial({ color: 0x00f2ff, emissive: 0x003366 });
  const shelfMat   = new THREE.MeshLambertMaterial({ color: 0x112244, emissive: 0x001133 });
  const interiorMat= new THREE.MeshLambertMaterial({ color: 0x001a33, emissive: 0x001133 });

  // ── Fridge group ──────────────────────────────────────────────────
  const fridgeGroup = new THREE.Group();

  // Body
  const bodyGeo = new THREE.BoxGeometry(1.6, 2.9, 1.0);
  fridgeGroup.add(new THREE.Mesh(bodyGeo, bodyMat));
  fridgeGroup.add(new THREE.LineSegments(new THREE.EdgesGeometry(bodyGeo), cyanLine.clone()));

  // Interior back panel (visible when door opens)
  const intGeo  = new THREE.BoxGeometry(1.52, 2.82, 0.12);
  const intMesh = new THREE.Mesh(intGeo, interiorMat);
  intMesh.position.set(0, 0, -0.42);
  fridgeGroup.add(intMesh);

  // Shelves inside
  [-0.55, 0.0, 0.55].forEach(y => {
    const sm = new THREE.Mesh(new THREE.BoxGeometry(1.46, 0.04, 0.9), shelfMat);
    sm.position.set(0, y, 0);
    fridgeGroup.add(sm);
  });

  // Divider strip between main/freezer
  const divMesh = new THREE.Mesh(
    new THREE.BoxGeometry(1.62, 0.05, 1.02),
    new THREE.MeshLambertMaterial({ color: 0x00f2ff, emissive: 0x003344 })
  );
  divMesh.position.y = 0.55;
  fridgeGroup.add(divMesh);

  // Interior light (starts off, brightens when door opens)
  const intLight = new THREE.PointLight(0x88ccff, 0, 4);
  intLight.position.set(0, 0, 0);
  fridgeGroup.add(intLight);

  // ── MAIN DOOR PIVOT (hinge at left-front edge) ────────────────────
  // Main section: y from -1.45 to 0.525, center y = -0.4625
  const mainDoorPivot = new THREE.Group();
  mainDoorPivot.position.set(-0.8, -0.4625, 0.545);
  fridgeGroup.add(mainDoorPivot);

  const mainDoorGeo = new THREE.BoxGeometry(1.6, 2.0, 0.09);
  const mainDoorMesh = new THREE.Mesh(mainDoorGeo, doorMat);
  mainDoorMesh.position.set(0.8, 0, 0);
  mainDoorPivot.add(mainDoorMesh);
  const mainDoorEdge = new THREE.LineSegments(new THREE.EdgesGeometry(mainDoorGeo), magLine.clone());
  mainDoorEdge.position.copy(mainDoorMesh.position);
  mainDoorPivot.add(mainDoorEdge);

  // Main handle
  const mHandle = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.7, 8), handleMat);
  mHandle.rotation.z = Math.PI / 2;
  mHandle.position.set(1.45, 0, 0.06);
  mainDoorPivot.add(mHandle);

  // ── FREEZER DOOR PIVOT ────────────────────────────────────────────
  // Freezer: y from 0.575 to 1.45, center y = 1.0125
  const fzDoorPivot = new THREE.Group();
  fzDoorPivot.position.set(-0.8, 1.0125, 0.505);
  fridgeGroup.add(fzDoorPivot);

  const fzDoorGeo  = new THREE.BoxGeometry(1.6, 0.87, 0.09);
  const fzDoorMesh = new THREE.Mesh(fzDoorGeo, doorMat.clone());
  fzDoorMesh.position.set(0.8, 0, 0);
  fzDoorPivot.add(fzDoorMesh);
  const fzDoorEdge = new THREE.LineSegments(new THREE.EdgesGeometry(fzDoorGeo), cyanLine.clone());
  fzDoorEdge.position.copy(fzDoorMesh.position);
  fzDoorPivot.add(fzDoorEdge);

  // Freezer handle
  const fHandle = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.55, 8),
    new THREE.MeshLambertMaterial({ color: 0xff00ff, emissive: 0x330033 }));
  fHandle.rotation.z = Math.PI / 2;
  fHandle.position.set(1.42, 0, 0.06);
  fzDoorPivot.add(fHandle);

  // ── Decorative floating shapes ────────────────────────────────────
  const floaters = [];

  function addFloater(geo, pos, solidCol, wireCol, rotSpd) {
    const grp = new THREE.Group();
    grp.add(new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: solidCol, transparent: true, opacity: 0.18 })));
    grp.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: wireCol })));
    grp.position.set(...pos);
    scene.add(grp);
    floaters.push({ g: grp, oy: pos[1], phase: Math.random() * Math.PI * 2, rx: rotSpd[0], ry: rotSpd[1], rz: rotSpd[2] || 0 });
    return grp;
  }

  // Icosahedra
  addFloater(new THREE.IcosahedronGeometry(0.24),  [-2.5,  0.6,  0.3], 0x00f2ff, 0x00f2ff, [0.018, 0.012]);
  addFloater(new THREE.IcosahedronGeometry(0.19),  [ 2.6, -0.5,  0.2], 0xff00ff, 0xff00ff, [-0.014, 0.016]);
  addFloater(new THREE.IcosahedronGeometry(0.15),  [-2.1, -1.3, -0.4], 0x7000ff, 0x7000ff, [0.02, -0.01]);
  addFloater(new THREE.IcosahedronGeometry(0.13),  [ 1.7,  1.8, -0.3], 0x00f2ff, 0xff00ff, [-0.012, 0.022]);

  // Octahedra
  addFloater(new THREE.OctahedronGeometry(0.22),   [ 2.3,  1.2, -0.2], 0x00f2ff, 0xff00ff, [-0.016, 0.018]);
  addFloater(new THREE.OctahedronGeometry(0.17),   [-2.9, -0.4,  0.1], 0xff00ff, 0x00f2ff, [0.012, 0.022]);
  addFloater(new THREE.OctahedronGeometry(0.14),   [ 2.0, -1.6,  0.3], 0x7000ff, 0x00f2ff, [0.02, -0.015]);

  // Tori
  addFloater(new THREE.TorusGeometry(0.24, 0.055, 8, 24), [-2.2,  1.6, -0.2], 0x7000ff, 0x00f2ff, [0.022, 0.01]);
  addFloater(new THREE.TorusGeometry(0.20, 0.045, 7, 20), [ 2.8,  0.7,  0.3], 0xff00ff, 0xff00ff, [-0.018, 0.014]);
  addFloater(new THREE.TorusGeometry(0.16, 0.04,  6, 16), [-1.9, -0.8, -0.5], 0x00f2ff, 0x7000ff, [0.015, -0.02]);

  // Tetrahedra
  addFloater(new THREE.TetrahedronGeometry(0.22),  [ 2.0, -1.1, -0.3], 0x00f2ff, 0xff2e63, [0.022, -0.018]);
  addFloater(new THREE.TetrahedronGeometry(0.18),  [-2.7,  1.3,  0.2], 0xff00ff, 0x7000ff, [-0.015, 0.02]);
  addFloater(new THREE.TetrahedronGeometry(0.14),  [ 1.6,  0.2,  0.6], 0x7000ff, 0x00f2ff, [0.018, 0.015]);

  // Cones
  addFloater(new THREE.ConeGeometry(0.13, 0.32, 6), [ 2.4, -1.5, -0.2], 0x00f2ff, 0x00f2ff, [0.01,  0.025]);
  addFloater(new THREE.ConeGeometry(0.11, 0.27, 5), [-1.8,  1.9,  0.1], 0xff00ff, 0xff00ff, [-0.02, 0.012]);
  addFloater(new THREE.ConeGeometry(0.10, 0.22, 4), [-2.4, -1.6,  0.4], 0x7000ff, 0x00f2ff, [0.016, -0.02]);

  // Dodecahedra
  addFloater(new THREE.DodecahedronGeometry(0.18), [ 3.0,  0.1,  0.0], 0xff00ff, 0x00f2ff, [0.013, 0.017]);
  addFloater(new THREE.DodecahedronGeometry(0.14), [-1.5, -1.9, -0.3], 0x00f2ff, 0xff00ff, [-0.017, -0.013]);

  // Boxes (rotated for diamond look)
  addFloater(new THREE.BoxGeometry(0.22, 0.22, 0.22), [ 2.7,  1.5,  0.1], 0x7000ff, 0xff00ff, [0.02, 0.02, 0.015]);
  addFloater(new THREE.BoxGeometry(0.18, 0.18, 0.18), [-2.3, -1.1,  0.5], 0x00f2ff, 0x00f2ff, [-0.018, 0.016, -0.01]);

  // ── Orbiting torus rings ──────────────────────────────────────────
  const orbitRing1 = new THREE.Mesh(
    new THREE.TorusGeometry(2.85, 0.022, 4, 90),
    new THREE.MeshBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.40 })
  );
  orbitRing1.rotation.x = Math.PI / 2.3;
  scene.add(orbitRing1);

  const orbitRing2 = new THREE.Mesh(
    new THREE.TorusGeometry(3.3, 0.016, 4, 90),
    new THREE.MeshBasicMaterial({ color: 0xff00ff, transparent: true, opacity: 0.28 })
  );
  orbitRing2.rotation.z = Math.PI / 3;
  orbitRing2.rotation.x = Math.PI / 4.5;
  scene.add(orbitRing2);

  const orbitRing3 = new THREE.Mesh(
    new THREE.TorusGeometry(2.5, 0.013, 4, 80),
    new THREE.MeshBasicMaterial({ color: 0x7000ff, transparent: true, opacity: 0.22 })
  );
  orbitRing3.rotation.y = Math.PI / 6;
  orbitRing3.rotation.z = Math.PI / 2.5;
  scene.add(orbitRing3);

  // ── Particle field ────────────────────────────────────────────────
  const PC = 160;
  const pPos = new Float32Array(PC * 3);
  const pCol = new Float32Array(PC * 3);
  const neonCols = [[0,0.95,1],[1,0,1],[0.44,0,1],[1,0.18,0.39]];
  for (let i = 0; i < PC; i++) {
    const r = 2.8 + Math.random() * 2.8;
    const theta = Math.random() * Math.PI * 2;
    const phi   = Math.acos(2 * Math.random() - 1);
    pPos[i*3]   = r * Math.sin(phi) * Math.cos(theta);
    pPos[i*3+1] = r * Math.cos(phi);
    pPos[i*3+2] = r * Math.sin(phi) * Math.sin(theta);
    const c = neonCols[Math.floor(Math.random() * neonCols.length)];
    pCol[i*3] = c[0]; pCol[i*3+1] = c[1]; pCol[i*3+2] = c[2];
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  pGeo.setAttribute('color',    new THREE.BufferAttribute(pCol, 3));
  const particles = new THREE.Points(pGeo,
    new THREE.PointsMaterial({ vertexColors: true, size: 0.045, transparent: true, opacity: 0.75 })
  );
  scene.add(particles);

  // ── Glowing mini-spheres ──────────────────────────────────────────
  [[-2.1, 0.0, 0.5, 0x00f2ff],[2.1, 1.4,-0.4, 0xff00ff],[-1.9,-1.5, 0.2, 0x7000ff],
   [ 2.5,-0.9, 0.4, 0x00f2ff],[-2.8, 0.9,-0.3, 0xff00ff]].forEach(([x,y,z,col]) => {
    const sm = new THREE.Mesh(
      new THREE.SphereGeometry(0.10, 8, 8),
      new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.85 })
    );
    sm.position.set(x, y, z);
    scene.add(sm);
    floaters.push({ g: sm, oy: y, phase: Math.random()*Math.PI*2, rx:0, ry:0.02, rz:0 });
  });

  scene.add(fridgeGroup);

  // ── Lights ────────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0x111122, 0.9));
  const cyanPt = new THREE.PointLight(0x00f2ff, 3, 14);
  cyanPt.position.set(3, 2, 5); scene.add(cyanPt);
  const magPt = new THREE.PointLight(0xff00ff, 2, 14);
  magPt.position.set(-3, -1, 4); scene.add(magPt);
  const purpPt = new THREE.PointLight(0x7000ff, 1.5, 8);
  purpPt.position.set(0, -3, 2); scene.add(purpPt);

  // ── Raycaster for click ───────────────────────────────────────────
  const raycaster = new THREE.Raycaster();
  const mouse     = new THREE.Vector2();
  let doorAnimating = false;
  let doorOpened    = false;

  const allMeshes = [];
  fridgeGroup.traverse(obj => { if (obj.isMesh) allMeshes.push(obj); });

  function onFridgeClick(e) {
    if (doorAnimating || doorOpened) return;
    const rect = canvas.getBoundingClientRect();
    const clientX = e.clientX ?? e.changedTouches?.[0]?.clientX;
    const clientY = e.clientY ?? e.changedTouches?.[0]?.clientY;
    if (clientX == null) return;
    mouse.x =  ((clientX - rect.left) / rect.width)  * 2 - 1;
    mouse.y = -((clientY - rect.top)  / rect.height)  * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    if (raycaster.intersectObjects(allMeshes).length > 0) {
      startDoorOpen();
    }
  }

  canvas.addEventListener('click',    onFridgeClick);
  canvas.addEventListener('touchend', onFridgeClick);

  // Show "tap" hint on hover
  canvas.style.cursor = 'pointer';

  // ── Door open animation ───────────────────────────────────────────
  function startDoorOpen() {
    doorAnimating = true;
    document.getElementById('landing-hint').style.opacity = '0';
    document.getElementById('landing-opening-msg').style.opacity = '1';

    const DURATION = 1800;
    const TARGET   = -1.32; // ~75 degrees
    const start    = performance.now();

    // Stop rotation, face forward smoothly
    isIdle = false;

    function animFrame(now) {
      const t    = Math.min((now - start) / DURATION, 1);
      const ease = 1 - Math.pow(1 - t, 3); // cubic ease-out

      mainDoorPivot.rotation.y = TARGET * ease;
      fzDoorPivot.rotation.y   = TARGET * ease * 0.85;
      intLight.intensity        = ease * 3.5;
      // Straighten fridge rotation to face user
      fridgeGroup.rotation.y   = fridgeGroup.rotation.y * (1 - ease * 0.08);

      if (t < 1) {
        requestAnimationFrame(animFrame);
      } else {
        doorOpened    = true;
        doorAnimating = false;
        setTimeout(revealApp, 500);
      }
    }
    requestAnimationFrame(animFrame);
  }

  // ── Main render loop ──────────────────────────────────────────────
  let t = 0;
  let isIdle = true;

  function animate() {
    requestAnimationFrame(animate);
    t += 0.013;

    if (isIdle) {
      fridgeGroup.rotation.y = Math.sin(t * 0.38) * 0.42;
    }
    fridgeGroup.position.y = Math.sin(t * 0.65) * 0.18;
    cyanPt.intensity = 2.8 + Math.sin(t * 2.0) * 0.5;
    magPt.intensity  = 1.8 + Math.sin(t * 1.6 + 1) * 0.4;

    // Animate floaters
    floaters.forEach(fl => {
      fl.g.position.y = fl.oy + Math.sin(t + fl.phase) * 0.13;
      fl.g.rotation.x += fl.rx || 0;
      fl.g.rotation.y += fl.ry || 0;
      fl.g.rotation.z += fl.rz || 0;
    });

    // Spin orbit rings
    orbitRing1.rotation.z += 0.0045;
    orbitRing2.rotation.y += 0.003;
    orbitRing3.rotation.x += 0.0035;

    // Drift particles
    particles.rotation.y += 0.0018;
    particles.rotation.x += 0.0008;

    renderer.render(scene, camera);
  }
  animate();

  // Resize handler
  window.addEventListener('resize', () => {
    const wrap = canvas.parentElement;
    const nw = wrap ? wrap.offsetWidth  : Math.min(520, window.innerWidth  * 0.85);
    const nh = wrap ? wrap.offsetHeight : Math.min(580, window.innerHeight * 0.72);
    camera.aspect = nw / nh;
    camera.updateProjectionMatrix();
    renderer.setSize(nw, nh, false);
  });
}

// ── HOLD TRIGGER (for easter egg game, in app header) ────────────────
let holdTimer = null;

function initHoldTrigger() {
  const trigger = document.getElementById('game-trigger');
  const ring    = document.getElementById('hold-progress-ring');
  if (!trigger || !ring) return;

  const circ = 2 * Math.PI * 22;
  const setRing = pct => {
    ring.style.strokeDashoffset = circ - circ * pct;
    ring.style.opacity = pct > 0 ? '1' : '0';
  };

  const startHold = () => {
    if (holdTimer) return;
    let elapsed = 0;
    holdTimer = setInterval(() => {
      elapsed += 50;
      setRing(elapsed / 3000);
      if (elapsed >= 3000) {
        clearInterval(holdTimer); holdTimer = null;
        setRing(0);
        triggerMilkSplash();
      }
    }, 50);
  };
  const cancelHold = () => {
    if (holdTimer) { clearInterval(holdTimer); holdTimer = null; }
    setRing(0);
  };

  trigger.addEventListener('mousedown',   startHold);
  trigger.addEventListener('touchstart',  startHold,  { passive: true });
  trigger.addEventListener('mouseup',     cancelHold);
  trigger.addEventListener('mouseleave',  cancelHold);
  trigger.addEventListener('touchend',    cancelHold);
  trigger.addEventListener('touchcancel', cancelHold);
}

// ── MILK SPLASH ───────────────────────────────────────────────────────
function triggerMilkSplash() {
  const overlay      = document.getElementById('game-overlay');
  const splashCanvas = document.getElementById('splash-canvas');
  overlay.style.display = 'flex';
  splashCanvas.style.display = 'block';

  const W = splashCanvas.width  = window.innerWidth;
  const H = splashCanvas.height = window.innerHeight;
  const ctx = splashCanvas.getContext('2d');

  const blobs = Array.from({ length: 32 }, (_, i) => {
    const angle = (i / 32) * Math.PI * 2 + Math.random() * 0.4;
    const spd   = 7 + Math.random() * 15;
    return { x: W/2, y: H/2, vx: Math.cos(angle)*spd, vy: Math.sin(angle)*spd, r: 22 + Math.random()*30 };
  });

  let frame = 0;
  const draw = () => {
    const p = frame / 100;
    ctx.fillStyle = `rgba(255,255,255,${0.07 + p*0.12})`;
    ctx.fillRect(0, 0, W, H);
    blobs.forEach(b => {
      b.x += b.vx; b.y += b.vy; b.vx *= 0.965; b.vy *= 0.965; b.r += 3.5 + p*5;
      const g = ctx.createRadialGradient(b.x,b.y,0,b.x,b.y,b.r);
      g.addColorStop(0, 'rgba(255,255,255,1)');
      g.addColorStop(1, 'rgba(200,230,255,0.3)');
      ctx.beginPath(); ctx.arc(b.x,b.y,b.r,0,Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
    });
    frame++;
    if (frame < 100) requestAnimationFrame(draw);
    else {
      ctx.fillStyle = '#fff'; ctx.fillRect(0,0,W,H);
      setTimeout(() => { splashCanvas.style.display='none'; startCarGame(); }, 350);
    }
  };
  draw();
}

// ── CAR GAME ──────────────────────────────────────────────────────────
const ILLNESSES = [
  'Acute Food Poisoning','Salmonella Infection','E. Coli Contamination',
  'Listeriosis','Botulism','Norovirus Gastroenteritis',
  'Campylobacteriosis','Staphylococcal Toxaemia','Hepatitis A',
  'Cryptosporidiosis','Bacillus Cereus Syndrome'
];

let carCleanup = null;

function startCarGame() {
  const screen = document.getElementById('car-game-screen');
  screen.style.display = 'flex';

  const canvas = document.getElementById('car-canvas');
  // Explicitly match buffer AND CSS size so the car never draws off-screen
  const W = canvas.width  = window.innerWidth;
  const H = canvas.height = window.innerHeight;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');

  const ROAD_W = Math.min(440, W * 0.68);
  const ROAD_X = (W - ROAD_W) / 2;
  const LANES  = 3;
  const LW     = ROAD_W / LANES;

  let lane = 1, score = 0, speed = 4, lineOff = 0;
  let playerX  = ROAD_X + LW * lane + LW/2 - 23;
  let targetX  = playerX;
  let enemies  = [], spawnT = 0, running = true;

  const onKey = e => {
    if (!running) return;
    if (e.code === 'ArrowLeft'  && lane > 0)        { lane--; targetX = ROAD_X+LW*lane+LW/2-23; }
    if (e.code === 'ArrowRight' && lane < LANES-1)  { lane++; targetX = ROAD_X+LW*lane+LW/2-23; }
  };
  document.addEventListener('keydown', onKey);

  let tX = 0;
  canvas.addEventListener('touchstart', e => { tX = e.touches[0].clientX; }, {passive:true});
  canvas.addEventListener('touchend',   e => {
    const dx = e.changedTouches[0].clientX - tX;
    if (Math.abs(dx) > 30) {
      if (dx < 0 && lane > 0)       { lane--; targetX = ROAD_X+LW*lane+LW/2-23; }
      if (dx > 0 && lane < LANES-1) { lane++; targetX = ROAD_X+LW*lane+LW/2-23; }
    }
  });

  // Proportional Y — always 18% from the bottom, never off-canvas
  const PW = 46, PH = 80, PY = Math.floor(H * 0.80) - PH;

  function loop() {
    if (!running) return;
    lineOff += speed * 1.5; score++; speed = Math.min(4 + score/600, 13);
    playerX += (targetX - playerX) * 0.18;

    spawnT++;
    if (spawnT >= Math.max(55 - Math.floor(score/150), 20)) {
      const el = Math.floor(Math.random()*LANES);
      enemies.push({ x: ROAD_X+LW*el+LW/2-23, y:-90, c: ['#ff2e63','#ff9900','#ff00ff'][Math.floor(Math.random()*3)] });
      spawnT = 0;
    }
    enemies.forEach(e => { e.y += speed*2; });
    enemies = enemies.filter(e => e.y < H+100);

    // Draw
    ctx.fillStyle='#070712'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#0d0d22'; ctx.fillRect(ROAD_X,0,ROAD_W,H);
    ctx.shadowColor='#00f2ff'; ctx.shadowBlur=20;
    ctx.strokeStyle='#00f2ff'; ctx.lineWidth=3;
    ctx.beginPath(); ctx.moveTo(ROAD_X,0); ctx.lineTo(ROAD_X,H); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(ROAD_X+ROAD_W,0); ctx.lineTo(ROAD_X+ROAD_W,H); ctx.stroke();
    ctx.shadowBlur=0;
    ctx.setLineDash([38,28]); ctx.strokeStyle='rgba(255,255,255,0.22)'; ctx.lineWidth=2;
    for (let l=1;l<LANES;l++){
      const lx=ROAD_X+LW*l;
      ctx.beginPath(); ctx.moveTo(lx,-(lineOff%66)); ctx.lineTo(lx,H); ctx.stroke();
    }
    ctx.setLineDash([]);

    const drawCar=(x,y,w,h,col,pl)=>{
      ctx.shadowColor=col; ctx.shadowBlur=pl?22:10;
      ctx.fillStyle=col; ctx.beginPath(); ctx.roundRect(x,y+h*.1,w,h*.8,5); ctx.fill();
      ctx.fillStyle=pl?'#001133':'#1a0011';
      ctx.beginPath(); ctx.roundRect(x+w*.15,y+h*.22,w*.7,h*.44,4); ctx.fill();
      const lc=pl?'#00f2ff':'#ff2200'; ctx.fillStyle=lc; ctx.shadowColor=lc; ctx.shadowBlur=8;
      [[x+3,y+(pl?h*.08:h*.84)],[x+w-11,y+(pl?h*.08:h*.84)]].forEach(([lx,ly])=>ctx.fillRect(lx,ly,8,5));
      ctx.shadowBlur=0;
    };

    enemies.forEach(e=>drawCar(e.x,e.y,46,80,e.c,false));
    drawCar(playerX,PY,PW,PH,'#00f2ff',true);

    ctx.fillStyle='rgba(0,0,0,0.55)'; ctx.fillRect(0,0,W,52);
    ctx.font='bold 22px "Bebas Neue",sans-serif';
    ctx.fillStyle='#00f2ff'; ctx.textAlign='left'; ctx.fillText(`SCORE: ${score}`,20,34);
    ctx.fillStyle='#ff00ff'; ctx.textAlign='right'; ctx.fillText(`SPEED: ${speed.toFixed(1)}x`,W-20,34);
    document.getElementById('car-score').textContent = score;

    // Collision
    const hit = enemies.some(e=>playerX<e.x+46&&playerX+PW>e.x&&PY<e.y+80&&PY+PH>e.y);
    if (hit) { running=false; document.removeEventListener('keydown',onKey); showDeath(score); return; }

    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  carCleanup = () => { running=false; document.removeEventListener('keydown',onKey); };
}

function showDeath(score) {
  document.getElementById('car-game-screen').style.display='none';
  const ds=document.getElementById('death-screen');
  ds.style.display='flex';
  document.getElementById('death-illness').textContent = ILLNESSES[Math.floor(Math.random()*ILLNESSES.length)].toUpperCase();
  document.getElementById('death-score-val').textContent = score;
  let f=0; const fi=setInterval(()=>{ ds.style.opacity=Math.random()>.3?'1':'0.8'; if(++f>12){clearInterval(fi);ds.style.opacity='1';} },80);
}

function continueGame() {
  document.getElementById('death-screen').style.display='none';
  startCarGame();
}

function exitCarGame() {
  if(carCleanup) carCleanup();
  ['car-game-screen','death-screen','splash-canvas'].forEach(id=>{ const el=document.getElementById(id); if(el) el.style.display='none'; });
  document.getElementById('game-overlay').style.display='none';
}

// ── INIT ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const load3D = () => {
    // Double rAF ensures the browser has computed layout before we read dimensions
    requestAnimationFrame(() => requestAnimationFrame(() => initHero3D()));
  };

  if (typeof THREE !== 'undefined') {
    load3D();
  } else {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js';
    s.onload = load3D;
    document.head.appendChild(s);
  }
  // Hold trigger init (app-shell is hidden but event listeners still attach)
  initHoldTrigger();
});
