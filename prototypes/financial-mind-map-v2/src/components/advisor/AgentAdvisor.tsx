// FinancialMindMap — Agent Advisor ("Chip"): Cleo-style conversational planning.
// Mascot thinks (money/stocks/coins/loans orbit overhead) → snaps fingers → plan appears.
import React, { useEffect, useRef, useState } from 'react';
import {
  Sparkles, Send, BookOpen, Target, TrendingUp, Coins, Home, Heart, Plane,
  Rocket, Compass, CreditCard, Palmtree, CheckCircle2, AlertTriangle, Save,
} from 'lucide-react';
import { AdvisorEngine, GOALS, Plan, money, pct, GoalType } from '../../lib/advisor';
import { GUIDES } from '../../data/guides';
import { Mascot3D, MascotHandle } from '../mascot/Mascot3D';
import { useFinanceContext } from '../../context/FinanceContext';

interface AgentAdvisorProps {
  initialAsk?: string | null;
  onOpenGuide: (slug: string) => void;
}

interface ChatMsg {
  id: number;
  who: 'me' | 'chip';
  text: string;
  plan?: Plan;
  card?: 'greeting' | 'budget';
}

const GOAL_ICONS: Record<GoalType, React.ComponentType<{ className?: string }>> = {
  vacation: Plane, wedding: Heart, home: Home, retirement: Palmtree,
  business: Rocket, crypto: Coins, invest: TrendingUp, budget: Compass, debt: CreditCard,
};

const ALLOC_COLORS = ['#3D9EFF', '#2ECC71', '#FDE047', '#FF4D6A'];

