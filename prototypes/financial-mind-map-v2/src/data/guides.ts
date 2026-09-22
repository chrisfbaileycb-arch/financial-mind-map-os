// FinancialMindMap — Guides & playbooks data (rendered by the Guides hub + sub-pages)

export interface GuideSection {
  h: string;
  p: string;
  list?: string[];
}

export interface GuideFaq {
  q: string;
  a: string;
}

export interface Guide {
  slug: string;
  emoji: string;
  tag: string;
  minutes: number;
  title: string;
  intro: string;
  sections: GuideSection[];
  faq: GuideFaq[];
  cta: { label: string; ask: string };
  related: string[];
}

export const GUIDES: Record<string, Guide> = {
  budgeting: {
    slug: 'budgeting', emoji: '🧭', tag: 'Foundations', minutes: 6,
    title: 'Budgeting that actually sticks',
    intro: 'A budget is not a diet — it is a map. Here is how to build one you will still follow on a rainy Tuesday.',
    sections: [
      { h: 'The 50 / 30 / 20 starting point', p: 'Split take-home pay into needs (50%), wants (30%) and future-you (20%: savings + debt overpayments). Treat it as a starting ratio, then bend it to your life.', list: ['Needs: rent, food, transport, utilities, minimum debt payments', 'Wants: eating out, subscriptions, hobbies, travel', 'Future you: emergency fund, investing, extra debt payments'] },
      { h: 'Pay yourself first, automatically', p: 'Move your savings the day you get paid. Automation beats willpower every single time.', list: ['Standing order on payday → savings/investment account', 'Round-up purchases into a pot', 'Review subscriptions quarterly and cancel the "why do I still have this?" ones'] },
      { h: 'Know your real numbers', p: 'Track for one honest month before cutting anything. Most people find 5–10% of spending they do not value.', list: ['Export 3 months of statements and tag every line', 'Find the three biggest "fun leaks"', 'Cap them with a weekly spending allowance'] },
    ],
    faq: [
      { q: 'How big should my emergency fund be?', a: '3–6 months of essential expenses in easy-access cash. If your income is variable, aim for 6–12 months.' },
      { q: 'What if my income changes monthly?', a: 'Budget on last month’s income (or your lowest recent month) and treat peaks as bonus money for goals.' },
    ],
    cta: { label: 'Build my budget plan with Chip', ask: 'Help me build a budget plan' },
    related: ['debt-credit', 'investing', 'vacation'],
  },

  investing: {
    slug: 'investing', emoji: '📈', tag: 'Investing', minutes: 8,
    title: 'Investing from zero to confident',
    intro: 'Investing is how money earns money while you sleep. Start boring, stay consistent, get fancy later (maybe never).',
    sections: [
      { h: 'Before you invest a single coin', p: 'Investing is step 3, not step 1. Get these done first:', list: ['Clear expensive debt (credit cards, payday loans)', 'Emergency fund: 3–6 months of essentials', 'Know your time horizon — money you need in under 3 years does not belong in volatile assets'] },
      { h: 'The core building blocks', p: 'Most healthy portfolios are 80% boring on purpose.', list: ['Broad index funds / ETFs — instant diversification', 'Bonds or bond funds — the shock absorber', 'Individual stocks — only money you can watch drop 50% without panic-selling', 'Crypto — high volatility satellite, keep it a slice you can lose'] },
      { h: 'Risk is a dial, not a personality', p: 'Your mix should reflect when you need the money, not how bold you feel today.', list: ['Cautious: 20% growth / 80% defensive', 'Balanced: 60% growth / 40% defensive', 'Bold: 80–90% growth / 10–20% defensive'] },
      { h: 'The magic is boring: pound-cost averaging', p: 'Investing a fixed amount every month buys more units when prices fall and fewer when they rise. You stop needing to time the market.', list: ['Automate a monthly transfer on payday', 'Rebalance once or twice a year', 'When markets drop: keep going — that is the sale'] },
    ],
    faq: [
      { q: 'How much do I need to start?', a: 'Most platforms start at $10–50, and fractional shares mean $10 buys a slice of anything. Consistency beats size.' },
      { q: 'Should I wait for a dip?', a: 'Time in the market beats timing the market. Monthly investing removes the dilemma entirely.' },
    ],
    cta: { label: 'Model my investment plan', ask: 'Build me an investment plan' },
    related: ['stocks-etfs', 'crypto', 'retirement'],
  },

  'stocks-etfs': {
    slug: 'stocks-etfs', emoji: '🧺', tag: 'Investing', minutes: 6,
    title: 'Stocks, ETFs & funds — picking your vehicles',
    intro: 'One company is a bet. The whole market is a machine. Here is how to choose what rides in your portfolio.',
    sections: [
      { h: 'Single stocks', p: 'Buying a share is buying a slice of one business. Highest excitement, highest risk.', list: ['Only with money you can afford to lose', 'Cap single stocks at 10–20% of your portfolio', 'Write down why you bought — it stops panic selling'] },
      { h: 'ETFs and index funds', p: 'A basket that tracks an index (like the S&P 500 or a world index). One purchase = hundreds of companies.', list: ['Look for low ongoing charges (under 0.25% is good)', 'Accumulating (ACC) funds reinvest dividends automatically', 'Global beats single-country for the core'] },
      { h: 'How to choose in 3 questions', p: 'Keep it this simple:', list: ['When do I need this money? (horizon = how much volatility you can stomach)', 'What does it cost per year? (fees compound against you)', 'Is it diversified enough that one bad year is survivable?'] },
    ],
    faq: [
      { q: 'How many funds do I need?', a: 'One good global index fund is a complete portfolio. Two or three is plenty of fine-tuning.' },
      { q: 'Active vs passive?', a: 'Most active managers underperform their index over 10+ years. Passive core, active satellite only if you love the research.' },
    ],
    cta: { label: 'Compare allocations', ask: 'Build me an investment plan' },
    related: ['investing', 'crypto', 'retirement'],
  },

  crypto: {
    slug: 'crypto', emoji: '🪙', tag: 'Alternatives', minutes: 7,
    title: 'Crypto & digital coins — sane participation',
    intro: 'Coins can 10x and can drop 80%. This guide is about participating without getting wrecked.',
    sections: [
      { h: 'Position sizing is everything', p: 'Decide the slice before you buy anything.', list: ['Satellite allocation: typically 1–10% of total investable assets', 'Money in = money you can watch go to zero', 'Never borrow to buy coins'] },
      { h: 'What you are actually buying', p: 'Bitcoin is digital scarcity; platform chains are bets on ecosystems; memecoins are lottery tickets with better branding.', list: ['Core: BTC/ETH as the "blue chips"', 'Small caps: research only, tiny slices', 'Stablecoins: useful rails, but they carry issuer risk — not "cash"'] },
      { h: 'Survival rules', p: 'The space is 24/7 and optimised to make you impulsive. Your defences:', list: ['Dollar-cost average in — never all-time-high lump sums', 'Use reputable exchanges and a hardware wallet for serious holdings', 'Write an exit plan (take-profit levels) before you buy', 'Ignore DMs, "guaranteed returns", and leverage as a beginner'] },
    ],
    faq: [
      { q: 'Is it too late?', a: 'Nobody knows. That is exactly why it stays a satellite position and not your retirement plan.' },
      { q: 'Staking — free money?', a: 'Yield comes from risk: lockups, slashing, smart-contract bugs, price drops. Size it accordingly.' },
    ],
    cta: { label: 'Set my crypto slice', ask: 'How much crypto should I hold?' },
    related: ['investing', 'stocks-etfs'],
  },

  'home-buying': {
    slug: 'home-buying', emoji: '🏠', tag: 'Life goals', minutes: 8,
    title: 'Buying a home — the deposit game plan',
    intro: 'The hardest part is the deposit. Here is how to get there without putting life on pause for a decade.',
    sections: [
      { h: 'Know your full number', p: 'The deposit is only the headline. Budget for the whole move:', list: ['Deposit: 5–20% of the price', 'Stamp duty / transfer taxes', 'Legal fees, surveys, moving costs (often 3–5% of price)', 'A buffer for the first-year "the boiler broke" fund'] },
      { h: 'Deposit sprint strategy', p: 'Pick a target date, then reverse-engineer the monthly number and hit it automatically.', list: ['Use tax-advantaged first-home accounts where available', 'Keep the deposit in cash-like or short-horizon investments — not 100% equities', 'Raise the rate: side income beats skipping every coffee'] },
      { h: 'Mortgage sense', p: 'The monthly payment must survive an interest rate shock.', list: ['Stress-test at +3% above your quoted rate', 'Fixed terms give payment certainty; shorter fixes are cheaper but riskier', 'Bigger deposit = better rate band — compare the break points'] },
    ],
    faq: [
      { q: 'How much house can I afford?', a: 'A common ceiling: 4–4.5× combined income, but the real test is monthly payment under 28–33% of take-home pay at a stressed rate.' },
      { q: 'Invest the deposit instead?', a: 'If you buy within ~3 years, keep it in cash/short bonds. Markets can drop 30% the month before you need the keys.' },
    ],
    cta: { label: 'Plan my deposit', ask: 'Help me save a house deposit' },
    related: ['budgeting', 'investing', 'wedding'],
  },

  wedding: {
    slug: 'wedding', emoji: '💍', tag: 'Life goals', minutes: 5,
    title: 'Funding a wedding without funding a decade of regret',
    intro: 'One beautiful day, zero debt hangover. The trick is deciding what the day is for before the quotes arrive.',
    sections: [
      { h: 'Set the ceiling first', p: 'Decide the number before the inspiration board. Your ceiling = savings + contributions ÷ months, minus a 10% buffer.', list: ['Pick your 3 non-negotiables (photos? food? the band?)', 'Everything else gets the "does this change the memory?" test', 'Agree the number together — early'] },
      { h: 'Where the money hides', p: 'Wedding quotes inflate through emotion and timing. Fight back:', list: ['Off-season and Friday/Sunday dates save 15–30%', 'Trim the guest list — catering is per head', 'Book vendors in the quiet months, pay deposits from the wedding pot, never a credit card'] },
      { h: 'Cashflow plan', p: 'Open a separate wedding pot, automate monthly transfers the day after payday, and track vendor payments on a simple timeline.', list: ['12+ months out: venue & photo', '6–9 months: catering tasting & deposits', '1 month: final balances from the pot, not from credit'] },
    ],
    faq: [{ q: 'Is wedding debt ever fine?', a: 'High-interest wedding debt is the worst wedding gift to your future selves. Delay the date before financing the day.' }],
    cta: { label: 'Build my wedding budget', ask: 'Plan my wedding budget' },
    related: ['home-buying', 'budgeting', 'vacation'],
  },

  vacation: {
    slug: 'vacation', emoji: '🏖️', tag: 'Life goals', minutes: 5,
    title: 'The dream trip, fully funded in advance',
    intro: 'The best trips are paid for before take-off. Here is the vacation sinking-fund playbook.',
    sections: [
      { h: 'Price the real trip', p: 'A "cheap" flight is 25% of the bill. Price flights, stays, food, activities, transport and a 15% "yes" fund.', list: ['Build the total from categories, not vibes', 'Track prices 3–4 months out; set fare alerts', 'Pay in the local currency when abroad, never let the terminal convert'] },
      { h: 'The sinking fund', p: 'Total ÷ months until departure = your monthly auto-transfer. Simple, boring, effective.', list: ['Separate pot named after the destination — it makes spending it harder', 'Windfalls (bonus, birthday, refunds) go straight in', 'Book refundable first, commit later'] },
      { h: 'Stretch the value', p: 'One splurge category, save on the rest.', list: ['Travel rewards points for flights — but never spend for points', 'Shoulder season: same trip, 30–50% less'] },
    ],
    faq: [{ q: 'Should I pay on a credit card?', a: 'Yes — for protection and points — then clear it in full from the vacation pot before interest kicks in.' }],
    cta: { label: 'Fund my dream trip', ask: 'Help me save for my dream vacation' },
    related: ['budgeting', 'wedding'],
  },

  retirement: {
    slug: 'retirement', emoji: '🌴', tag: 'Life goals', minutes: 8,
    title: 'Retirement: the goal with the biggest multiplier',
    intro: 'Time is the strongest asset you own. Every decade you start early roughly halves what you need to save.',
    sections: [
      { h: 'The number, roughly', p: 'A quick target: aim for 25× your desired annual spending in retirement (the 4% rule of thumb). Want $40k/year? That is about $1,000,000 invested.', list: ['Subtract expected pensions/state income first', 'Revisit the number every year — it is a compass, not a contract', 'Inflation is the tax on waiting: use 2–3% in your maths'] },
      { h: 'Free money first', p: 'Use tax-advantaged pensions and employer matching before anything else.', list: ['Employer match = instant 50–100% return. Always take the full match', 'Max tax relief wrappers before taxable investing', 'Auto-escalate contributions 1% a year — you will not miss it'] },
      { h: 'Glide path', p: 'Your mix gets more defensive as the date approaches.', list: ['25+ years out: 80–90% growth assets', '10 years out: 60–70% growth', '5 years out: 40–50% growth + 2–3 years of spending in cash'] },
    ],
    faq: [
      { q: 'I started late. Panic?', a: 'No — but automate aggressively: max the match, escalate 1–2% yearly, and consider working two extra years. Time still compounds.' },
      { q: 'Retire at 55?', a: 'Model it: 25× spending, healthcare bridging years, and a plan for what the days will contain.' },
    ],
    cta: { label: 'Model my retirement', ask: 'Can I retire comfortably?' },
    related: ['investing', 'stocks-etfs', 'business'],
  },

  business: {
    slug: 'business', emoji: '🚀', tag: 'Building', minutes: 7,
    title: 'Business planning & funding your venture',
    intro: 'A business is an investment with your time, sweat and savings attached. Plan the money before the merch.',
    sections: [
      { h: 'The runway rule', p: 'Decide your funding method before you spend:', list: ['Bootstrapping: keep 12 months of personal expenses saved before quitting', 'Pre-revenue cap: set a hard "if we are not at X by date Y, we stop or adjust" line', 'Never fund the business on credit cards'] },
      { h: 'Unit economics in one page', p: 'If the maths works small, it works big. If it fails small, nothing saves it.', list: ['Price − cost to deliver = gross profit per sale', 'Customer acquisition cost vs lifetime value (aim for 3:1)', 'Break-even count = fixed costs ÷ gross profit per sale'] },
      { h: 'Funding ladder', p: 'Take the cheapest money first:', list: ['Revenue (best investor is the customer)', 'Grants & competition prizes', 'Friends & family on clear written terms', 'Loans/credit lines — stress-test repayments at +3% interest', 'Equity investors — most expensive money; only for scalable models'] },
    ],
    faq: [{ q: 'How much personal money should I risk?', a: 'Only what you can lose without touching: emergency fund, retirement contributions and family essentials stay off the table.' }],
    cta: { label: 'Plan my business funding', ask: 'Help me plan business funding' },
    related: ['budgeting', 'retirement', 'investing'],
  },

  'debt-credit': {
    slug: 'debt-credit', emoji: '💳', tag: 'Foundations', minutes: 6,
    title: 'Debt, credit & the interest-rate war',
    intro: 'Debt is money from the future at a price. Pay the expensive price never; use the cheap price carefully.',
    sections: [
      { h: 'Avalanche vs snowball', p: 'Both work. Pick the one you will actually stick with:', list: ['Avalanche: highest interest rate first — mathematically optimal', 'Snowball: smallest balance first — fastest wins for motivation', 'Either way: automate minimums on everything, attack one debt'] },
      { h: 'Refinance and consolidate — carefully', p: 'Moving 24% credit card debt to a 0% or low personal loan saves real money. Then cut up the card habit.', list: ['Balance transfers: mind the transfer fee and promo end date', 'Consolidation only works if you stop new borrowing', 'One month of expenses as a buffer prevents new debt spirals'] },
      { h: 'The credit score shortcut', p: 'Scores reward boring consistency.', list: ['Use under 30% of your limit, pay in full monthly', 'Never miss a payment — set up direct debits for minimums', 'Do not open three cards while shopping for a mortgage'] },
    ],
    faq: [{ q: 'Save and invest while in debt?', a: 'Always grab employer pension match, then attack debt above ~6–7% interest before investing. Below that, investing can mathematically win.' }],
    cta: { label: 'Build my debt payoff plan', ask: 'Build me a debt payoff plan' },
    related: ['budgeting', 'investing'],
  },
};

export const GUIDE_LIST = Object.values(GUIDES);
