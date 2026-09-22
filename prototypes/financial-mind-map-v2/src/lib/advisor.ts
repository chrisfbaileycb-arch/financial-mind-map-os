// FinancialMindMap — Agent advisor engine (planning math + conversational intents)
// Pure client-side. Swap `process()` for a backend LLM call later — the return
// shape ({ text, plan, chips }) is all the UI needs.

export type GoalType =
  | 'vacation' | 'wedding' | 'home' | 'retirement'
  | 'business' | 'crypto' | 'invest' | 'budget' | 'debt';

export type RiskKey = 'cautious' | 'balanced' | 'bold';

export interface GoalMeta {
  key: GoalType;
  emoji: string;
  label: string;
  horizon: number; // default years
  amount: number;  // default target
  guide: string;   // guide slug
  icon: string;    // lucide icon name used by goals
  color: string;
}

export interface RiskMeta {
  label: string;
  ret: number; // assumed annual return
  alloc: [string, number][];
}

export interface PlanInput {
  goalType: GoalType;
  target: number;
  years: number;
  saved: number;
  monthly: number;
  risk: RiskKey;
}

export interface Plan {
  goal: GoalMeta;
  risk: RiskMeta;
  target: number;
  years: number;
  saved: number;
  monthlyNeeded: number;
  monthlyCapacity: number;
  projected: number;
  onTrack: boolean;
  yearsNeeded: number | null;
  milestones: { label: string; value: number }[];
  gap: number;
  tips: string[];
}

export interface AdvisorReply {
  text: string;
  plan?: Plan;
  extraTips?: string[];
  card?: 'greeting' | 'budget';
  chips?: string[];
}

export const GOALS: Record<GoalType, GoalMeta> = {
  vacation:   { key: 'vacation',   emoji: '🏖️', label: 'Dream vacation',   horizon: 2,  amount: 6000,    guide: 'vacation',    icon: 'Plane',          color: '#3D9EFF' },
  wedding:    { key: 'wedding',    emoji: '💍', label: 'Wedding',          horizon: 2,  amount: 25000,   guide: 'wedding',     icon: 'Heart',          color: '#FF4D6A' },
  home:       { key: 'home',       emoji: '🏠', label: 'Home purchase',    horizon: 5,  amount: 60000,   guide: 'home-buying', icon: 'Home',           color: '#2ECC71' },
  retirement: { key: 'retirement', emoji: '🌴', label: 'Retirement',       horizon: 30, amount: 1000000, guide: 'retirement',  icon: 'Palmtree',       color: '#A78BFA' },
  business:   { key: 'business',   emoji: '🚀', label: 'Business launch',  horizon: 3,  amount: 20000,   guide: 'business',    icon: 'Rocket',         color: '#F59E0B' },
  crypto:     { key: 'crypto',     emoji: '🪙', label: 'Crypto portfolio', horizon: 5,  amount: 10000,   guide: 'crypto',      icon: 'Coins',          color: '#FACC15' },
  invest:     { key: 'invest',     emoji: '📈', label: 'Investing',        horizon: 10, amount: 50000,   guide: 'investing',   icon: 'TrendingUp',     color: '#22D3EE' },
  budget:     { key: 'budget',     emoji: '🧭', label: 'Budget plan',      horizon: 1,  amount: 0,       guide: 'budgeting',   icon: 'Compass',        color: '#9BB5D6' },
  debt:       { key: 'debt',       emoji: '💳', label: 'Debt payoff',      horizon: 2,  amount: 0,       guide: 'debt-credit', icon: 'CreditCard',     color: '#FB923C' },
};

export const RISK: Record<RiskKey, RiskMeta> = {
  cautious: { label: 'Cautious', ret: 0.035, alloc: [['Cash & high-yield savings', 35], ['Bonds & bond funds', 40], ['Broad ETFs', 20], ['Crypto', 5]] },
  balanced: { label: 'Balanced', ret: 0.055, alloc: [['Broad ETFs', 45], ['Quality stocks', 25], ['Bonds & bond funds', 20], ['Crypto', 10]] },
  bold:     { label: 'Bold',     ret: 0.075, alloc: [['Growth stocks', 40], ['Broad ETFs', 30], ['Crypto', 20], ['Bonds & bond funds', 10]] },
};

