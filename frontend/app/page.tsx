"use client";
import AnatomyViewer from "@/components/AnatomyViewer";
import { useState, useRef, useEffect, useCallback, Suspense, useMemo, useRef as useReactRef } from "react";

import { Canvas, ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Environment, useGLTF, Html } from "@react-three/drei";

// place human_body.glb inside /public folder
 
// ─── Helpers ───────────────────────────────────────────────────────────────────
const uid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
 
const generateTitle = (text: string) => {
  const t = text.trim().toLowerCase();

  if (t.includes("chest pain")) return "Chest Pain Concern";
  if (t.includes("headache")) return "Headache Analysis";
  if (t.includes("fever")) return "Fever Symptoms";
  if (t.includes("skin") || t.includes("rash")) return "Skin Issue";
  if (t.includes("stomach") || t.includes("abdomen")) return "Stomach Concern";
  if (t.includes("uric acid")) return "High Uric Acid";
  if (t.includes("pain")) return "Pain Consultation";

  // natural language fallback from user prompt
  const cleaned = text
    .replace(/^(i have|i am having|having|what is|why do i have|can you tell me about)\s+/i, "")
    .trim();

  return cleaned
    .split(" ")
    .slice(0,5)
    .map(w=>w.charAt(0).toUpperCase()+w.slice(1))
    .join(" ") || "Health Consultation";
};

 
// ─── Types ─────────────────────────────────────────────────────────────────────
type Message = { id: string; role: "user" | "assistant"; content: string; time: string };
type Chat    = { id: string; title: string; messages: Message[] };

type BodyZone = "Head" | "Chest" | "Abdomen" | "Arms" | "Legs" | null;
 
