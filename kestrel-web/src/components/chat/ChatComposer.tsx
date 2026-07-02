"use client";

import { useRef, useEffect, useState } from "react";
import { Square, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useEntitlements } from "@/hooks/useEntitlements";
import { SkillMenu } from "./SkillMenu";

export interface Attachment { name: string; type: string; size: number; dataUrl?: string }

interface Props {
  input: string;
  setInput: (v: string) => void;
  model: string;
  setModel: (v: string) => void;
  isStreaming: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  handleKeyDown: (e: React.KeyboardEvent) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  webSearchEnabled: boolean;
  setWebSearchEnabled: (v: boolean) => void;
  researchEnabled: boolean;
  setResearchEnabled: (v: boolean) => void;
  planEnabled: boolean;
  setPlanEnabled: (v: boolean) => void;
  attachments: Attachment[];
  setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
}

/** The chat input bar: textarea + slash-command menu, attachment preview, the +
 *  (files/screenshot/feature-toggles) menu, model selector, and the voice-input
 *  controls. The audio engine lives in useVoiceRecorder; this component owns the
 *  menu open/close UI and file/screenshot capture. Split out of ChatWindow. */
export function ChatComposer({
  input, setInput, model, setModel, isStreaming, onSubmit, onCancel, handleKeyDown, textareaRef,
  webSearchEnabled, setWebSearchEnabled, researchEnabled, setResearchEnabled,
  planEnabled, setPlanEnabled, attachments, setAttachments,
}: Props) {
  const t = useTranslations("chat");
  const router = useRouter();
  const toast = useToast();
  const voice = useVoiceRecorder(setInput);
  // Deep research is a Pro feature — gate the toggle (route to pricing if unentitled).
  const { can: canFeature } = useEntitlements();
  const canResearch = canFeature("deep_research");
  const [plusMenuOpen, setPlusMenuOpen] = useState(false);
  const [micMenuOpen, setMicMenuOpen] = useState(false);
  const [micHovered, setMicHovered] = useState(false);
  const [audioSettingsOpen, setAudioSettingsOpen] = useState(false);
  // Slash-command skill menu: open when the input is a bare "/query" (no spaces yet).
  const slashMatch = /^\/(\S*)$/.exec(input);
  const skillMenuOpen = slashMatch !== null;
  const skillQuery = slashMatch ? slashMatch[1] : "";
  const skillKeyHandlerRef = useRef<((e: React.KeyboardEvent) => boolean) | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const plusRef = useRef<HTMLDivElement>(null);
  const micRef = useRef<HTMLDivElement>(null);

  const closeMicMenu = () => { setMicMenuOpen(false); voice.stopMicTest(); };
  const openMicMenu = async () => { await voice.loadAudioDevices(); setMicMenuOpen(true); voice.startMicTest(); };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (plusRef.current && !plusRef.current.contains(e.target as Node)) setPlusMenuOpen(false);
      if (micRef.current && !micRef.current.contains(e.target as Node)) { closeMicMenu(); setMicHovered(false); }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
    // Outside-click listener binds once; closeMicMenu is stable enough here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileUpload = () => fileInputRef.current?.click();

  const onFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    Array.from(files).forEach((file) => {
      if (file.size > MAX_SIZE) { toast.error(t("file_too_large")); return; }
      const reader = new FileReader();
      reader.onerror = () => toast.error(t("file_read_error"));
      reader.onload = () => {
        setAttachments((prev) => [...prev, { name: file.name, type: file.type, size: file.size, dataUrl: reader.result as string }]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = "";
  };

  const handleScreenshot = async () => {
    setPlusMenuOpen(false);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "browser" },
        preferCurrentTab: false,
      } as DisplayMediaStreamOptions);
      const track = stream.getVideoTracks()[0];
      const video = document.createElement("video");
      video.srcObject = stream;
      video.setAttribute("playsinline", "true");
      await video.play();
      await new Promise((r) => setTimeout(r, 100));
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")?.drawImage(video, 0, 0);
      track.stop();
      stream.getTracks().forEach((tr) => tr.stop());
      const dataUrl = canvas.toDataURL("image/png");
      setAttachments((prev) => [...prev, {
        name: `screenshot-${Date.now()}.png`,
        type: "image/png",
        size: Math.round(dataUrl.length * 0.75),
        dataUrl,
      }]);
    } catch { /* user cancelled the picker */ }
  };

  const removeAttachment = (index: number) => setAttachments((prev) => prev.filter((_, i) => i !== index));

  const { voiceState, startRecording, stopRecording, toggleRecording, holdToRecord } = voice;
  const hasInput = input.trim().length > 0 || attachments.length > 0;

  return (
    <div className="px-4 md:px-8 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-background border border-border/40 rounded-2xl px-4 pt-3 pb-2 focus-within:border-signal/40 transition-colors shadow-sm">
          {/* Hidden file input */}
          <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.csv,.json" onChange={onFilesSelected} className="hidden" />

          {/* Attachments preview */}
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {attachments.map((file, i) => (
                <div key={i} className="flex items-center gap-1.5 px-2 py-1 bg-raised rounded-lg border border-border">
                  {file.type.startsWith("image/") && file.dataUrl ? (
                    // Local file-attachment preview (data: URI) — next/image doesn't handle data URIs.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={file.dataUrl} alt="" className="w-6 h-6 rounded object-cover" />
                  ) : (
                    <svg className="w-4 h-4 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  )}
                  <span className="text-[10px] text-muted max-w-[80px] truncate">{file.name}</span>
                  <button onClick={() => removeAttachment(i)} aria-label={t("remove_attachment")} className="p-0.5 hover:bg-border rounded transition-colors">
                    <svg className="w-3 h-3 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Textarea / Voice transcription area */}
          {voiceState !== "idle" ? (
            <div className="min-h-[24px] py-1">
              <span className="text-sm text-muted/60">
                {voiceState === "connecting" ? t("voice_connecting") : voiceState === "transcribing" ? t("voice_transcribing") : input || t("voice_listening")}
              </span>
            </div>
          ) : (
            <div className="relative">
              {skillMenuOpen && (
                <SkillMenu
                  query={skillQuery}
                  onSelect={(skill) => {
                    // Frame the prompt around the chosen skill; the backend classifier
                    // then routes to it. User continues typing their actual question.
                    setInput(`[${skill.name}] `);
                    textareaRef.current?.focus();
                  }}
                  onClose={() => setInput("")}
                  registerKeyHandler={(h) => { skillKeyHandlerRef.current = h; }}
                />
              )}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  // While the slash menu is open, let it consume nav/select keys first.
                  if (skillMenuOpen && skillKeyHandlerRef.current?.(e)) { e.preventDefault(); return; }
                  handleKeyDown(e);
                }}
                placeholder={t("input_placeholder")}
                rows={1}
                className="w-full bg-transparent resize-none outline-none text-sm leading-relaxed max-h-[150px] text-foreground placeholder:text-muted/50"
              />
            </div>
          )}

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between mt-2 pt-1">
            {/* Left: + button, research / plan indicators */}
            <div className="flex items-center gap-1">
              <div ref={plusRef} className="relative">
                <button
                  onClick={() => setPlusMenuOpen(!plusMenuOpen)}
                  aria-label={t("attach_menu")}
                  className="p-1.5 rounded-lg hover:bg-raised transition-colors text-muted hover:text-foreground"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
                {plusMenuOpen && (
                  <div className="absolute bottom-full left-0 mb-2 bg-surface border border-border rounded-xl shadow-xl shadow-black/10 py-2 z-50 w-52">
                    <PlusMenuItem icon={<svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>} label={t("add_files")} shortcut="Ctrl+U" onClick={() => { setPlusMenuOpen(false); handleFileUpload(); }} />
                    <PlusMenuItem icon={<svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>} label={t("take_screenshot")} onClick={handleScreenshot} />
                    <div className="my-1.5 border-t border-border" />
                    <PlusMenuItem
                      icon={canResearch
                        ? <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
                        : <Lock className="w-4 h-4" />}
                      label={t("research")}
                      checked={canResearch && researchEnabled}
                      onClick={() => {
                        setPlusMenuOpen(false);
                        // Pro-gated: unentitled users are sent to the pricing page.
                        if (!canResearch) { router.push("/pricing"); return; }
                        setResearchEnabled(!researchEnabled);
                      }}
                    />
                    <PlusMenuItem
                      icon={<svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>}
                      label={t("web_search")}
                      checked={webSearchEnabled}
                      onClick={() => { setWebSearchEnabled(!webSearchEnabled); setPlusMenuOpen(false); }}
                    />
                    <PlusMenuItem
                      icon={<svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>}
                      label={t("plan_mode")}
                      checked={planEnabled}
                      onClick={() => { setPlanEnabled(!planEnabled); setPlusMenuOpen(false); }}
                    />
                  </div>
                )}
              </div>

              {researchEnabled && (
                <button onClick={() => setResearchEnabled(false)} className="p-1.5 rounded-lg bg-signal/10 text-signal" title="Research enabled">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
                </button>
              )}

              {planEnabled && (
                <button onClick={() => setPlanEnabled(false)} className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-signal/10 text-signal text-[11px] font-medium" title={t("plan_mode")}>
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
                  {t("plan_mode")}
                </button>
              )}
            </div>

            {/* Right: model, mic, send/voice */}
            <div className="flex items-center gap-1.5">
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="text-[11px] bg-surface border border-border/40 rounded-lg px-2 py-1 text-foreground outline-none cursor-pointer hover:border-signal/30 transition-colors"
              >
                <option value="auto">Auto</option>
                <optgroup label="Free">
                  <option value="chatanywhere/gpt-4o-mini">GPT-4o Mini (Free)</option>
                  <option value="chatanywhere/gpt-5-mini">GPT-5 Mini (Free)</option>
                  <option value="deepseek-ai/deepseek-v4-flash">DeepSeek V4 Flash</option>
                  <option value="openrouter/free">OpenRouter Free</option>
                </optgroup>
                {/* Vision model for image analysis (verified: describes charts/photos
                    accurately). It's the $0 free-tier vision fallback. Phi-4 was removed —
                    its NVIDIA function is degraded/unavailable. */}
                <optgroup label="Free · Vision">
                  <option value="meta/llama-4-maverick-17b-128e-instruct">Llama 4 Maverick (Vision)</option>
                </optgroup>
                <optgroup label="Anthropic">
                  <option value="claude-opus-4-8">Claude Opus 4.8</option>
                  <option value="claude-opus-4-6">Claude Opus 4.6</option>
                  <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                  <option value="claude-haiku-4-5">Claude Haiku 4.5</option>
                  <option value="claude-fable-5" disabled>Claude Fable 5 (unavailable)</option>
                  <option value="claude-mythos-5" disabled>Claude Mythos 5 (unavailable)</option>
                </optgroup>
                <optgroup label="OpenAI">
                  <option value="gpt-5.5">GPT-5.5</option>
                  <option value="gpt-5.4">GPT-5.4</option>
                  <option value="gpt-5.4-mini">GPT-5.4 Mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                </optgroup>
                <optgroup label="Google">
                  <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro</option>
                  <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                  <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                </optgroup>
                <optgroup label="Other">
                  <option value="deepseek-ai/deepseek-v4-pro">DeepSeek V4 Pro</option>
                  <option value="minimaxai/minimax-m2.7">MiniMax M2.7</option>
                </optgroup>
              </select>

              {/* Mic button with settings arrow on hover */}
              <div
                ref={micRef}
                className="relative flex items-center"
                onMouseEnter={() => setMicHovered(true)}
                onMouseLeave={() => { if (!micMenuOpen) setMicHovered(false); }}
              >
                {(micHovered || micMenuOpen) && (
                  <button
                    onClick={() => micMenuOpen ? closeMicMenu() : openMicMenu()}
                    aria-label={t("voice_input")}
                    className="p-1.5 rounded-lg border border-border bg-raised/50 text-muted hover:text-foreground transition-all"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
                  </button>
                )}
                <button
                  onClick={holdToRecord ? undefined : toggleRecording}
                  onMouseDown={holdToRecord ? () => startRecording() : undefined}
                  onMouseUp={holdToRecord ? () => stopRecording() : undefined}
                  onMouseLeave={holdToRecord ? () => stopRecording() : undefined}
                  onTouchStart={holdToRecord ? () => startRecording() : undefined}
                  onTouchEnd={holdToRecord ? () => stopRecording() : undefined}
                  className={`p-1.5 rounded-lg transition-colors shrink-0 select-none ${
                    voiceState === "listening" ? "bg-down/10 text-down scale-110" : "hover:bg-raised text-muted hover:text-foreground"
                  }`}
                  title={t("hold_to_record")}
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                </button>
                {micMenuOpen && (
                  <div className="absolute bottom-full right-0 mb-2 bg-surface border border-border rounded-xl shadow-xl shadow-black/10 py-2 z-50 w-64">
                    {/* Volume level indicator */}
                    <div className="px-3 py-1.5 flex items-center gap-2">
                      <div className={`w-2.5 h-2.5 rounded-full transition-colors ${voice.micLevel > 0.05 ? "bg-up animate-pulse" : "bg-signal"}`} />
                      <div className="flex-1 h-2 bg-raised rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.max(voice.micLevel * 100, 3)}%`,
                            backgroundColor: voice.micLevel > 0.6 ? "var(--up)" : "var(--signal)",
                            transition: "width 50ms ease-out",
                          }}
                        />
                      </div>
                    </div>
                    {/* Device list */}
                    {voice.audioDevices.map((device) => (
                      <button
                        key={device.deviceId}
                        onClick={() => voice.selectDevice(device.deviceId)}
                        className="flex items-center justify-between w-full px-3 py-2 text-xs text-foreground/80 hover:bg-raised transition-colors"
                      >
                        <span className="truncate">{device.label || t("voice_microphone")}</span>
                        {voice.selectedDevice === device.deviceId && (
                          <svg className="w-3.5 h-3.5 text-signal shrink-0 ml-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                        )}
                      </button>
                    ))}
                    {voice.audioDevices.length === 0 && (
                      <div className="px-3 py-2 text-xs text-muted">{t("voice_no_mic")}</div>
                    )}
                    <div className="my-1 border-t border-border" />
                    {/* Hold to record toggle */}
                    <button
                      onClick={() => voice.setHoldToRecord(!holdToRecord)}
                      className="flex items-center justify-between w-full px-3 py-1.5 text-xs text-muted hover:bg-raised transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
                        <span>{t("hold_to_record")}</span>
                      </div>
                      <div className={`w-8 h-4 rounded-full relative transition-colors ${holdToRecord ? "bg-signal" : "bg-border"}`}>
                        <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${holdToRecord ? "right-0.5" : "left-0.5"}`} />
                      </div>
                    </button>
                  </div>
                )}
              </div>

              {/* Send / Voice mode button */}
              {isStreaming ? (
                <button onClick={onCancel} aria-label={t("stop")} className="p-2 rounded-xl bg-down/10 text-down hover:bg-down/20 transition-colors shrink-0" title="Stop (Esc)">
                  <Square className="w-4 h-4" />
                </button>
              ) : voiceState !== "idle" ? (
                <div className="flex items-center gap-1.5">
                  {/* Audio settings chevron */}
                  <div className="relative" ref={plusRef}>
                    <button
                      onClick={() => setAudioSettingsOpen(!audioSettingsOpen)}
                      aria-label={t("audio_settings")}
                      className="p-1.5 rounded-lg hover:bg-raised transition-colors text-muted"
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
                    </button>
                    {audioSettingsOpen && (
                      <div className="absolute bottom-full right-0 mb-2 bg-surface border border-border rounded-xl shadow-xl py-2 z-50 w-72">
                        {/* Speakers */}
                        <div className="px-3 py-1.5 flex items-center gap-2 text-xs text-muted">
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/></svg>
                          <span>{t("voice_speakers")}</span>
                        </div>
                        {voice.outputDevices.map((d) => (
                          <button
                            key={d.deviceId}
                            onClick={() => voice.setSelectedOutput(d.deviceId)}
                            className="flex items-center justify-between w-full px-3 py-1.5 text-xs hover:bg-raised transition-colors"
                          >
                            <span className="truncate">{d.label || t("voice_speaker")}</span>
                            {voice.selectedOutput === d.deviceId && <svg className="w-3.5 h-3.5 text-signal shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>}
                          </button>
                        ))}
                        {/* Mic volume indicator */}
                        <div className="px-3 py-2 flex items-center gap-2 border-t border-border mt-1 pt-2">
                          <svg className="w-3.5 h-3.5 text-muted shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
                          <div className="flex-1 h-1.5 bg-raised rounded-full overflow-hidden">
                            <div className="h-full bg-signal rounded-full transition-all" style={{ width: `${Math.max(voice.micLevel * 100, 3)}%`, transition: "width 50ms" }} />
                          </div>
                        </div>
                        {/* Mic devices */}
                        {voice.audioDevices.map((d) => (
                          <button
                            key={d.deviceId}
                            onClick={() => { voice.selectDevice(d.deviceId); setAudioSettingsOpen(false); }}
                            className="flex items-center justify-between w-full px-3 py-1.5 text-xs hover:bg-raised transition-colors"
                          >
                            <span className="truncate">{d.label || t("voice_microphone")}</span>
                            {voice.selectedDevice === d.deviceId && <svg className="w-3.5 h-3.5 text-signal shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Mic mute toggle */}
                  <button
                    onClick={voice.toggleMute}
                    className={`p-1.5 rounded-lg transition-colors ${voice.micMuted ? "bg-down/15 text-down" : "hover:bg-raised text-muted hover:text-foreground"}`}
                    title={voice.micMuted ? t("voice_unmute") : t("voice_mute")}
                  >
                    {voice.micMuted ? (
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    ) : (
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
                    )}
                  </button>

                  {/* ··· Stop/Cancel button */}
                  <button
                    onClick={() => { voice.stopAndReset(); setInput(""); setAudioSettingsOpen(false); }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-signal/15 text-signal hover:bg-signal/25 transition-colors text-xs font-medium"
                  >
                    <span className="flex gap-0.5">
                      <span className="w-1 h-1 rounded-full bg-signal animate-pulse" />
                      <span className="w-1 h-1 rounded-full bg-signal animate-pulse" style={{animationDelay:"0.15s"}} />
                      <span className="w-1 h-1 rounded-full bg-signal animate-pulse" style={{animationDelay:"0.3s"}} />
                    </span>
                    {voiceState === "connecting" ? t("cancel") : t("voice_stop")}
                  </button>
                </div>
              ) : hasInput ? (
                <button onClick={onSubmit} aria-label={t("send")} className="p-2 rounded-xl bg-signal text-background hover:brightness-110 transition-all shrink-0">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
              ) : (
                <button
                  onClick={holdToRecord ? undefined : toggleRecording}
                  onMouseDown={holdToRecord ? () => startRecording() : undefined}
                  onMouseUp={holdToRecord ? () => stopRecording() : undefined}
                  onMouseLeave={holdToRecord ? () => stopRecording() : undefined}
                  onTouchStart={holdToRecord ? () => startRecording() : undefined}
                  onTouchEnd={holdToRecord ? () => stopRecording() : undefined}
                  className="group p-2 rounded-xl hover:bg-raised transition-colors text-muted hover:text-foreground shrink-0 select-none"
                  title={t("hold_to_record")}
                >
                  <svg className="w-5 h-5" viewBox="0 0 28 20" fill="currentColor">
                    <rect x="1" y="7" width="2.5" height="6" rx="1.25" className="voice-bar voice-bar-1" />
                    <rect x="5.5" y="5" width="2.5" height="10" rx="1.25" className="voice-bar voice-bar-2" />
                    <rect x="10" y="3" width="2.5" height="14" rx="1.25" className="voice-bar voice-bar-3" />
                    <rect x="14.5" y="4" width="2.5" height="12" rx="1.25" className="voice-bar voice-bar-4" />
                    <rect x="19" y="2" width="2.5" height="16" rx="1.25" className="voice-bar voice-bar-5" />
                    <rect x="23.5" y="5" width="2.5" height="10" rx="1.25" className="voice-bar voice-bar-6" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
        <p className="text-[10px] text-muted/50 text-center mt-2">{t("disclaimer")}</p>
      </div>
    </div>
  );
}

function PlusMenuItem({ icon, label, shortcut, checked, onClick }: { icon: React.ReactNode; label: string; shortcut?: string; checked?: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center gap-3 w-full px-3 py-2 text-sm text-muted hover:text-foreground hover:bg-raised transition-colors">
      {icon}
      <span className="flex-1 text-left">{label}</span>
      {shortcut && <span className="text-[10px] text-muted/50">{shortcut}</span>}
      {checked !== undefined && checked && (
        <svg className="w-4 h-4 text-signal" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
      )}
    </button>
  );
}