const TIPS: Record<GoalType, string[]> = {
  vacation: ['📅 Travel shoulder-season — same trip, 30–50% cheaper', '🫙 Name the savings pot after the destination — it makes dipping harder', '💳 Book on a card for protection, clear it from the pot before interest'],
  wedding: ['🥂 Decide your 3 non-negotiables before the quotes arrive', '📉 Trim guests — catering is per head, and heads add up fast', '🗓️ Off-season / Friday dates save 15–30% on venues'],
  home: ['🏦 Keep the deposit in cash-like funds if buying within 3 years', '📈 Stress-test the mortgage at +3% above your quoted rate', '🧾 Budget 3–5% of price for taxes, legal and moving'],
  retirement: ['🤝 Always take the full employer match — it is instant return', '🚀 Auto-escalate contributions 1% each year', '🛥️ Plan what the days contain, not just what the account says'],
  business: ['🧪 Prove unit economics small before scaling anything', '🛫 Keep 12 months of personal expenses before quitting', '🚫 Never fund the business on credit cards'],
  crypto: ['⚖️ Cap crypto at 1–10% of investable assets', '🐢 Dollar-cost average — no all-time-high lump sums', '📝 Write your exit plan before you buy'],
  invest: ['🔁 Automate payday investing — consistency beats timing', '🧺 One global index fund is already a complete portfolio', '🐻 Market drops are when your monthly buys go on sale'],
  budget: ['🤖 Automate savings on payday — pay future-you first', '🔎 Track one honest month before cutting anything', '✂️ Review subscriptions quarterly'],
  debt: ['⛰️ Avalanche (highest rate first) saves the most money', '⛄ Snowball (smallest first) builds momentum', '🛟 Keep one month of expenses as a buffer to avoid new debt'],
};

/* ---------- formatting ---------- */
export const money = (n: number): string =>
  '$' + Math.round(n).toLocaleString('en-US');
export const pct = (n: number): string =>
  (n * 100).toFixed(1).replace(/\.0$/, '') + '%';

/* ---------- plan math ---------- */
export function monthlyRequired(target: number, saved: number, years: number, annualRate: number): number {
  const r = annualRate / 12;
  const n = Math.max(1, Math.round(years * 12));
  const fvSaved = saved * Math.pow(1 + r, n);
  const gap = Math.max(0, target - fvSaved);
  if (gap === 0) return 0;
  const f = (Math.pow(1 + r, n) - 1) / r;
  return gap / f;
}

export function futureValue(saved: number, monthly: number, years: number, annualRate: number): number {
  const r = annualRate / 12;
  const n = Math.round(years * 12);
  return saved * Math.pow(1 + r, n) + monthly * ((Math.pow(1 + r, n) - 1) / r);
}

export function buildPlan(o: PlanInput): Plan {
  const g = GOALS[o.goalType] ?? GOALS.invest;
  const risk = RISK[o.risk] ?? RISK.balanced;
  const target = o.target || g.amount;
  const years = Math.max(0.25, o.years || g.horizon);
  const saved = o.saved || 0;
  const need = monthlyRequired(target, saved, years, risk.ret);
  const capacity = o.monthly || 0;
  const projected = futureValue(saved, capacity, years, risk.ret);
  const onTrack = capacity >= need - 1;
  let yearsNeeded: number | null = null;
  if (!onTrack && capacity > 0) {
    for (let i = 12; i <= 12 * 60; i += 12) {
      if (futureValue(saved, capacity, i / 12, risk.ret) >= target) { yearsNeeded = i / 12; break; }
    }
  }
  const milestones = [25, 50, 75, 100].map(p => ({
    label: `${p}% of ${g.label.toLowerCase()} target`,
    value: (target * p) / 100,
  }));
  return {
    goal: g, risk, target, years, saved,
    monthlyNeeded: Math.ceil(need),
    monthlyCapacity: capacity,
    projected, onTrack, yearsNeeded, milestones,
    gap: Math.max(0, target - saved),
    tips: TIPS[o.goalType] ?? [],
  };
}

