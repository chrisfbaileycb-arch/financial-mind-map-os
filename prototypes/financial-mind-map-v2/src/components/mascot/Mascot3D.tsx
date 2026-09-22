// FinancialMindMap — 3D mascot "Chip" (React + three.js)
// Idle: breathes & blinks. Thinking: 💰📈🪙💳🏦💵📊 orbit over its head.
// Answer ready: raises its hand and SNAPS its fingers — spark burst + scatter.
import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import * as THREE from 'three';

export interface MascotHandle {
  think: () => void;
  snap: () => void;
}

const ICONS = ['💰', '📈', '🪙', '💳', '🏦', '💵', '📊', '🪙'];

function emojiTexture(ch: string): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  g.font = '96px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(ch, 64, 70);
  const tx = new THREE.CanvasTexture(c);
  tx.needsUpdate = true;
  return tx;
}

function mat(color: number, rough = 0.4, metal = 0.05): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });
}

export const Mascot3D = forwardRef<MascotHandle, { className?: string }>(function Mascot3D(_props, ref) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<'idle' | 'thinking' | 'snap'>('idle');
  const apiRef = useRef<{
    setSnap: () => void;
  } | null>(null);

  useImperativeHandle(ref, () => ({
    think: () => { stateRef.current = 'thinking'; },
    snap: () => { stateRef.current = 'snap'; apiRef.current?.setSnap(); },
  }));

  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      return; // no WebGL — the CSS fallback chip in the parent stays visible
    }
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 50);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    el.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';

    scene.add(new THREE.HemisphereLight(0xd8ccff, 0x2a1e5e, 1.0));
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(3, 5, 4);
    scene.add(key);
    const rim = new THREE.PointLight(0x3d9eff, 0.8, 20);
    rim.position.set(-3, 2, -2);
    scene.add(rim);

    const clock = new THREE.Clock();

    /* ---- build Chip ---- */
    const root = new THREE.Group();
    const body = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 32), mat(0x3d9eff, 0.45));
    body.scale.set(1, 1.08, 0.88);
    body.position.y = 0.85;
    root.add(body);

    const belly = new THREE.Mesh(new THREE.SphereGeometry(0.62, 32, 24), mat(0xe8f3ff, 0.6));
    belly.scale.set(1, 1.05, 0.55);
    belly.position.set(0, 0.7, 0.62);
    root.add(belly);

    const head = new THREE.Group();
    head.position.y = 2.0;
    root.add(head);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.78, 40, 32), mat(0x59b0ff, 0.4));
    skull.scale.set(1, 0.94, 0.9);
    head.add(skull);

    [-1, 1].forEach(s => {
      const tuft = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.42, 12), mat(0x2f7fd6));
      tuft.position.set(0.42 * s, 0.72, 0);
      tuft.rotation.z = -0.35 * s;
      head.add(tuft);
    });

    const eyes: { group: THREE.Group; pupil: THREE.Mesh }[] = [];
    [-1, 1].forEach(sx => {
      const e = new THREE.Group();
      const white = new THREE.Mesh(new THREE.SphereGeometry(0.24, 24, 20), mat(0xffffff, 0.25));
      white.scale.z = 0.6;
      const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 14), mat(0x0b1b33, 0.2));
      pupil.position.z = 0.16;
      const shine = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), mat(0xffffff, 0.1));
      shine.position.set(0.05, 0.06, 0.23);
      e.add(white, pupil, shine);
      e.position.set(0.3 * sx, 0.1, 0.62);
      eyes.push({ group: e, pupil });
      head.add(e);
    });

    const beak = new THREE.Mesh(new THREE.ConeGeometry(0.13, 0.3, 10), mat(0xfde047, 0.35));
    beak.rotation.x = Math.PI / 2;
    beak.position.set(0, -0.18, 0.72);
    head.add(beak);

    // gold coin antenna — spins while thinking
    const coin = new THREE.Group();
    coin.position.set(0, 1.0, 0);
    head.add(coin);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.3, 8), mat(0xfde047, 0.3, 0.8));
    coin.add(stem);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.05, 28), mat(0xfacc15, 0.25, 0.85));
    disc.rotation.x = Math.PI / 2;
    disc.position.y = 0.3;
    coin.add(disc);

    function makeArm(sx: number) {
      const arm = new THREE.Group();
      const upper = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, 0.5, 6, 12), mat(0x2f7fd6));
      upper.position.y = -0.32;
      arm.add(upper);
      const hand = new THREE.Group();
      hand.position.y = -0.68;
      arm.add(hand);
      hand.add(new THREE.Mesh(new THREE.SphereGeometry(0.17, 18, 14), mat(0x59b0ff, 0.4)));
      const finger = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.16, 4, 8), mat(0x8fd0ff, 0.4));
      finger.position.set(0.02, 0.16, 0.05);
      finger.rotation.x = -0.5;
      hand.add(finger);
      const thumb = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.14, 4, 8), mat(0x8fd0ff, 0.4));
      thumb.position.set(-0.1, 0.1, 0.06);
      thumb.rotation.set(-0.4, 0, 0.9);
      hand.add(thumb);
      arm.position.set(0.92 * sx, 1.25, 0.1);
      arm.rotation.z = -0.5 * sx;
      return { arm, hand, finger, thumb };
    }
    const AR = makeArm(1);
    const AL = makeArm(-1);
    root.add(AR.arm, AL.arm);

    [-1, 1].forEach(s => {
      const foot = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 12), mat(0xfde047, 0.4));
      foot.scale.set(1, 0.5, 1.3);
      foot.position.set(0.35 * s, 0.02, 0.25);
      root.add(foot);
    });

    const shadow = new THREE.Mesh(
      new THREE.CircleGeometry(1.05, 32),
      new THREE.MeshBasicMaterial({ color: 0x02060f, transparent: true, opacity: 0.25 }),
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = -0.02;
    root.add(shadow);
    scene.add(root);

    /* ---- orbiting money symbols ---- */
    const icons: THREE.Sprite[] = ICONS.map((ch, i) => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: emojiTexture(ch), transparent: true, depthWrite: false }));
      sp.scale.set(0.5, 0.5, 0.5);
      sp.userData = { i, angle: (i / ICONS.length) * Math.PI * 2 };
      sp.visible = false;
      scene.add(sp);
      return sp;
    });

    /* ---- spark burst ---- */
    const sparks: THREE.Sprite[] = [];
    function burst(from: THREE.Vector3) {
      for (let i = 0; i < 22; i++) {
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({
          map: emojiTexture(i % 3 === 0 ? '✨' : i % 3 === 1 ? '⭐' : '🪙'),
          transparent: true, depthWrite: false,
        }));
        sp.scale.set(0.26, 0.26, 0.26);
        sp.position.copy(from);
        const a = Math.random() * Math.PI * 2;
        const v = 0.6 + Math.random() * 1.8;
        sp.userData = { vx: Math.cos(a) * v, vy: 0.8 + Math.random() * 1.6, vz: Math.sin(a) * v, life: 1 };
        sparks.push(sp);
        scene.add(sp);
      }
    }

    /* ---- animation state ---- */
    let tSnap = -1;
    let tBlink = 0;
    let nextBlink = 2.5;
    let blinkT = -1;
    let snapped = false;
    const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);

    apiRef.current = {
      setSnap: () => {
        tSnap = 0;
        snapped = false;
        AR.thumb.rotation.set(-0.4, 0, 0.9);
        AR.finger.rotation.x = -0.5;
      },
    };

    function resize() {
      const w = el?.clientWidth ?? 0;
      const h = el?.clientHeight ?? 0;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      camera.position.set(0, 1.7, w < 420 ? 8.4 : w < 720 ? 7.4 : 6.6);
      camera.lookAt(0, 1.55, 0);
    }
    resize();
    window.addEventListener('resize', resize);

    let raf = 0;
    const T1 = 0.34, T2 = 0.42, T3 = 1.05;
    function animate() {
      raf = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      const t = clock.elapsedTime;
      const state = stateRef.current;

      root.position.y = Math.sin(t * 1.6) * 0.05;
      root.rotation.y = Math.sin(t * 0.7) * 0.12;
      head.rotation.z = Math.sin(t * 0.9) * 0.03;

      // blink
      tBlink += dt;
      if (blinkT >= 0) {
        blinkT += dt;
        const s = blinkT < 0.08 ? 1 - blinkT / 0.08 : blinkT < 0.16 ? (blinkT - 0.08) / 0.08 : 1;
        eyes.forEach(e => { e.group.scale.y = Math.max(0.08, s); });
        if (blinkT > 0.18) { blinkT = -1; eyes.forEach(e => { e.group.scale.y = 1; }); }
      } else if (tBlink > nextBlink) { blinkT = 0; tBlink = 0; nextBlink = 2.2 + Math.random() * 3; }

      if (state === 'thinking') {
        coin.rotation.y += dt * 9;
        head.rotation.x = -0.12 + Math.sin(t * 2) * 0.05;
        eyes.forEach(e => { e.pupil.position.y = 0.05; });
        body.scale.y = 1.08 + Math.sin(t * 3) * 0.02;
        icons.forEach((sp, i) => {
          const u = sp.userData as { angle: number };
          sp.visible = true;
          u.angle += dt * 1.5;
          const r = 1.25 + Math.sin(t * 1.3 + i) * 0.08;
          sp.position.set(Math.cos(u.angle) * r, 3.35 + Math.sin(t * 2.2 + i) * 0.14, Math.sin(u.angle) * r * 0.55 + 0.2);
          const k = 0.5 + Math.sin(t * 3 + i) * 0.05;
          sp.scale.set(k, k, k);
          (sp.material as THREE.SpriteMaterial).opacity = 1;
        });
      } else if (state === 'snap' && tSnap >= 0) {
        tSnap += dt;
        coin.rotation.y += dt * 2;
        head.rotation.x *= 0.9;
        if (tSnap < T1) {
          const k = easeOut(tSnap / T1);
          AR.arm.rotation.z = -0.5 + k * 2.0;
          AR.arm.rotation.x = k * -0.25;
          AR.arm.position.y = 1.25 + k * 0.75;
          body.scale.set(1 - k * 0.04, 1.08 + k * 0.05, 0.88);
        } else if (tSnap < T2) {
          const u = (tSnap - T1) / (T2 - T1);
          AR.thumb.rotation.z = 0.9 - u * 1.0;
          AR.finger.rotation.x = -0.5 + u * 0.55;
          if (u > 0.7 && !snapped) {
            snapped = true;
            const from = new THREE.Vector3();
            AR.hand.getWorldPosition(from);
            burst(from);
            body.scale.set(1.1, 1.0, 0.9);
          }
        } else if (tSnap < T3) {
          const k2 = easeOut((tSnap - T2) / (T3 - T2));
          AR.arm.rotation.z = 1.5 - k2 * 2.0;
          AR.arm.rotation.x = -0.25 + k2 * 0.25;
          AR.arm.position.y = 2.0 - k2 * 0.75;
          body.scale.lerp(new THREE.Vector3(1, 1.08, 0.88), 0.15);
          AR.thumb.rotation.set(-0.4, 0, 0.9);
          AR.finger.rotation.x = -0.5;
          icons.forEach(sp => {
            const m = sp.material as THREE.SpriteMaterial;
            if (m.opacity > 0) {
              sp.position.x *= 1.06;
              sp.position.y += 0.06;
              sp.position.z *= 1.06;
              m.opacity -= dt * 2.2;
              if (m.opacity <= 0) sp.visible = false;
            }
          });
        } else {
          stateRef.current = 'idle';
          tSnap = -1;
          AR.arm.rotation.set(0, 0, -0.5);
          AR.arm.position.set(0.92, 1.25, 0.1);
          body.scale.set(1, 1.08, 0.88);
          icons.forEach(sp => { sp.visible = false; (sp.material as THREE.SpriteMaterial).opacity = 1; });
        }
      } else {
        eyes.forEach(e => { e.pupil.position.y = Math.sin(t * 0.5) * 0.02; });
        coin.rotation.y += dt * 0.8;
      }

      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        const su = s.userData as { vx: number; vy: number; vz: number; life: number };
        su.life -= dt * 1.4;
        su.vy -= dt * 2.2;
        s.position.x += su.vx * dt;
        s.position.y += su.vy * dt;
        s.position.z += su.vz * dt;
        (s.material as THREE.SpriteMaterial).opacity = Math.max(0, su.life);
        const sc = 0.26 * Math.max(0.2, su.life);
        s.scale.set(sc, sc, sc);
        if (su.life <= 0) {
          scene.remove(s);
          sparks.splice(i, 1);
        }
      }

      renderer.render(scene, camera);
    }
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      renderer.dispose();
      if (renderer.domElement.parentNode === el) el.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={hostRef} className="absolute inset-0" aria-hidden="true" />;
});
