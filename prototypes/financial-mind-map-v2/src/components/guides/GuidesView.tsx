// FinancialMindMap — Guides hub + sub-pages (playbooks that hand off to the advisor)
import React, { useEffect, useState } from 'react';
import { BookOpen, ChevronRight, Clock, ArrowLeft, Sparkles, ArrowRight, Link2 } from 'lucide-react';
import { GUIDES, GUIDE_LIST } from '../../data/guides';

interface GuidesViewProps {
  initialSlug?: string | null;
  onAskAdvisor: (ask: string) => void;
}

export const GuidesView: React.FC<GuidesViewProps> = ({ initialSlug, onAskAdvisor }) => {
  const [slug, setSlug] = useState<string | null>(initialSlug ?? null);

  useEffect(() => {
    if (initialSlug) setSlug(initialSlug);
  }, [initialSlug]);

  // ---------- sub-page ----------
  if (slug && GUIDES[slug]) {
    const g = GUIDES[slug];
    return (
      <div className="w-full max-w-4xl mx-auto space-y-6">
        <button
          onClick={() => setSlug(null)}
          className="flex items-center gap-1.5 text-xs font-bold text-[#9BB5D6] hover:text-[#FDE047] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> All guides
        </button>

        <header className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-[#0B1B33] border border-[#1E3352] grid place-items-center text-3xl">{g.emoji}</div>
            <div className="flex items-center gap-2 text-[10px]">
              <span className="px-2 py-0.5 rounded-full bg-[#FDE047]/15 text-[#FDE047] font-black uppercase tracking-wider border border-[#FDE047]/30">{g.tag}</span>
              <span className="flex items-center gap-1 text-[#9BB5D6] font-bold"><Clock className="w-3 h-3" /> {g.minutes} min read</span>
            </div>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white leading-tight">{g.title}</h1>
          <p className="text-sm sm:text-base text-[#9BB5D6] leading-relaxed max-w-2xl">{g.intro}</p>
        </header>

        <div className="space-y-5">
          {g.sections.map(s => (
            <section key={s.h} className="p-4 sm:p-5 rounded-2xl bg-[#0B1B33]/80 border border-[#1E3352]">
              <h2 className="text-base font-black text-white mb-1.5">{s.h}</h2>
              <p className="text-[13px] text-[#C2D8F2] leading-relaxed">{s.p}</p>
              {s.list && (
                <ul className="mt-2.5 space-y-1.5">
                  {s.list.map(l => (
                    <li key={l} className="flex items-start gap-2 text-[12.5px] text-[#9BB5D6]">
                      <ChevronRight className="w-3.5 h-3.5 text-[#3D9EFF] flex-shrink-0 mt-0.5" />
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>

        <section className="space-y-2">
          <h2 className="text-base font-black text-white">Quick questions</h2>
          {g.faq.map(f => (
            <details key={f.q} className="p-3.5 rounded-2xl bg-[#0B1B33]/80 border border-[#1E3352] group">
              <summary className="text-[13px] font-bold text-white cursor-pointer list-none flex items-center justify-between">
                {f.q}
                <ChevronRight className="w-3.5 h-3.5 text-[#9BB5D6] group-open:rotate-90 transition-transform" />
              </summary>
              <p className="mt-2 text-[12.5px] text-[#9BB5D6] leading-relaxed">{f.a}</p>
            </details>
          ))}
        </section>

        <div className="p-6 rounded-3xl bg-gradient-to-r from-[#3D9EFF] to-[#59B0FF] text-center shadow-[0_10px_40px_rgba(61,158,255,0.25)]">
          <div className="text-white font-black mb-1">Turn this guide into your plan</div>
          <p className="text-[12px] text-white/85 mb-3">Chip builds the numbers live — target, timeline, monthly amount and allocation.</p>
          <button
            onClick={() => onAskAdvisor(g.cta.ask)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-[#06101E] hover:bg-[#0B1B33] text-white text-xs font-black transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#FDE047]" /> {g.cta.label} <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <section className="space-y-2">
          <h2 className="text-base font-black text-white flex items-center gap-2"><Link2 className="w-4 h-4 text-[#3D9EFF]" /> Keep going</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {g.related.map(r => {
              const rg = GUIDES[r];
              return (
                <button
                  key={r}
                  onClick={() => setSlug(r)}
                  className="p-3.5 rounded-2xl bg-[#0B1B33]/80 border border-[#1E3352] hover:border-[#3D9EFF] text-left transition-colors"
                >
                  <div className="text-2xl mb-1">{rg.emoji}</div>
                  <div className="text-[12px] font-bold text-white leading-snug">{rg.title}</div>
                </button>
              );
            })}
          </div>
        </section>
      </div>
    );
  }

  // ---------- hub ----------
  return (
    <div className="w-full space-y-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-black text-white">
          📚 Guides & <span className="text-[#FDE047]">Playbooks</span>
        </h1>
        <p className="text-sm text-[#9BB5D6] mt-1 max-w-2xl">
          Short, practical sub-pages that pair with Chip, your AI advisor. Every guide ends with a one-tap handoff into a live plan.
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {GUIDE_LIST.map(g => (
          <button
            key={g.slug}
            onClick={() => setSlug(g.slug)}
            className="p-5 rounded-3xl bg-[#0B1B33]/90 border border-[#1E3352] hover:border-[#3D9EFF] hover:-translate-y-0.5 transition-all text-left group"
          >
            <div className="w-12 h-12 rounded-2xl bg-[#06101E] border border-[#1E3352] grid place-items-center text-2xl mb-3">{g.emoji}</div>
            <span className="px-2 py-0.5 rounded-full bg-[#FDE047]/15 text-[#FDE047] text-[9px] font-black uppercase tracking-wider border border-[#FDE047]/30">{g.tag}</span>
            <h3 className="text-sm font-black text-white mt-2 leading-snug">{g.title}</h3>
            <p className="text-[12px] text-[#9BB5D6] mt-1.5 leading-relaxed line-clamp-3">{g.intro}</p>
            <div className="flex items-center gap-2 mt-3 text-[11px] font-bold text-[#3D9EFF]">
              <BookOpen className="w-3 h-3" /> Read · {g.minutes} min
              <ChevronRight className="w-3 h-3 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