const PlanCard: React.FC<{ plan: Plan; onSaveGoal: (p: Plan) => void; onOpenGuide: (slug: string) => void }> = ({ plan, onSaveGoal, onOpenGuide }) => {
  const GoalIcon = GOAL_ICONS[plan.goal.key];
  return (
    <div className="mt-2.5 rounded-2xl bg-[#06101E]/95 border border-[#1E3352] overflow-hidden">
      <div className="flex items-center space-x-3 px-4 py-3 border-b border-[#1E3352]">
        <div className="w-10 h-10 rounded-xl grid place-items-center" style={{ backgroundColor: plan.goal.color + '22', color: plan.goal.color }}>
          <GoalIcon className="w-5 h-5" />
        </div>
        <div>
          <div className="text-sm font-black text-white">{plan.goal.label} plan</div>
          <div className="text-[10px] text-[#9BB5D6] font-semibold">
            {plan.years}-year horizon · {plan.risk.label} · ~{pct(plan.risk.ret)} assumed return
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3">
        {[
          [money(plan.target), 'Target'],
          [money(plan.gap), 'Left to fund'],
          [money(plan.monthlyNeeded), 'Needed / month'],
          [money(plan.projected), 'Projected pot'],
        ].map(([n, l]) => (
          <div key={l} className="rounded-xl bg-[#0B1B33] border border-[#1E3352] px-2.5 py-2">
            <div className="text-sm font-black text-white">{n}</div>
            <div className="text-[9px] text-[#9BB5D6] font-bold uppercase tracking-wider">{l}</div>
          </div>
        ))}
      </div>

      <div className="px-4 pb-2">
        <div className="text-[10px] font-black text-[#9BB5D6] uppercase tracking-wider mb-1.5">
          Suggested {plan.risk.label.toLowerCase()} allocation
        </div>
        {plan.risk.alloc.map(([name, v], i) => (
          <div key={name} className="flex items-center gap-2 text-[11px] text-[#C2D8F2] mb-1">
            <span className="w-32 sm:w-40 truncate">{name}</span>
            <div className="flex-1 h-2 rounded-full bg-[#0F2444] overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${v}%`, backgroundColor: ALLOC_COLORS[i] }} />
            </div>
            <span className="w-8 text-right font-mono text-[#9BB5D6]">{v}%</span>
          </div>
        ))}
      </div>

      <div className="px-4 pb-2">
        <div className="text-[10px] font-black text-[#9BB5D6] uppercase tracking-wider mb-1">Milestones</div>
        {plan.milestones.map(m => (
          <div key={m.label} className="flex items-center gap-2 text-[11px] text-[#C2D8F2] py-0.5">
            <CheckCircle2 className="w-3 h-3 text-[#2ECC71] flex-shrink-0" />
            <span>{m.label} — <strong className="text-white">{money(m.value)}</strong></span>
          </div>
        ))}
      </div>

      {plan.onTrack ? (
        <div className="mx-4 mb-2 px-3 py-2 rounded-xl bg-[#2ECC71]/10 border border-[#2ECC71]/25 text-[11px] text-[#2ECC71] font-semibold">
          ✅ On track. Automate {money(plan.monthlyNeeded)}/month into this goal and you land on target.
        </div>
      ) : (
        <div className="mx-4 mb-2 px-3 py-2 rounded-xl bg-[#FDE047]/10 border border-[#FDE047]/25 text-[11px] text-[#FDE047] font-semibold flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>
            {plan.monthlyCapacity > 0 ? (
              <>At {money(plan.monthlyCapacity)}/month you reach {money(plan.target)} in about <strong>{plan.yearsNeeded ? `${plan.yearsNeeded.toFixed(1)} years` : '50+ years'}</strong>. Extend the timeline, grow the monthly amount, or trim the target.</>
            ) : (
              <>To hit {money(plan.target)} in {plan.years} years you need about <strong>{money(plan.monthlyNeeded)}/month</strong>. Tell me your real numbers and I will re-plan.</>
            )}
          </span>
        </div>
      )}

      <div className="flex flex-wrap gap-2 px-4 pb-3 pt-1">
        <button
          onClick={() => onSaveGoal(plan)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#FDE047] hover:bg-[#FEF08A] text-[#06101E] text-[11px] font-black transition-colors"
        >
          <Save className="w-3 h-3" /> Save & track goal
        </button>
        <button
          onClick={() => onOpenGuide(plan.goal.guide)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0F2444] hover:bg-[#132E56] text-white hover:text-[#FDE047] text-[11px] font-bold transition-colors"
        >
          <BookOpen className="w-3 h-3" /> Read the {plan.goal.label.toLowerCase()} guide
        </button>
      </div>
    </div>
  );
};

const BudgetCard: React.FC<{ onOpenGuide: (slug: string) => void }> = ({ onOpenGuide }) => (
  <div className="mt-2.5 rounded-2xl bg-[#06101E]/95 border border-[#1E3352] p-3.5">
    <div className="text-[10px] font-black text-[#9BB5D6] uppercase tracking-wider mb-1.5">Starter budget split</div>
    {[['Needs', 50, '#3D9EFF'], ['Wants', 30, '#2ECC71'], ['Future you', 20, '#FDE047']].map(([n, v, c]) => (
      <div key={n as string} className="flex items-center gap-2 text-[11px] text-[#C2D8F2] mb-1">
        <span className="w-24">{n as string}</span>
        <div className="flex-1 h-2 rounded-full bg-[#0F2444] overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${v}%`, backgroundColor: c as string }} />
        </div>
        <span className="w-8 text-right font-mono text-[#9BB5D6]">{v}%</span>
      </div>
    ))}
    <button onClick={() => onOpenGuide('budgeting')} className="mt-2 text-[11px] font-bold text-[#3D9EFF] hover:underline flex items-center gap-1">
      <BookOpen className="w-3 h-3" /> Budgeting guide
    </button>
  </div>
);

const GreetingCard: React.FC<{ onOpenGuide: (slug: string) => void; onNavigateGoals: () => void }> = ({ onOpenGuide, onNavigateGoals }) => (
  <div className="mt-2.5 rounded-2xl bg-[#06101E]/95 border border-[#1E3352] p-3.5">
    <div className="text-[10px] font-black text-[#9BB5D6] uppercase tracking-wider mb-2">Explore</div>
    <div className="flex flex-wrap gap-2">
      <button onClick={onNavigateGoals} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0F2444] hover:bg-[#132E56] text-white text-[11px] font-bold transition-colors">
        <Target className="w-3 h-3" /> Goal planners
      </button>
      <button onClick={() => onOpenGuide('investing')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0F2444] hover:bg-[#132E56] text-white text-[11px] font-bold transition-colors">
        <TrendingUp className="w-3 h-3" /> Investment guide
      </button>
      <button onClick={() => onOpenGuide('budgeting')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0F2444] hover:bg-[#132E56] text-white text-[11px] font-bold transition-colors">
        <Compass className="w-3 h-3" /> Budget playbook
      </button>
    </div>
  </div>
);

export const AgentAdvisor: React.FC<AgentAdvisorProps> = ({ initialAsk, onOpenGuide }) => {
  const { addGoal } = useFinanceContext();
  const mascotRef = useRef<MascotHandle>(null);
  const engineRef = useRef<AdvisorEngine>(new AdvisorEngine());
  const logRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(1);
  const busyRef = useRef(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [chips, setChips] = useState<string[]>([]);
  const askHandled = useRef<string | null>(null);

  const push = (m: Omit<ChatMsg, 'id'>) => setMsgs(prev => [...prev, { ...m, id: idRef.current++ }]);

  const send = (text: string) => {
    const t = text.trim();
    if (!t || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setChips([]);
    push({ who: 'me', text: t });
    setInput('');
    mascotRef.current?.think(); // 💰📈🪙💳 spin over its head

    const wait = 700 + Math.min(1400, t.length * 22);
    window.setTimeout(() => {
      const reply = engineRef.current.process(t);
      mascotRef.current?.snap(); // ✨ fingers snap — answer ready
      window.setTimeout(() => {
        push({ who: 'chip', text: reply.text, plan: reply.plan, card: reply.card });
        setChips(reply.chips ?? []);
        setBusy(false);
        busyRef.current = false;
      }, 340);
    }, wait);
  };

  // opening message
  useEffect(() => {
    const greet = engineRef.current.greet();
    push({ who: 'chip', text: greet.text, card: greet.card });
    setChips(greet.chips ?? []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // deep link: ask from guides / goals
  useEffect(() => {
    if (initialAsk && askHandled.current !== initialAsk) {
      askHandled.current = initialAsk;
      send(initialAsk);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialAsk]);

  // autoscroll
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
  }, [msgs, busy]);

  const saveGoal = (plan: Plan) => {
    addGoal({
      title: `${plan.goal.emoji} ${plan.goal.label}`,
      target: plan.target,
      current: plan.saved,
      deadline: new Date(Date.now() + plan.years * 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
      icon: plan.goal.icon,
      color: plan.goal.color,
    });
    push({
      who: 'chip',
      text: `🎉 Saved <strong>${plan.goal.label}</strong> to your Goals board — I’ll cheer every deposit. (Find it in the Goals tab.)`,
    });
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Mascot stage */}
        <div className="relative w-full lg:w-[340px] h-[300px] lg:h-auto lg:min-h-[540px] rounded-3xl overflow-hidden bg-gradient-to-br from-[#0B1B33] via-[#123059] to-[#1E3352] border border-[#1E3352] shadow-[0_10px_40px_rgba(0,0,0,0.5)] flex-shrink-0">
          <div className="absolute top-3 left-3 flex gap-1.5 z-10 flex-wrap">
            {['💬 AI advisor', '🎯 Goal maps', '🪙 3D mascot'].map(b => (
              <span key={b} className="px-2.5 py-1 rounded-full bg-white/10 border border-white/20 text-white text-[10px] font-bold backdrop-blur">{b}</span>
            ))}
          </div>
          <Mascot3D ref={mascotRef} />
          <div className="absolute bottom-0 inset-x-0 z-10 p-4 bg-gradient-to-t from-[#02060f]/80 to-transparent">
            <div className="text-white font-black">Meet Chip 🦉</div>
            <div className="text-[11px] text-[#C2D8F2] leading-snug">
              Money, stocks, coins & loans spin over its head while it plans — and it <em>snaps its fingers</em> the moment your answer is ready.
            </div>
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col rounded-3xl bg-[#0B1B33]/95 border border-[#1E3352] shadow-[0_10px_40px_rgba(0,0,0,0.5)] overflow-hidden min-h-[520px] max-h-[78vh]">
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-[#1E3352]">
            <div className="w-8 h-8 rounded-xl bg-[#FDE047] text-[#06101E] grid place-items-center shadow-[0_0_12px_rgba(253,224,71,0.4)]">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-black text-white">Chip · AI Financial Advisor</div>
              <div className="text-[10px] text-[#9BB5D6] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2ECC71] animate-pulse" /> plans · investments · goals
              </div>
            </div>
          </div>

          <div ref={logRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3.5">
            {msgs.map(m => (
              <div key={m.id} className={`flex ${m.who === 'me' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[88%] sm:max-w-[80%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                  m.who === 'me'
                    ? 'bg-gradient-to-r from-[#3D9EFF] to-[#59B0FF] text-white rounded-br-md'
                    : 'bg-[#06101E] text-[#C2D8F2] border border-[#1E3352] rounded-bl-md'
                }`}>
                  <span dangerouslySetInnerHTML={{ __html: m.text }} />
                  {m.plan && <PlanCard plan={m.plan} onSaveGoal={saveGoal} onOpenGuide={onOpenGuide} />}
                  {m.card === 'budget' && <BudgetCard onOpenGuide={onOpenGuide} />}
                  {m.card === 'greeting' && (
                    <GreetingCard
                      onOpenGuide={onOpenGuide}
                      onNavigateGoals={() => send('Help me build a budget plan')}
                    />
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md bg-[#06101E] border border-[#1E3352] px-3.5 py-2.5 text-[12px] text-[#9BB5D6] flex items-center gap-2">
                  <span className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <span key={i} className="w-1.5 h-1.5 rounded-full bg-[#3D9EFF] animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </span>
                  crunching numbers…
                </div>
              </div>
            )}
          </div>

          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 px-4 pb-2">
              {chips.map(c => (
                <button
                  key={c}
                  onClick={() => send(c)}
                  className="px-3 py-1.5 rounded-full bg-[#0F2444] border border-[#1E3352] hover:border-[#3D9EFF] text-[#C2D8F2] hover:text-white text-[11px] font-bold transition-colors"
                >
                  {c}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={e => { e.preventDefault(); send(input); }}
            className="flex items-center gap-2 px-3 py-2.5 border-t border-[#1E3352]"
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Tell me your goal — “wedding in 2 years”…"
              className="flex-1 rounded-2xl bg-[#06101E] border border-[#1E3352] focus:border-[#3D9EFF] px-4 py-2.5 text-[13px] text-white placeholder:text-[#5E7BA6] outline-none"
            />
            <button
              type="submit"
              className="w-10 h-10 rounded-2xl bg-[#FDE047] hover:bg-[#FEF08A] text-[#06101E] grid place-items-center shadow-[0_0_15px_rgba(253,224,71,0.3)] transition-colors"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export const ASK_CHIPS = Object.keys(GUIDES);
