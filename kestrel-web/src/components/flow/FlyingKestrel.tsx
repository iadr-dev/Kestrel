"use client";

import { useEffect, useRef } from "react";

/** Scroll-driven flight route for the landing page. Renders `/landing/kestrel.webp`
 *  as a fixed-position underlay that "flies" across the viewport as the user scrolls
 *  through the chapters. The trajectory is a hand-authored set of waypoints
 *  (position + scale) that scroll progress interpolates between (Catmull-Rom smoothing
 *  for a curved, sweeping path). Banking rotation is derived from the instantaneous
 *  direction of travel, a gentle idle bob is layered on top, and scale gives a
 *  parallax/depth feel. Driven off window.scrollY via a rAF-throttled scroll listener.
 *
 *  Sits behind the text (low z-index) but above the dark background gradient which
 *  it also provides (ported from the old FlowScene inline style). Under
 *  prefers-reduced-motion the kestrel is shown static at its first waypoint. */
export function FlyingKestrel() {
  const birdRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const bird = birdRef.current;
    if (!bird) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Flight waypoints keyed to scroll progress (0 = top / hero, 1 = footer).
    // x/y are viewport fractions (0..1) of the bird's centre; s is scale.
    // The route sweeps in from the left at the hero, banks across to the right for
    // chapter 1, dives down-left for chapter 2, climbs back right for chapter 3,
    // then glides toward centre for chapter 4 / footer.
    const route: { p: number; x: number; y: number; s: number }[] = [
      { p: 0.0, x: 0.16, y: 0.34, s: 1.0 },
      { p: 0.25, x: 0.74, y: 0.28, s: 0.82 },
      { p: 0.5, x: 0.24, y: 0.6, s: 1.12 },
      { p: 0.72, x: 0.78, y: 0.42, s: 0.7 },
      { p: 1.0, x: 0.5, y: 0.5, s: 0.95 },
    ];

    // Catmull-Rom interpolation of a single channel across the route.
    const sample = (prog: number, key: "x" | "y" | "s") => {
      // clamp
      const t = Math.min(1, Math.max(0, prog));
      // find bracketing segment
      let i = 0;
      while (i < route.length - 1 && route[i + 1].p < t) i++;
      const p0 = route[Math.max(0, i - 1)];
      const p1 = route[i];
      const p2 = route[Math.min(route.length - 1, i + 1)];
      const p3 = route[Math.min(route.length - 1, i + 2)];
      const span = p2.p - p1.p || 1;
      const lt = (t - p1.p) / span;
      const v0 = p0[key], v1 = p1[key], v2 = p2[key], v3 = p3[key];
      const t2 = lt * lt;
      const t3 = t2 * lt;
      return (
        0.5 *
        ((2 * v1) +
          (-v0 + v2) * lt +
          (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2 +
          (-v0 + 3 * v1 - 3 * v2 + v3) * t3)
      );
    };

    const applyStatic = () => {
      const x = sample(0, "x");
      const y = sample(0, "y");
      const s = sample(0, "s");
      bird.style.left = `${x * 100}%`;
      bird.style.top = `${y * 100}%`;
      bird.style.transform = `translate(-50%,-50%) scale(${s})`;
    };

    if (reduceMotion) {
      applyStatic();
      return;
    }

    let raf = 0;
    let ticking = false;
    const startMs = performance.now();

    const render = () => {
      ticking = false;
      const max = document.body.scrollHeight - window.innerHeight || 1;
      const prog = Math.min(1, Math.max(0, window.scrollY / max));

      const x = sample(prog, "x");
      const y = sample(prog, "y");
      const s = sample(prog, "s");

      // Banking: rotate toward the direction of travel. Sample slightly ahead and
      // behind to get the tangent of the path in viewport space, then tilt by it.
      const eps = 0.006;
      const ax = sample(prog + eps, "x") - sample(prog - eps, "x");
      const ay = sample(prog + eps, "y") - sample(prog - eps, "y");
      // atan2 gives heading; scale down so the bank reads as a subtle tilt, not a spin.
      const bank = Math.atan2(ay, ax) * (180 / Math.PI) * 0.28;

      // Gentle idle bob (vertical) + a touch of wing-flap breathing on scale.
      const time = (performance.now() - startMs) / 1000;
      const bob = Math.sin(time * 1.6) * 0.9; // in % of viewport height
      const breathe = 1 + Math.sin(time * 2.4) * 0.015;

      bird.style.left = `${x * 100}%`;
      bird.style.top = `${y * 100 + bob}%`;
      bird.style.transform = `translate(-50%,-50%) rotate(${bank}deg) scale(${s * breathe})`;
    };

    const loop = () => {
      raf = requestAnimationFrame(() => {
        render();
        loop();
      });
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(render);
      }
    };

    // rAF loop keeps the idle bob + breathing alive; scroll listener guarantees
    // an immediate update on scroll even between loop frames.
    render();
    loop();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <div
      aria-hidden
      className="flow-sky"
      style={{ background: "radial-gradient(120% 90% at 50% 10%, #15122b 0%, #0a0818 45%, #050410 100%)" }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img ref={birdRef} src="/landing/kestrel.webp" alt="" className="flow-bird" draggable={false} />
    </div>
  );
}
