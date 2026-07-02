"use client";

import { useRef, useState } from "react";

export type VoiceState = "idle" | "connecting" | "listening" | "transcribing";

/** Voice-input engine for the chat composer: mic permission + device enumeration,
 *  push-to-talk / click recording, live level metering, and Whisper transcription.
 *
 *  Extracted from ChatWindow so the composer UI stays presentational. The hook owns
 *  the audio graph (MediaRecorder, AudioContext, analyser) and device state; the
 *  caller owns the menu open/close UI and drives the mic-test lifecycle via
 *  loadAudioDevices/startMicTest/stopMicTest. `onTranscript` receives the final
 *  text (empty string on failure), which the composer writes into the input. */
export function useVoiceRecorder(onTranscript: (text: string) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [micMuted, setMicMuted] = useState(false);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [outputDevices, setOutputDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>("");
  const [selectedOutput, setSelectedOutput] = useState<string>("");
  const [holdToRecord, setHoldToRecord] = useState(true);
  const [micLevel, setMicLevel] = useState(0);
  const [micPermissionGranted, setMicPermissionGranted] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number>(0);
  const micTestStreamRef = useRef<MediaStream | null>(null);
  const micTestCtxRef = useRef<AudioContext | null>(null);
  const micTestAnimRef = useRef<number>(0);

  const loadAudioDevices = async () => {
    if (micPermissionGranted && audioDevices.length > 0) return;
    try {
      if (!micPermissionGranted) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((tr) => tr.stop());
        setMicPermissionGranted(true);
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const mics = devices.filter((d) => d.kind === "audioinput");
      const speakers = devices.filter((d) => d.kind === "audiooutput");
      setAudioDevices(mics);
      setOutputDevices(speakers);
      if (!selectedDevice && mics.length > 0) setSelectedDevice(mics[0].deviceId);
      if (!selectedOutput && speakers.length > 0) setSelectedOutput(speakers[0].deviceId);
    } catch { /* permission denied */ }
  };

  const startMicTest = async () => {
    try {
      const constraints: MediaStreamConstraints = { audio: selectedDevice ? { deviceId: { exact: selectedDevice } } : true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      micTestStreamRef.current = stream;
      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      micTestCtxRef.current = ctx;

      const updateLevel = () => {
        const data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        setMicLevel(Math.min(rms * 4, 1));
        micTestAnimRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch { /* silent */ }
  };

  const stopMicTest = () => {
    cancelAnimationFrame(micTestAnimRef.current);
    micTestStreamRef.current?.getTracks().forEach((tr) => tr.stop());
    micTestStreamRef.current = null;
    micTestCtxRef.current?.close();
    micTestCtxRef.current = null;
    setMicLevel(0);
  };

  const selectDevice = (deviceId: string) => {
    setSelectedDevice(deviceId);
    stopMicTest();
    setTimeout(() => startMicTest(), 100);
  };

  const transcribeAudio = async (blob: Blob) => {
    setVoiceState("transcribing");
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("kestrel_token") : null;
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${baseUrl}/voice/transcribe`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      const data = await res.json();
      if (data.text) onTranscript(data.text);
    } catch {
      onTranscript("");
    } finally {
      setVoiceState("idle");
    }
  };

  const startRecording = async () => {
    try {
      setVoiceState("connecting");
      await loadAudioDevices();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: selectedDevice ? { deviceId: { exact: selectedDevice } } : true,
      });

      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const recorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        transcribeAudio(blob);
        stream.getTracks().forEach((tr) => tr.stop());
        cancelAnimationFrame(animFrameRef.current);
        audioCtx.close();
        setMicLevel(0);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setVoiceState("listening");

      const updateLevel = () => {
        if (analyserRef.current) {
          const data = new Uint8Array(analyserRef.current.fftSize);
          analyserRef.current.getByteTimeDomainData(data);
          let sum = 0;
          for (let i = 0; i < data.length; i++) {
            const v = (data[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / data.length);
          setMicLevel(Math.min(rms * 4, 1));
        }
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch {
      setVoiceState("idle");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setVoiceState("idle");
  };

  /** Click-to-toggle recording (used when hold-to-record is off). */
  const toggleRecording = () => {
    if (voiceState === "idle") startRecording();
    else stopRecording();
  };

  /** Mute/unmute the live recording's audio tracks. */
  const toggleMute = () => {
    setMicMuted((prev) => {
      const next = !prev;
      mediaRecorderRef.current?.stream?.getAudioTracks().forEach((tr) => { tr.enabled = prev; });
      return next;
    });
  };

  /** Full stop + reset back to idle (the ··· cancel control). */
  const stopAndReset = () => {
    stopRecording();
    setVoiceState("idle");
    setMicMuted(false);
  };

  return {
    voiceState,
    micLevel,
    micMuted,
    holdToRecord,
    setHoldToRecord,
    audioDevices,
    outputDevices,
    selectedDevice,
    selectedOutput,
    setSelectedOutput,
    loadAudioDevices,
    startMicTest,
    stopMicTest,
    selectDevice,
    startRecording,
    stopRecording,
    toggleRecording,
    toggleMute,
    stopAndReset,
  };
}