/* ---------- parsing / detection ---------- */
function parseNumber(txt: string): number | null {
  const m = txt.replace(/,/g, '').match(/(\d+(?:\.\d+)?)\s*(k|m|K|M)?/);
  if (!m) return null;
  let n = parseFloat(m[1]);
  if (/k|K/.test(m[2] || '')) n *= 1e3;
  if (/m|M/.test(m[2] || '')) n *= 1e6;
  return n;
}

export function detectRisk(txt: string): RiskKey | null {
  if (/bold|aggressive|high risk|risky|growth heavy/i.test(txt)) return 'bold';
  if (/cautious|safe|careful|low risk|conservative/i.test(txt)) return 'cautious';
  if (/balanced|steady|moderate|middle/i.test(txt)) return 'balanced';
  return null;
}

export function detectGoal(txt: string): GoalType | null {
  const t = txt.toLowerCase();
  if (/vacation|holiday|trip|travel|getaway/.test(t)) return 'vacation';
  if (/wedding|marry|marriage|engagement|bride|groom/.test(t)) return 'wedding';
  if (/home|house|deposit|mortgage|property|flat|apartment/.test(t)) return 'home';
  if (/retire|retirement|pension/.test(t)) return 'retirement';
  if (/business|startup|venture|company|launch/.test(t)) return 'business';
  if (/crypto|bitcoin|btc|eth|coin|ethereum|web3/.test(t)) return 'crypto';
  if (/invest|portfolio|etf|stocks|shares|fund/.test(t)) return 'invest';
  if (/budget|spending|save money|where does/.test(t)) return 'budget';
  if (/debt|loan|credit card|owe|repay/.test(t)) return 'debt';
  return null;
}

/* ---------- conversation ---------- */
interface Session {
  pending: { goal: GoalType; step: number } | null;
  scratch: Partial<PlanInput>;
  last: PlanInput | null;
}

export class AdvisorEngine {
  private session: Session = { pending: null, scratch: {}, last: null };

  reset(): void {
    this.session = { pending: null, scratch: {}, last: null };
  }

  greet(): AdvisorReply {
    return {
      text: 'I map money around your life goals 🧠 Pick a dream and let’s build the plan:',
      card: 'greeting',
      chips: [
        'Plan my dream vacation 🏖️',
        'Help me save a house deposit 🏠',
        'Plan my wedding budget 💍',
        'Build me an investment plan 📈',
        'Can I retire comfortably? 🌴',
        'Business funding plan 🚀',
      ],
    };
  }

  process(text: string): AdvisorReply {
    const t = (text || '').trim();
    if (!t) return this.greet();

    if (this.session.pending) {
      if (/not sure|don'?t know|no idea/i.test(t)) {
        const g = GOALS[this.session.pending.goal];
        this.session.scratch.target = g.amount;
        return this.goalReply(this.session.pending.goal, t);
      }
      return this.goalReply(this.session.pending.goal, t);
    }

    if (/^(hi|hello|hey|yo|good (morning|evening|afternoon))\b/i.test(t) || /who are you|what can you do|^help\b/i.test(t)) {
      return this.greet();
    }

    const g1 = detectGoal(t);
    if (g1) return this.goalReply(g1, t);

    if (this.session.last && /(what if|per month|\/month|monthly|faster|sooner|extend|another|different|bold|cautious|balanced|target|budget)/i.test(t)) {
      const rr = this.recalcReply(t);
      if (rr) return rr;
    }

    return this.greet();
  }