// ─── OrbitalRing component ─────────────────────────────────────────────────────
function OrbitalRing({ onStartChat }: { onStartChat: () => void }) {
  return (
    <div
      style={{
        position: "relative",
        width: 450,
        height: 500,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      {/* Avatar circle — swap img src with your real doctor PNG */}
      <div
        onClick={onStartChat}
        style={{
          position: "relative",
          width: 360,
          height: 460,
          borderRadius: "0px",
          background: "transparent",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          zIndex: 5,
          flexShrink: 0,
          cursor: "pointer",
          filter: "drop-shadow(0 14px 26px rgba(59,130,246,.12))",
          transform: "translateY(-6px)",
          animation: "avatarFloat 4.8s ease-in-out infinite, avatarGlow 5.5s ease-in-out infinite",
        }}
      >
        <img
          src="/avatar-doctor.png"
          alt="Doctor Avatar"
          onError={(e) => {
            (e.target as HTMLImageElement).src =
              "https://cdn-icons-png.flaticon.com/512/387/387561.png";
          }}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
        />
      </div>
    </div>
  );
}
 
// ─── Main Page ─────────────────────────────────────────────────────────────────
useGLTF.preload('/human_body.glb');
useGLTF.preload('/models/z_skeleton.glb');

export default function Home() {
  const [input, setInput]               = useState("");
  const [chats, setChats]               = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [loading, setLoading]           = useState(false);
  const [showHome, setShowHome]         = useState(true);
  const [showLearnMore, setShowLearnMore] = useState(false);
  const [selectedZone, setSelectedZone] = useState<BodyZone>(null);
  const [showModelViewer, setShowModelViewer] = useState(false);
  const [anatomyLayer, setAnatomyLayer] = useState<'surface'|'skeleton'|'organs'>('surface');
  // Hinglish and file upload state
  const [useHinglish, setUseHinglish] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
 
  // ── Voice Input (Speech-to-Text) ───────────────────────────────────────────
  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      let chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        chunks.push(e.data);
      };

      mediaRecorder.onstart = () => {
        console.log("🎤 Recording...");
      };

      mediaRecorder.onstop = async () => {
        console.log("🎤 Recording stopped");

        const audioBlob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", audioBlob, "voice.webm");

        try {
          const res = await fetch("http://127.0.0.1:8000/voice", {
            method: "POST",
            body: formData,
          });

          const data = await res.json();

          if (data.text) {
            setInput(data.text);
          } else {
            alert("Could not understand voice. Try again.");
          }
        } catch (err) {
          console.error("Voice API error", err);
          alert("Voice processing failed.");
        }
      };

      mediaRecorder.start();

      // Stop after 3 seconds (simple demo)
      setTimeout(() => {
        mediaRecorder.stop();
        stream.getTracks().forEach((track) => track.stop());
      }, 3000);

    } catch (err) {
      console.error("Mic error", err);
      alert("Microphone access failed.");
    }
  };

  // ── Persist ────────────────────────────────────────────────────────────────
  useEffect(() => {
    const savedChats  = localStorage.getItem("medi_ai_chats");
    const savedActive = localStorage.getItem("medi_ai_active_chat");
    if (savedChats) {
      const parsed: Chat[] = JSON.parse(savedChats);
      setChats(parsed);
      if (savedActive && parsed.some((c) => c.id === savedActive)) setActiveChatId(savedActive);
      else if (parsed.length > 0) setActiveChatId(parsed[0].id);
    }
  }, []);
 
  useEffect(() => {
    localStorage.setItem("medi_ai_chats", JSON.stringify(chats));
    if (activeChatId) localStorage.setItem("medi_ai_active_chat", activeChatId);
  }, [chats, activeChatId]);
 
  useEffect(() => {
    if (chats.length === 0) return;
    if (!activeChatId || !chats.find((c) => c.id === activeChatId))
      setActiveChatId(chats[0].id);
  }, [chats]);
 
  const activeChat = chats.find((c) => c.id === activeChatId);
  const messages   = activeChat?.messages || [];
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // 🔥 stable sendMessage reference for anatomy events
  const sendMessageRef = useRef<((forcedText?: string) => void) | null>(null);

  // 🔥 Listen for anatomy clicks and auto-send to AI
  useEffect(() => {
    const handler = (event: any) => {
      const text = event.detail;

      if (!text) return;

      // open chat automatically
      setShowHome(false);
      setShowModelViewer(true);

      // auto-fill input
      setInput(text);

      // auto-send after short delay
      setTimeout(() => {
        sendMessageRef.current?.(text);
      }, 300);
    };

    window.addEventListener("anatomy-click", handler);

    return () => {
      window.removeEventListener("anatomy-click", handler);
    };
  }, []);

  useEffect(() => {
    if (!showHome) {
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [activeChatId, showHome]);
 
  // ── Actions ────────────────────────────────────────────────────────────────
  const createNewChat = useCallback(() => {
    const c: Chat = { id: uid(), title: "New Consultation", messages: [] };
    setChats((p) => [c, ...p]);
    setActiveChatId(c.id);
    setTimeout(() => inputRef.current?.focus(), 120);
  }, []);
 
  const deleteChat = useCallback((id: string) => {
    setChats((p) => p.filter((c) => c.id !== id));
    if (id === activeChatId) {
      setActiveChatId(null);
      localStorage.removeItem("medi_ai_active_chat");
    }
  }, [activeChatId]);
 
  const sendMessage = useCallback(async (forcedText?: string) => {
    const finalInput = forcedText || input;
    if (!finalInput.trim()) return;

    const userText = finalInput;
    // --- Auto region detection based on symptom keywords
    const lowerSymptom = userText.toLowerCase();
    if (lowerSymptom.includes('chest') || lowerSymptom.includes('heart') || lowerSymptom.includes('breath')) { setSelectedZone('Chest'); setShowModelViewer(true); }
    else if (lowerSymptom.includes('head') || lowerSymptom.includes('headache') || lowerSymptom.includes('migraine') || lowerSymptom.includes('dizzy')) { setSelectedZone('Head'); setShowModelViewer(true); }
    else if (lowerSymptom.includes('stomach') || lowerSymptom.includes('abdomen') || lowerSymptom.includes('belly') || lowerSymptom.includes('nausea')) { setSelectedZone('Abdomen'); setShowModelViewer(true); }
    else if (lowerSymptom.includes('arm') || lowerSymptom.includes('shoulder') || lowerSymptom.includes('hand')) { setSelectedZone('Arms'); setShowModelViewer(true); }
    else if (lowerSymptom.includes('leg') || lowerSymptom.includes('knee') || lowerSymptom.includes('foot')) { setSelectedZone('Legs'); setShowModelViewer(true); }
    // 🔥 Auto-detect Hinglish based on input
    const isHinglishInput = /\b(hai|ka|ke|ki|me|mera|mujhe|dard|sir|pet|kya|kyu|kyun|nahi)\b/i.test(userText);
    const userMsg: Message = {
      id:   uid(),
      role: "user",
      content: userText,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    let chatId = activeChatId;
    if (!chatId) {
      const nc: Chat = { id: uid(), title: generateTitle(userText), messages: [] };
      setChats((p) => [nc, ...p]);
      chatId = nc.id;
      setActiveChatId(chatId);
    }

    setChats((p) =>
      p.map((c) =>
        c.id !== chatId ? c
          : c.messages.some((m) => m.id === userMsg.id) ? c
          : { ...c, messages: [...c.messages, userMsg] }
      )
    );
    setInput("");
    setLoading(true);

    try {
      await new Promise((r) => setTimeout(r, 800 + Math.random() * 800));

      // Use latest messages for the current chat (including report uploads etc)
      const latestChat = chats.find(c => c.id === chatId);
      const currentMessages = latestChat ? [...latestChat.messages, userMsg] : [userMsg];

      // detect advanced intent from user message
      const advRegex = /\b(detailed|advanced|full|deep|complete|explain fully)\b/i;
      const isAdvanced = advRegex.test(userText);

      const res  = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          text: userText, 
          history: currentMessages, 
          body_region: selectedZone, 
          anatomical_mode: true, 
          hinglish: isHinglishInput,
          mode: isAdvanced ? "advanced" : "simple"
        }),
      });
      const data = await res.json();

      // soften rigid backend phrasing
      if (data.chat) {
        data.chat = String(data.chat)
          .replace(/Understanding the Issue:/g,"Understanding:")
          .replace(/When to Seek Help:/g,"When to get checked:")
          .replace(/You should/g,"You may want to")
          .replace(/must/g,"may need to");
      }

      // smarter title update from backend only if meaningful
      if (chatId) {
        const incomingTitle = String(data.title || "").trim();
        setChats((p) =>
          p.map((c) => {
            if (c.id !== chatId) return c;
            const genericTitles = ["Health Consultation","General Health Consultation","New Chat"];
            if (incomingTitle && !genericTitles.includes(incomingTitle)) {
              return { ...c, title: incomingTitle };
            }
            if (genericTitles.includes(c.title)) {
              return { ...c, title: generateTitle(userText) };
            }
            return c;
          })
        );
      }

      // Severity banner
      const low = userText.toLowerCase();
      const isHigh = ["chest pain","shortness of breath","cannot breathe","fainted","unconscious","severe bleeding","vision loss","paralysis","stroke"].some((k) => low.includes(k));
      const isMed  = ["persistent pain","high fever","vomiting","dizziness","infection","swelling"].some((k) => low.includes(k));
      const banner = isHigh
        ? "\n\n⚠️ This could be a serious condition. Please seek immediate medical attention."
        : isMed
        ? "\n\n⚠️ This may require attention if it persists. Consider consulting a doctor."
        : "";

      // Warmer, less robotic assistant response
      const introOptions = [
        "Based on what you described, here's what it may suggest:",
        "I looked at your symptoms — here's a practical interpretation:",
        "From what you've shared, this could be related to the following:",
      ];

      const careOptions = [
        "Monitor how symptoms evolve and seek medical care if they worsen or persist.",
        "Supportive care may help, and a clinician should evaluate it if symptoms continue.",
        "Keep an eye on changes and consider medical evaluation if it does not improve."
      ];

      const intro = introOptions[Math.floor(Math.random()*introOptions.length)];
      const care = careOptions[Math.floor(Math.random()*careOptions.length)];

      const finalText =
        `${intro}\n\n${String(data.chat).replace(/Possible Causes:/g,'Possible causes:').replace(/What You Can Do:/g,'Helpful next steps:')}\n\nGuidance:\n${care}${banner}`;

      const aiMsg: Message = {
        id: uid(), role: "assistant", content: "",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setChats((p) =>
        p.map((c) =>
          c.id === chatId ? { ...c, messages: [...c.messages, aiMsg] } : c
        )
      );

      // Word-by-word streaming
      let temp = "";
      for (const word of finalText.split(" ")) {
        temp += word + " ";
        await new Promise((r) => setTimeout(r, 45));
        setChats((p) =>
          p.map((c) =>
            c.id === chatId
              ? { ...c, messages: c.messages.map((m) => m.id === aiMsg.id ? { ...m, content: temp + "▌" } : m) }
              : c
          )
        );
      }
      // Remove cursor
      setChats((p) =>
        p.map((c) =>
          c.id === chatId
            ? { ...c, messages: c.messages.map((m) => m.id === aiMsg.id ? { ...m, content: temp } : m) }
            : c
        )
      );
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  }, [input, activeChatId, chats]);

  // keep latest sendMessage accessible outside render cycle
  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);
 
  const goToChat = useCallback(() => {
    setShowHome(false);
    setTimeout(() => inputRef.current?.focus(), 180);
  }, []);
 
  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen w-full">
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        @keyframes avatarFloat {
          0%   { transform: translateY(0px) scale(1); }
          50%  { transform: translateY(-8px) scale(1.01); }
          100% { transform: translateY(0px) scale(1); }
        }

        @keyframes avatarGlow {
          0%   { filter: drop-shadow(0 12px 22px rgba(59,130,246,.10)); }
          50%  { filter: drop-shadow(0 18px 34px rgba(56,189,248,.22)); }
          100% { filter: drop-shadow(0 12px 22px rgba(59,130,246,.10)); }
        }
      `}</style>
 
      {showHome ? (
        /* ══════════════════════ HOME ══════════════════════ */
        <div className="min-h-screen flex flex-col items-center justify-start text-center bg-gradient-to-br from-[#DDDFEE] via-[#cfd5f5] to-[#bfc7f0] relative overflow-hidden">
 
          {/* Dot pattern */}
          <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#000_1px,transparent_1px)] [background-size:20px_20px]" />
 
          {/* Navbar */}
          <div className="absolute top-0 w-full flex justify-center items-center px-10 py-4">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-widest bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 text-transparent bg-clip-text">
              MEDI AI
            </h1>
          </div>
 
          {/* Hero */}
          <div className="z-10 flex items-center justify-between w-full max-w-6xl px-12 pt-14 pb-2 min-h-[540px]">
 
            {/* Left text */}
            <div className="text-left -mt-2">
              <h2 className="text-[#3b82f6] font-semibold mb-2">Hey, I am Medi AI</h2>
              <h1 className="text-6xl font-extrabold mb-4 leading-tight text-[#1e293b] tracking-tight">
                Smart <span className="text-emerald-400">Health</span><br />Assistant
              </h1>
              <p className="text-[#475569] max-w-md mb-6">
                Describe your symptoms and get intelligent, structured guidance instantly.
              </p>
              <div className="flex gap-4">
                <button
                  onClick={goToChat}
                  className="bg-gradient-to-r from-cyan-400 to-blue-500 px-8 py-3 rounded-full text-white font-semibold hover:scale-105 transition shadow-lg"
                >
                  Start Chat →
                </button>
                <button
                  onClick={() => {
                    setShowLearnMore(true);
                    setTimeout(() => {
                      document.getElementById('learn-more-section')?.scrollIntoView({behavior:'smooth'});
                    }, 100);
                  }}
                  className="border border-[#3b82f6] text-[#3b82f6] px-8 py-3 rounded-full hover:bg-[#3b82f6] hover:text-white transition"
                >
                  Learn More
                </button>
              </div>
            </div>
 
            {/* Right — orbital ring */}
            <OrbitalRing onStartChat={goToChat} />
          </div>
 
          {/* Feature cards */}
          <div className="mt-4 mb-10 w-full flex justify-center gap-6 px-10">
            {[
              { icon: "🧠", title: "Smart Analysis",   desc: "AI analyzes symptoms like a real doctor." },
              { icon: "🔍", title: "Possible Causes",  desc: "Get likely conditions, not random guesses." },
              { icon: "🛡️", title: "Safe Guidance",    desc: "No unsafe advice, only structured help." },
            ].map((card) => (
              <div key={card.title} className="bg-white/40 backdrop-blur-lg p-5 rounded-xl shadow-md w-56 text-left flex gap-3 items-start">
                <span style={{ fontSize: 22 }}>{card.icon}</span>
                <div>
                  <h3 className="font-semibold text-[#1e293b]">{card.title}</h3>
                  <p className="text-sm text-[#475569] mt-1">{card.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {showLearnMore && (
            <section
              id="learn-more-section"
              className="w-full max-w-6xl px-10 pb-16 mt-6 z-10"
              style={{animation:'fadeIn .5s ease'}}
            >
              <div className="bg-white/45 backdrop-blur-xl rounded-3xl shadow-xl p-10 border border-white/30">
                <h2 className="text-4xl font-bold text-[#1e293b] mb-6">
                  How Medi AI Helps
                </h2>

                <div className="grid md:grid-cols-3 gap-6 mb-8">
                  <div className="bg-white/50 rounded-2xl p-6 shadow-sm">
                    <h3 className="font-semibold text-xl mb-3">🩺 Symptom Reasoning</h3>
                    <p className="text-[#475569]">Structured symptom analysis, possible causes, risk cues, and safe guidance.</p>
                  </div>
                  <div className="bg-white/50 rounded-2xl p-6 shadow-sm">
                    <h3 className="font-semibold text-xl mb-3">🤖 AI Assistance</h3>
                    <p className="text-[#475569]">Interactive follow-up questions, explanation levels, and intelligent health support.</p>
                  </div>
                  <div className="bg-white/50 rounded-2xl p-6 shadow-sm">
                    <h3 className="font-semibold text-xl mb-3">🔬 Research Support</h3>
                    <p className="text-[#475569]">Helpful for medical learning, idea exploration, literature support, and research inspiration.</p>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-2xl p-6 border border-cyan-100">
                  <h3 className="text-2xl font-semibold mb-3 text-[#1e293b]">Key Features</h3>
                  <ul className="space-y-2 text-[#475569]">
                    <li>• Smart symptom interpretation</li>
                    <li>• Possible cause exploration</li>
                    <li>• Safety-aware medical guidance</li>
                    <li>• Conversation memory across chats</li>
                    <li>• Interactive 3D human model visualization support</li>
                  </ul>
                </div>
              </div>
            </section>
          )}
        </div>
 
      ) : (
        /* ══════════════════════ CHAT ══════════════════════ */
        <div className="h-screen flex bg-gradient-to-br from-[#020617] via-[#020b1a] to-[#01030a] text-white">
 
          {/* Sidebar */}
          <div className="w-72 border-r border-white/10 p-4 flex flex-col bg-[#1E293B]">
            <button
              onClick={createNewChat}
              className="mb-4 bg-gradient-to-r from-cyan-400 to-blue-500 text-black p-3 rounded-xl font-semibold hover:scale-105 transition"
            >
              + New Chat
            </button>
 
            <div className="flex-1 overflow-y-auto space-y-2">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className={`p-3 rounded-xl cursor-pointer text-sm flex justify-between items-center transition-all duration-200 group ${
                    chat.id === activeChatId
                      ? "bg-[#334155] border border-[#6366F1]/30"
                      : "bg-[#1E293B] hover:bg-[#334155]"
                  }`}
                >
                  <span onClick={() => setActiveChatId(chat.id)} className="flex-1 truncate">
                    {chat.title}
                  </span>
                  <button
                    onClick={() => deleteChat(chat.id)}
                    className="text-red-400 text-xs ml-2 opacity-0 group-hover:opacity-100 transition"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
 
          {/* Chat area */}
          <div className="w-full flex p-6 gap-6 bg-[#0F172A]">
            <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 text-transparent bg-clip-text tracking-wide">
                Medi AI
              </h1>
              <div className="flex items-center">
                <button
                  onClick={() => setShowModelViewer(true)}
                  className="text-sm px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 hover:bg-cyan-500/30 transition mr-3"
                >
                  🫀 Open Anatomy Viewer
                </button>
                <button
                  onClick={() => setShowHome(true)}
                  className="text-sm px-4 py-2 rounded-lg bg-[#1E293B] border border-white/10 hover:bg-[#334155] transition"
                >
                  ← Home
                </button>
              </div>
            </div>
 
            <div className="flex-1 overflow-y-auto space-y-4 pt-4">
              {messages.length === 0 && (
                <div className="text-center text-[#94A3B8] mt-20">
                  <p className="text-lg">Start describing your symptoms</p>
                  <p className="text-sm mt-1">Medi AI will guide you step-by-step</p>
                  <p className="text-xs mt-4 text-cyan-300">Mention symptoms like chest pain or headache to auto-open the anatomy viewer.</p>
                </div>
              )}
 
              {messages.map((msg) => {
                let displayContent = msg.content;

                // Only show Hinglish style if last user message was Hinglish
                if (msg.role === "assistant") {
                  const lastUserMsg = messages.slice().reverse().find(m => m.role === "user");
                  const wasHinglish = lastUserMsg && /\b(hai|ka|ke|ki|me|mera|mujhe|dard|sir|pet|kya|kyu|kyun|nahi)\b/i.test(lastUserMsg.content);
                  if (wasHinglish) {
                    let hinglishResponse = msg.content
                      // intro fixes
                      .replace(/Based on what you described,?/gi, "Aapke bataye hue symptoms ke hisaab se")
                      .replace(/here's what it may suggest:/gi, "yeh indicate karta hai:")
                      .replace(/this could be/gi, "yeh ho sakta hai")
                      .replace(/may be caused by/gi, "iska reason ho sakta hai")

                      // sections
                      .replace(/Understanding:/gi, "Samajhne ke liye:")
                      .replace(/Possible causes:/gi, "Possible reasons:")
                      .replace(/Helpful next steps:/gi, "Aap kya kar sakte ho:")
                      .replace(/When to get checked:/gi, "Kab doctor ko dikhaana chahiye:")
                      .replace(/Guidance:/gi, "Advice:")

                      // main fixes (clean Hinglish)
                      .replace(/Head pain/gi, "Sir me dard")
                      .replace(/pain/gi, "dard")
                      .replace(/various factors/gi, "kai reasons")
                      .replace(/minor injuries/gi, "chhoti injuries")
                      .replace(/essential to identify/gi, "zaroori hai samajhna")

                      // actions
                      .replace(/apply/gi, "laga sakte ho")
                      .replace(/stay hydrated/gi, "hydrated raho")
                      .replace(/drink water/gi, "paani piyo")
                      .replace(/practice/gi, "practice karo")
                      .replace(/maintain good posture/gi, "posture sahi rakho")
                      .replace(/take regular breaks/gi, "regular breaks lo")

                      // doctor + safety
                      .replace(/consult a healthcare professional/gi, "doctor ko consult karo")
                      .replace(/consult a doctor/gi, "doctor ko dikhao")
                      .replace(/this is general guidance/gi, "yeh general guidance hai")

                      // fix broken words from earlier
                      .replace(/factyas/gi, "reasons")
                      .replace(/minya/gi, "minor")
                      .replace(/doctya/gi, "doctor")
                      .replace(/monitya/gi, "monitor")
                      .replace(/wyasen/gi, "worsen")

                      // connectors
                      .replace(/including/gi, "jaise")
                      .replace(/ or /gi, " ya ")
                      .replace(/ and /gi, " aur ");

                    displayContent = `🗣️ Hinglish Mode\n\n${hinglishResponse}`;
                  }
                }

                return (
                <div
                  key={msg.id}
                  className={`flex items-end gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 flex items-center justify-center text-xl">🧠</div>
                  )}
 
                  <div
                    className={`max-w-[60%] px-4 py-3 rounded-2xl shadow-md ${
                      msg.role === "user"
                        ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg"
                        : "bg-[#1E293B] border border-cyan-400/10 text-[#E2E8F0] shadow-lg leading-7"
                    }`}
                    style={{ animation: "fadeIn 0.4s ease" }}
                  >
                    <div className="whitespace-pre-wrap space-y-2">
                      {displayContent.split("\n").map((line, idx) => {
                        if (line.toLowerCase().includes("future risks")) {
                          return <div key={idx} className="text-red-400 font-semibold">🔮 {line}</div>;
                        }
                        if (
                          line.toLowerCase().includes("doctor suggestion") ||
                          line.toLowerCase().includes("cardiologist") ||
                          line.toLowerCase().includes("neurologist") ||
                          line.toLowerCase().includes("physician") ||
                          line.toLowerCase().includes("dermatologist")
                        ) {
                          return (
                            <div
                              key={idx}
                              className="text-cyan-400 font-semibold cursor-pointer hover:underline"
                              onClick={() => {
                                const followUp = "Why should I consult this doctor?";
                                setInput(followUp);
                                setTimeout(() => sendMessage(), 100);
                              }}
                            >
                              🩺 {line}
                            </div>
                          );
                        }
                        if (line.toLowerCase().includes("abnormal")) {
                          return <div key={idx} className="text-yellow-400 font-semibold">⚠️ {line}</div>;
                        }
                        if (line.toLowerCase().includes("precautions")) {
                          return <div key={idx} className="text-green-400 font-semibold">✅ {line}</div>;
                        }
                        return <div key={idx}>{line}</div>;
                      })}
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1 text-right opacity-70">{msg.time}</div>
                    {msg.role === "assistant" && (
                      <div className="text-xs text-gray-400 mt-2">
                        General health guidance — consult a medical professional for diagnosis.
                      </div>
                    )}
                  </div>
 
                  {msg.role === "user" && (
                    <div className="w-8 h-8 flex items-center justify-center text-lg">🙂</div>
                  )}
                </div>
                );
              })}
 
              {loading && (
                <div className="flex items-center gap-3 bg-white/5 px-4 py-3 rounded-2xl w-fit border border-white/10">
                  <span className="text-sm text-[#22D3EE]">Medi AI is thinking through your symptoms</span>
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-[#22D3EE] rounded-full animate-pulse" />
                    <span className="w-2 h-2 bg-[#22D3EE] rounded-full animate-pulse delay-150" />
                    <span className="w-2 h-2 bg-[#22D3EE] rounded-full animate-pulse delay-300" />
                  </div>
                </div>
              )}
 
              <div ref={chatEndRef} />
            </div>
 
            {useHinglish && (
              <div className="text-xs text-emerald-300 mb-2 ml-2">
                Responding in Hinglish mode
              </div>
            )}
            {/* Input bar */}
            <div className="flex gap-2 mt-4 bg-[#1E293B] p-3 rounded-2xl border border-white/10">
              {/* Upload button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 transition"
              >
                📷
              </button>
              {/* Hidden file input */}
              <input
                type="file"
                accept="image/jpeg,image/jpg,image/png,application/pdf"
                ref={fileInputRef}
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;

                  // show user upload message
                  const userMsg: Message = {
                    id: uid(),
                    role: "user",
                    content: "📄 Report uploaded: " + file.name,
                    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                  };

                  setChats((p) =>
                    p.map((c) =>
                      c.id === activeChatId
                        ? { ...c, messages: [...c.messages, userMsg] }
                        : c
                    )
                  );

                  // prepare form data
                  const formData = new FormData();
                  formData.append("file", file);

                  try {
                    // detect advanced intent from current input
                    const advRegex = /\b(detailed|advanced|full|deep|complete|explain fully)\b/i;
                    const isAdvanced = advRegex.test(input);

                    const url = isAdvanced
                      ? "http://127.0.0.1:8000/analyze-report?mode=advanced"
                      : "http://127.0.0.1:8000/analyze-report";

                    const res = await fetch(url, {
                      method: "POST",
                      body: formData,
                    });

                    let data;
                    try {
                      data = await res.json();
                    } catch {
                      data = { summary: "Image analysis currently limited. Please upload a PDF report for better results." };
                    }

                    const aiMsg: Message = {
                      id: uid(),
                      role: "assistant",
                      content: "📊 Report Analysis:\n\n" + (data.summary || "Report analyzed successfully."),
                      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    };

                    setChats((p) =>
                      p.map((c) =>
                        c.id === activeChatId
                          ? { ...c, messages: [...c.messages, aiMsg] }
                          : c
                      )
                    );
                  } catch (err) {
                    console.error(err);
                  }
                }}
              />
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    sendMessage();
                  }
                }}
                placeholder="Describe your symptom..."
                className="flex-1 p-3 rounded-xl bg-transparent outline-none placeholder-[#94A3B8] text-[#E2E8F0]"
              />
              <button
                onClick={startListening}
                className="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 transition"
                title="Voice input"
              >
                🎤
              </button>
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim()}
                className={`px-6 rounded-xl font-semibold transition shadow-md ${
                  input.trim()
                    ? "bg-[#6366F1] text-white hover:scale-105"
                    : "bg-gray-700 text-gray-400 cursor-not-allowed"
                }`}
              >
                Send
              </button>
              {/* Hinglish toggle */}
              <button
                onClick={() => setUseHinglish(v => !v)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  useHinglish
                    ? 'bg-gradient-to-r from-emerald-400 to-green-500 text-black shadow-md'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {useHinglish ? '🇮🇳 Hinglish ON' : '🌐 English'}
              </button>
            </div>
            </div>
          </div>
          {/* Modal 3D Anatomy Viewer */}
          {showModelViewer && (
            <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6">
              <div className="w-full max-w-6xl h-[88vh] bg-[#0F172A] rounded-3xl border border-cyan-400/20 shadow-2xl relative overflow-hidden pt-20">

                <button
                  onClick={() => setShowModelViewer(false)}
                  className="absolute top-6 right-10 z-50 px-4 py-2 rounded-xl bg-[#1E293B] hover:bg-[#334155]"
                >
                  ✕ Close
                </button>

                <div className="absolute top-6 left-10 z-50">
                  <h2 className="text-2xl font-bold text-cyan-300">3D Anatomy Viewer</h2>
                  <p className="text-sm text-slate-400 mt-1">Interactive symptom visualization</p>
                </div>

                <div className="w-full h-full flex items-start justify-center px-10 pb-10">
                  <AnatomyViewer
                    key={selectedZone || "default"}
                    selected={selectedZone}
                    onSelect={setSelectedZone}
                  />
                </div>

              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}