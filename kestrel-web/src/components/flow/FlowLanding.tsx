"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { FlyingKestrel } from "./FlyingKestrel";

const LOGIN = "/login";

/** "Flow" concept landing page — a fixed full-screen kestrel that "flies" along a
 *  scroll-driven flight route (FlyingKestrel) with readable text chapters scrolling
 *  above it. Custom liquid cursor, ambient sound
 *  toggle, and scroll-reveal narrative. All copy is bilingual via the `landing`
 *  namespace. Honours prefers-reduced-motion (cursor + reveals degrade gracefully). */
export function FlowLanding() {
  const t = useTranslations("landing");
  const cursorRef = useRef<HTMLDivElement>(null);
  const [soundOn, setSoundOn] = useState(false);
  const audioRef = useRef<{ ctx: AudioContext; gain: GainNode } | null>(null);

  // --- custom liquid cursor (lerped follow) ---
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const el = cursorRef.current;
    if (!el) return;
    let cx = window.innerWidth / 2, cy = window.innerHeight / 2, tx = cx, ty = cy, raf = 0;
    const onMove = (e: MouseEvent) => { tx = e.clientX; ty = e.clientY; };
    window.addEventListener("mousemove", onMove);
    const loop = () => {
      cx += (tx - cx) * 0.18; cy += (ty - cy) * 0.18;
      el.style.transform = `translate(${cx}px,${cy}px)`;
      raf = requestAnimationFrame(loop);
    };
    loop();

    const hoverables = document.querySelectorAll("a,button");
    const enter = () => document.body.classList.add("flow-hovering");
    const leave = () => document.body.classList.remove("flow-hovering");
    hoverables.forEach((h) => { h.addEventListener("mouseenter", enter); h.addEventListener("mouseleave", leave); });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      hoverables.forEach((h) => { h.removeEventListener("mouseenter", enter); h.removeEventListener("mouseleave", leave); });
      document.body.classList.remove("flow-hovering");
    };
  }, []);

  // --- scroll reveal ---
  useEffect(() => {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("in"); });
    }, { threshold: 0.3 });
    document.querySelectorAll(".flow-reveal").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  // --- ambient sound (WebAudio pad) ---
  const toggleSound = () => {
    let store = audioRef.current;
    if (!store) {
      const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      const gain = ctx.createGain();
      gain.gain.value = 0;
      gain.connect(ctx.destination);
      [110, 164.81, 220].forEach((f, i) => {
        const o = ctx.createOscillator();
        o.type = "sine"; o.frequency.value = f;
        const g = ctx.createGain(); g.gain.value = 0.06 / (i + 1);
        o.connect(g); g.connect(gain); o.start();
      });
      store = { ctx, gain };
      audioRef.current = store;
    }
    const next = !soundOn;
    store.gain.gain.linearRampToValueAtTime(next ? 0.5 : 0, store.ctx.currentTime + 0.6);
    setSoundOn(next);
  };

  const chapters = [
    { num: t("ch1_num"), title: t("ch1_title"), body: t("ch1_body"), right: false },
    { num: t("ch2_num"), title: t("ch2_title"), body: t("ch2_body"), right: true },
    { num: t("ch3_num"), title: t("ch3_title"), body: t("ch3_body"), right: false },
    { num: t("ch4_num"), title: t("ch4_title"), body: t("ch4_body"), right: true },
  ];

  return (
    <div className="flow-root">
      <FlyingKestrel />

      <header className="flow-header">
        <div className="flow-brand"><span className="flow-dot" />{t("brand")}</div>
        <nav className="flow-menu">
          <a href="#signals">{t("menu_signals")}</a>
          <a href="#scoring">{t("menu_scoring")}</a>
          <a href="#screening">{t("menu_screening")}</a>
          <a href="#advisor">{t("menu_advisor")}</a>
        </nav>
        <Link href={LOGIN} className="flow-menu-pill">{t("menu")}</Link>
      </header>

      <div className="flow-stage">
        <section id="hero" className="flow-section">
          <div className="flow-eyebrow">{t("eyebrow")}</div>
          <h1 className="flow-h1">
            <span className="flow-line"><span>{t("hero_title_1")}</span></span>
            <span className="flow-line"><span className="flow-gloss">{t("hero_title_2")}</span></span>
          </h1>
          <p className="flow-sub">{t("hero_sub")}</p>
          <div className="flow-cta-row">
            <Link className="flow-btn flow-btn-primary" href={LOGIN}>{t("cta_primary")}</Link>
            <a className="flow-btn flow-btn-ghost" href="#signals">{t("cta_ghost")}</a>
          </div>
        </section>

        {chapters.map((c, i) => (
          <section key={i} id={["signals", "scoring", "screening", "advisor"][i]} className="flow-section">
            <div className={`flow-chapter flow-reveal${c.right ? " right" : ""}`}>
              <div className="flow-num">{c.num}</div>
              <h2>{c.title}</h2>
              <p>{c.body}</p>
            </div>
          </section>
        ))}

        <footer className="flow-footer">
          <h2 className="flow-reveal">{t("footer_title")}</h2>
          <Link className="flow-btn flow-btn-primary" href={LOGIN}>{t("footer_cta")}</Link>
          <div className="flow-legal">{t("footer_legal")}</div>
        </footer>
      </div>

      <button
        className={`flow-sound${soundOn ? "" : " muted"}`}
        onClick={toggleSound}
        aria-label={t("sound_label")}
        aria-pressed={soundOn}
      >
        <i /><i /><i />
      </button>
      <div className="flow-scrollhint">{t("scroll")}</div>

      <div className="flow-cursor" ref={cursorRef} aria-hidden>
        <span className="flow-ring outer" />
        <span className="flow-ring inner" />
        <span className="flow-core" />
      </div>

      <FlowStyles />
    </div>
  );
}