  private goalReply(goalKey: GoalType, txt: string): AdvisorReply {
    const s = this.session.scratch;
    if (!this.session.pending || this.session.pending.goal !== goalKey) {
      this.session.pending = { goal: goalKey, step: 0 };
      this.session.scratch = { goalType: goalKey, risk: detectRisk(txt) ?? undefined };
    }
    const g = GOALS[goalKey];

    const yrs = txt.match(/(\d+(?:\.\d+)?)\s*(?:years?|yrs?)/i);
    if (yrs) s.years = parseFloat(yrs[1]);
    const mth = txt.match(/(\d+(?:\.\d+)?)\s*(?:per month|\/month|a month|monthly|\/mo)/i);
    if (mth) s.monthly = parseNumber(mth[0]) ?? undefined;
    const riskNow = detectRisk(txt);
    if (riskNow) s.risk = riskNow;
    if (/^\s*(yes|yeah|yep|sure|ok)\b/i.test(txt) && s.years == null) s.years = g.horizon;

    // slot filling — strip duration phrases so "6000 in 2 years" reads target=6000
    const needTarget = goalKey !== 'budget' && goalKey !== 'debt' && s.target == null;
    if (needTarget) {
      const stripped = txt.replace(/\d+(?:\.\d+)?\s*(k|m)?\s*(?:years?|yrs?|months?|per month|\/month|a month|monthly|\/mo)\b/gi, '');
      const n = parseNumber(stripped);
      if (n != null) s.target = n;
    }

    if (s.target == null) {
      this.session.pending = { goal: goalKey, step: 1 };
      return {
        text: `${g.emoji} Love it — let’s plan your <strong>${g.label.toLowerCase()}</strong>. What is your rough target amount? (e.g. “${g.amount >= 1000 ? Math.round(g.amount / 1000) + 'k' : g.amount}” — a ballpark is fine)`,
        chips: [String(g.amount >= 1000 ? Math.round(g.amount / 1000) + 'k' : g.amount), 'Not sure yet'],
      };
    }
    if (s.years == null) {
      this.session.pending = { goal: goalKey, step: 2 };
      return {
        text: `Got it — aiming for about <strong>${money(s.target)}</strong> 💰 When do you want it? How many years away is the big day?`,
        chips: ['1 year', '3 years', '5 years', '10 years', `${g.horizon} years`],
      };
    }
    if (s.risk == null) {
      this.session.pending = { goal: goalKey, step: 3 };
      return {
        text: 'Nice timeline. How do you want your money to feel along the way — steady and calm, balanced, or bold?',
        chips: ['Cautious', 'Balanced', 'Bold'],
      };
    }

    // finish → plan
    this.session.pending = null;
    const input: PlanInput = {
      goalType: goalKey,
      target: s.target,
      years: s.years,
      saved: s.saved || 0,
      monthly: s.monthly || 0,
      risk: s.risk,
    };
    this.session.last = input;
    const plan = buildPlan(input);
    return {
      text: `Done — here is your personalised <strong>${plan.goal.label.toLowerCase()} plan</strong> ✨ (snapped it together for you).`,
      plan,
      chips: ['What if I save 400 per month?', 'Model a bold profile', 'Extend it to 5 years'],
    };
  }

  private recalcReply(txt: string): AdvisorReply | null {
    const p: PlanInput = { ...(this.session.last as PlanInput) };
    const notes: string[] = [];
    const mth = txt.match(/(\d+(?:\.\d+)?)\s*(?:per month|\/month|a month|monthly|\/mo)/i);
    const yrs = txt.match(/(\d+(?:\.\d+)?)\s*(?:years?|yrs?)/i);
    if (mth) { p.monthly = parseNumber(mth[0]) ?? p.monthly; notes.push(`monthly → ${money(p.monthly)}`); }
    if (yrs) { p.years = parseFloat(yrs[1]); notes.push(`timeline → ${p.years} yrs`); }
    const r = detectRisk(txt);
    if (r) { p.risk = r; notes.push(`profile → ${RISK[r].label}`); }
    if (!mth && !yrs && !r) {
      const n = parseNumber(txt);
      if (n != null) { p.target = n; notes.push(`target → ${money(n)}`); }
    }
    if (!notes.length) return null;
    this.session.last = p;
    return {
      text: `Recalculated ✨ ${notes.join(' · ')}`,
      plan: buildPlan(p),
      chips: ['What if I save 600 per month?', 'Model a cautious profile', 'Plan my retirement'],
    };
  }
}
