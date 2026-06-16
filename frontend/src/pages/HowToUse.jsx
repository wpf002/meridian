import { PageTitle } from '../components/states.jsx'

function Term({ name, children }) {
  return (
    <div className="py-3 border-b border-edge/50 last:border-0">
      <div className="font-semibold text-ink">{name}</div>
      <div className="text-sm text-muted mt-1 leading-relaxed">{children}</div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="card p-5">
      <div className="card-head -mx-5 -mt-5 mb-2 rounded-t-lg">{title}</div>
      {children}
    </div>
  )
}

export default function HowToUse() {
  return (
    <div>
      <PageTitle
        title="How To Use"
        sub="Plain-English meaning of every term on the other pages. Nothing here is financial advice — it's a screening tool to help you do your own research."
      />

      <div className="grid lg:grid-cols-2 gap-4 auto-rows-fr">
        <Section title="The basics">
          <Term name="Score (0–100)">
            One number summarizing how strong a stock's setup looks right now. Higher is better.
            It blends four ingredients (below). It is not a price target or a guarantee — it's a
            relative ranking that moves as the data changes.
          </Term>
          <Term name="Tier">
            A simple grade based on the Score. <b>Tier 1</b> = strongest (Score ≈ 75+),
            <b> Tier 2</b> = solid, <b>Tier 3</b> = marginal / only if timed well, and
            <b> Avoid</b> = weak setup or a hard risk flag — steer clear.
          </Term>
          <Term name="Signal — Buy / Watch / Avoid">
            The suggested stance. <b>Buy</b> = the setup is strong enough to act on,
            <b> Watch</b> = keep an eye on it, <b>Avoid</b> = stay away, <b>Neutral</b> = nothing
            notable either way.
          </Term>
          <Term name="Confidence">
            How much the underlying signals agree with each other. <b>High</b> means macro, price,
            news and risk all point the same way; <b>Low</b> means they're mixed, so take the Score
            with a grain of salt.
          </Term>
        </Section>

        <Section title="What drives the Score">
          <Term name="Macro">
            The big-picture backdrop — interest rates, inflation, volatility. Is the overall market
            environment a tailwind or a headwind right now?
          </Term>
          <Term name="Price Trend">
            How the stock's own price has been behaving — momentum and trend over recent history.
          </Term>
          <Term name="News">
            Sentiment from recent headlines, read by an AI model: are the stories about this company
            getting better or worse?
          </Term>
          <Term name="Risk">
            Signs of fragility — stretched valuations, crowding, balance-sheet stress. This one
            <b> subtracts</b> from the Score; everything else adds.
          </Term>
        </Section>

        <Section title="Portfolio buckets">
          <Term name="Foundation">
            Stable, high-conviction names meant to be held long-term — the anchor of the mix.
          </Term>
          <Term name="Growth">
            Higher-risk names with more upside potential.
          </Term>
          <Term name="Protection">
            Safe-havens (think bonds, gold) that tend to hold up when stocks fall.
          </Term>
          <Term name="Short-term">
            Opportunistic, shorter-duration positions — trades, not anchors.
          </Term>
          <Term name="Heads-up warnings">
            The yellow box on the Portfolio page flags diversification or concentration concerns
            (e.g. too much in one sector). They're cautions to consider, not errors.
          </Term>
        </Section>

        <Section title="Scenarios & alerts">
          <Term name="Scenario (a 'what if')">
            A hypothetical market shock — like a recession or an inflation spike. Running one
            re-scores every name as if that environment arrived, so you can see what would hold up
            and what would get hit.
          </Term>
          <Term name="Regime">
            A label for the kind of market we're in: <b>Risk-on</b> (appetite for risk),
            <b> Risk-off</b> (flight to safety), <b>Inflationary</b>, or <b>Liquidity contraction</b>
            (money getting tighter).
          </Term>
          <Term name="Alerts">
            Automatic flags raised when something notable happens — a risk spike, a top-tier name, or
            unusually low confidence. They surface on the Status page.
          </Term>
        </Section>
      </div>
    </div>
  )
}