/** Scoped styles for the landing page. Kept inline (a single <style>) so the page is
 *  self-contained and never touches the app-wide globals/layout. */
function FlowStyles() {
  return (
    <style>{`
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap');
.flow-root{
  --violet:#b8a9ff;--ice:#9fd4ff;--pink:#f3b5ff;--white:#f6f4ff;--ink:#070611;
  --display:"Space Grotesk",system-ui,sans-serif;--body:"Inter",system-ui,sans-serif;
  position:relative;min-height:100vh;background:var(--ink);color:var(--white);
  font-family:var(--body);overflow-x:hidden;cursor:none;
}
.flow-root a{color:inherit;text-decoration:none}

/* flying kestrel underlay: dark sky (ported from the old WebGL scene) + the bird */
.flow-sky{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.flow-bird{position:absolute;left:16%;top:34%;width:clamp(200px,26vw,380px);height:auto;transform:translate(-50%,-50%);will-change:transform,left,top;filter:drop-shadow(0 18px 60px rgba(159,212,255,.28)) drop-shadow(0 0 30px rgba(184,169,255,.18));opacity:.92;user-select:none}

.flow-stage{position:relative;z-index:2;pointer-events:none}
.flow-section{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:0 clamp(24px,6vw,120px)}
.flow-stage a,.flow-stage button{pointer-events:auto}

.flow-header{position:fixed;z-index:5;top:0;left:0;right:0;display:flex;align-items:center;justify-content:space-between;padding:22px clamp(24px,6vw,60px);pointer-events:none}
.flow-brand{font-family:var(--display);font-weight:600;letter-spacing:.18em;font-size:14px;text-transform:uppercase;display:flex;align-items:center;gap:10px;pointer-events:auto}
.flow-dot{width:9px;height:9px;border-radius:50%;background:linear-gradient(135deg,var(--ice),var(--pink));box-shadow:0 0 18px var(--violet)}
.flow-menu{display:flex;gap:30px;pointer-events:auto}
.flow-menu a{font-size:13px;letter-spacing:.06em;color:rgba(246,244,255,.65);transition:color .3s}
.flow-menu a:hover{color:var(--white)}
.flow-menu-pill{display:none;pointer-events:auto;padding:9px 18px;border:1px solid rgba(184,169,255,.35);border-radius:999px;font-size:13px;letter-spacing:.05em;backdrop-filter:blur(8px);background:rgba(20,18,40,.4)}

.flow-eyebrow{font-family:var(--display);font-size:12px;letter-spacing:.32em;text-transform:uppercase;color:var(--ice);margin-bottom:26px;opacity:0;animation:flow-rise 1s .2s forwards}
.flow-h1{font-family:var(--display);font-weight:500;font-size:clamp(46px,8.5vw,120px);line-height:.96;letter-spacing:-.02em;max-width:16ch;text-shadow:0 4px 60px rgba(159,212,255,.25)}
.flow-line{display:block;overflow:hidden}
.flow-line span{display:block;opacity:0;transform:translateY(110%);animation:flow-reveal 1.1s cubic-bezier(.2,.7,.2,1) forwards}
.flow-line:nth-child(1) span{animation-delay:.35s}
.flow-line:nth-child(2) span{animation-delay:.5s}
.flow-gloss{background:linear-gradient(100deg,var(--violet),var(--ice),var(--pink));-webkit-background-clip:text;background-clip:text;color:transparent}
.flow-sub{margin-top:34px;max-width:48ch;font-weight:300;font-size:clamp(15px,1.5vw,18px);line-height:1.6;color:rgba(246,244,255,.72);opacity:0;animation:flow-rise 1s .8s forwards}
.flow-cta-row{margin-top:46px;display:flex;gap:16px;flex-wrap:wrap;opacity:0;animation:flow-rise 1s 1s forwards}
.flow-btn{font-family:var(--display);font-size:14px;letter-spacing:.03em;padding:15px 30px;border-radius:999px;transition:transform .35s,box-shadow .35s}
.flow-btn-primary{background:linear-gradient(120deg,var(--violet),var(--ice));color:#0a0818;font-weight:600;box-shadow:0 8px 40px rgba(159,212,255,.35)}
.flow-btn-primary:hover{transform:translateY(-3px);box-shadow:0 14px 50px rgba(184,169,255,.5)}
.flow-btn-ghost{border:1px solid rgba(246,244,255,.25);color:var(--white)}
.flow-btn-ghost:hover{border-color:var(--ice);transform:translateY(-3px)}

.flow-chapter{max-width:560px}
.flow-num{font-family:var(--display);font-size:12px;letter-spacing:.3em;color:var(--pink);margin-bottom:18px}
.flow-chapter h2{font-family:var(--display);font-weight:500;font-size:clamp(30px,4.5vw,56px);line-height:1.04;letter-spacing:-.01em;margin-bottom:20px}
.flow-chapter p{font-weight:300;line-height:1.65;color:rgba(246,244,255,.7);font-size:clamp(15px,1.5vw,17px)}
.flow-chapter.right{margin-left:auto;text-align:right}

.flow-footer{z-index:2;position:relative;text-align:center;padding:120px 24px 60px}
.flow-footer h2{font-family:var(--display);font-weight:500;font-size:clamp(34px,6vw,80px);letter-spacing:-.02em;margin-bottom:30px}
.flow-legal{margin-top:80px;font-size:12px;letter-spacing:.08em;color:rgba(246,244,255,.4)}

.flow-sound{position:fixed;z-index:6;left:clamp(20px,4vw,40px);bottom:30px;width:54px;height:54px;border-radius:50%;pointer-events:auto;border:1px solid rgba(184,169,255,.35);background:rgba(13,11,28,.5);backdrop-filter:blur(10px);display:flex;align-items:center;justify-content:center;gap:3px;transition:border-color .3s,transform .3s}
.flow-sound:hover{border-color:var(--ice);transform:scale(1.06)}
.flow-sound i{display:block;width:3px;border-radius:2px;background:var(--ice);animation:flow-eq 1.1s ease-in-out infinite}
.flow-sound i:nth-child(1){height:10px;animation-delay:0s}
.flow-sound i:nth-child(2){height:18px;animation-delay:.2s}
.flow-sound i:nth-child(3){height:13px;animation-delay:.4s}
.flow-sound.muted i{animation-play-state:paused;height:6px;opacity:.4}

.flow-scrollhint{position:fixed;z-index:5;right:clamp(20px,4vw,40px);bottom:34px;writing-mode:vertical-rl;font-family:var(--display);font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:rgba(246,244,255,.45);pointer-events:none}

.flow-cursor{position:fixed;top:0;left:0;z-index:50;pointer-events:none;transform:translate(-50%,-50%);mix-blend-mode:screen}
.flow-ring{position:absolute;top:50%;left:50%;border-radius:50%;transform:translate(-50%,-50%)}
.flow-ring.outer{width:34px;height:34px;border:1px solid rgba(159,212,255,.55);transition:width .3s,height .3s,opacity .3s}
.flow-ring.inner{width:22px;height:22px;border:1px dashed rgba(243,181,255,.7);animation:flow-spin 4s linear infinite}
.flow-core{position:absolute;top:50%;left:50%;width:5px;height:5px;transform:translate(-50%,-50%) rotate(45deg);background:var(--white);box-shadow:0 0 10px var(--ice)}
body.flow-hovering .flow-ring.outer{width:50px;height:50px;opacity:.5}

@keyframes flow-spin{to{transform:translate(-50%,-50%) rotate(360deg)}}
@keyframes flow-eq{0%,100%{transform:scaleY(.5)}50%{transform:scaleY(1)}}
@keyframes flow-reveal{to{opacity:1;transform:translateY(0)}}
@keyframes flow-rise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.flow-reveal{opacity:0;transform:translateY(40px);transition:opacity 1s,transform 1s}
.flow-reveal.in{opacity:1;transform:translateY(0)}

@media (max-width:760px){
  .flow-menu{display:none}
  .flow-menu-pill{display:block}
  .flow-chapter.right{text-align:left;margin-left:0}
  .flow-scrollhint{display:none}
}
@media (prefers-reduced-motion:reduce){
  .flow-root *{animation:none!important;transition:none!important}
  .flow-reveal{opacity:1;transform:none}
  .flow-root{cursor:auto}
  .flow-cursor{display:none}
  .flow-h1 .flow-line span,.flow-eyebrow,.flow-sub,.flow-cta-row{opacity:1;transform:none}
}
    `}</style>
  );
}
