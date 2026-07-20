/* =============================================================================
   Maco Deal Analyzer — CENTRAL SITE CONFIG
   -----------------------------------------------------------------------------
   THIS IS THE ONE FILE TO EDIT for prices, plan features, report prices,
   supported markets, the demo scheduling link, and the founding-member limit.
   Every public page reads from here, so a change made once shows up everywhere.

   HOW TO EDIT (non-technical):
     • To change a price, edit the "price" line for that plan or report.
     • To change what a plan includes, edit its "features" list.
     • To turn on a scheduling link (Calendly, etc.), paste the URL into
       SCHEDULING_URL below. Leave it "" to keep the demo request form.
     • To show a founding-member count, set FOUNDING_MEMBER_LIMIT to a number.
       Leave it null to hide any count (recommended until you decide a real cap).
   Nothing else needs to change. Save the file and it takes effect.
   ============================================================================= */

window.MACO = (function () {
  'use strict';

  /* ---- Business basics ----------------------------------------------------
     Two addresses, deliberately separate, because they fail in different ways.

     CONTACT_EMAIL is what VISITORS SEE — every address printed on the site and
     every mailto: link. Generic on purpose: the business, not a person.

     FORM_DELIVERY_EMAIL is where form submissions are actually DELIVERED.
     FormSubmit requires a one-time confirmation per destination address, and an
     unconfirmed address drops submissions with no bounce and no error — the form
     appears to work and the lead is simply gone. So this stays pointed at the
     address that is already confirmed and receiving until deals@ is proven.

     TO SWITCH DELIVERY OVER (do these in order, see tools/inbox-README.md):
       1. Create deals@macoequitypartners.com (the domain already routes to
          Microsoft 365 — it is an alias or a new user, not a new signup).
       2. Fix the SPF record, or your replies will fail SPF and land in spam.
       3. Set FORM_DELIVERY_EMAIL below to CONTACT_EMAIL.
       4. Deploy, submit a form, click the FormSubmit confirmation that arrives
          at deals@, then submit AGAIN and confirm the second one lands.
     Do not do step 3 before step 1, and do not skip step 4. */
  var CONTACT_EMAIL       = 'deals@macoequitypartners.com';
  var FORM_DELIVERY_EMAIL = 'rmac@macoequitypartners.com';   // ← step 3 changes this to CONTACT_EMAIL
  var FORM_ENDPOINT       = 'https://formsubmit.co/' + FORM_DELIVERY_EMAIL;

  // Paste a scheduling URL (Calendly / SavvyCal / Google Appt) to let visitors
  // book directly. Leave "" and the demo page uses the request form instead.
  var SCHEDULING_URL = '';

  // STRIPE PAYMENT LINKS — live, verified against the Stripe checkout pages on
  // 2026-07-19: each opens "Maco Equity Partners LLC · Subscribe to Maco Deal
  // Analyzer — <plan>" at the right price, recurring monthly.
  // Blank any string to send that plan's card back to the trial only.
  // Still worth doing in Stripe: turn on the customer portal so "cancel anytime"
  // is self-serve rather than an email to you.
  var STRIPE_LINKS = {
    'founding':      'https://buy.stripe.com/eVqbJ21cK1ys4Bffmn7Zu0b',   // $50/mo — verified
    'standard':      'https://buy.stripe.com/14AeVe8Fcb926Jn4HJ7Zu0c',   // $75/mo — verified
    'market-select': 'https://buy.stripe.com/28E7sMbRo4KE1p33DF7Zu0d'    // $85/mo — verified
  };

  // Set to a number (e.g. 25) to advertise a founding-member cap. Leave null to
  // show NO count (never invent a live countdown — see brand rules).
  var FOUNDING_MEMBER_LIMIT = null;

  // Extra-market economics (Market Select plan).
  var ADD_MARKET_PRICE = '+$10/month each';
  var NEW_MARKET_SETUP = 'New-market activation may require a one-time setup fee, quoted before any work begins.';

  /* ---- Subscription plans ------------------------------------------------- */
  var PLANS = [
    {
      id: 'founding',
      name: 'Founding Member',
      price: '$50',
      cadence: '/month',
      badge: 'Launch pricing',
      featured: true,
      desc: 'Full Deal Analyzer access at the founding rate.',
      features: [
        'Core market access',
        'Ranked off-market leads',
        'Comparable-sale analysis',
        'Flip and hold underwriting',
        'Code and lien signals where available',
        'Exports and investor pipeline',
        'Seven-day free trial first — no card required'
      ],
      notes: [
        'Keep your $50 monthly rate for as long as your subscription remains continuously active.'
      ],
      cta: 'Start Free Trial',
      href: 'trial.html'
    },
    {
      id: 'standard',
      name: 'Standard Access',
      price: '$75',
      cadence: '/month',
      badge: '',
      featured: false,
      desc: 'Complete access to the Deal Analyzer in the primary supported market.',
      features: [
        'Complete core platform',
        'Nightly or scheduled lead updates where supported',
        'Comparable sales and estimated ARV tools',
        'Editable underwriting',
        'Export and pipeline functionality',
        'Product support'
      ],
      notes: [],
      cta: 'Start Free Trial',
      href: 'trial.html'
    },
    {
      id: 'market-select',
      name: 'Market Select',
      price: '$85',
      cadence: '/month',
      badge: '',
      featured: false,
      desc: 'Choose one supported market based on where you invest.',
      features: [
        'Complete Deal Analyzer access',
        'One selected supported market',
        'Market-specific records where available',
        'Comparable sales and underwriting',
        'Exports and pipeline',
        'Ability to request a new market'
      ],
      notes: [
        'New market requests are subject to public-data availability, feasibility and the market launch queue.',
        'Additional supported markets: ' + ADD_MARKET_PRICE + '.',
        NEW_MARKET_SETUP
      ],
      cta: 'Start Free Trial',
      href: 'trial.html'
    }
  ];

  /* ---- À la carte reports -------------------------------------------------- */
  var REPORTS = [
    {
      id: 'snapshot',
      name: 'Property Snapshot',
      price: 'Ask',
      desc: 'A fast read on a single property before you spend time on it.',
      includes: [
        'Ownership and property overview',
        'Recorded transaction history',
        'Available distress and municipal signals',
        'Preliminary opportunity summary'
      ]
    },
    {
      id: 'comps',
      name: 'Comparable Sales & Estimated Value Report',
      price: 'Ask',
      desc: 'Recorded comps and an estimated value range with methodology shown.',
      includes: [
        'Relevant recorded comparable sales',
        'Price-per-square-foot analysis',
        'Estimated value range',
        'Comp methodology and limitations'
      ]
    },
    {
      id: 'underwriting',
      name: 'Full Deal Underwriting',
      price: 'Ask',
      desc: 'A complete flip/hold model with editable assumptions and return scenarios.',
      includes: [
        'Purchase and renovation assumptions',
        'Financing and carrying costs',
        'Closing and sale assumptions',
        'Estimated profit and return scenarios',
        'Editable scenario summary'
      ]
    },
    {
      id: 'analyst',
      name: 'Analyst-Reviewed Acquisition Report',
      price: 'Ask',
      desc: 'Full underwriting, reviewed by a person for obvious data issues and risk.',
      includes: [
        'Full deal underwriting',
        'Review of assumptions and obvious data issues',
        'Key risk considerations',
        'Clear next-step checklist'
      ]
    },
    {
      id: 'distress',
      name: 'Distress & Title-Risk Signal Report',
      price: 'Ask',
      desc: 'Everything the public record says is wrong with a property, in one place.',
      includes: [
        'Open code-enforcement cases and recorded liens',
        'Unsafe-structure and expired-permit history',
        'Scheduled foreclosure-auction status where filed',
        'Flood zone and insurance implication',
        'What to verify with title before you commit'
      ]
    },
    {
      id: 'owner',
      name: 'Owner & Entity Research',
      price: 'Ask',
      desc: 'Who actually controls the property, and where to reach them.',
      includes: [
        'Ownership chain from recorded transfers',
        'Entity principals and registered-agent lookup',
        'Mailing address and absentee/out-of-state profile',
        'Estate, trust and heir indicators',
        'Skip-trace starting points (contact data not resold)'
      ]
    },
    {
      id: 'farm',
      name: 'Farm Area Build-Out',
      price: 'Ask',
      desc: 'A whole ZIP or neighborhood scored, ranked and ready to work.',
      includes: [
        'Every qualifying property in the target area',
        'Motivation scoring and ranking',
        'Value bands and owner mailing data',
        'Exportable mail list and pipeline import'
      ]
    },
    {
      id: 'auction',
      name: 'Auction Watchlist',
      price: 'Ask',
      desc: 'Upcoming foreclosure sales in your buy box, underwritten before the date.',
      includes: [
        'Scheduled sales matching your criteria',
        'Judgment amount and assessed value',
        'Preliminary value range per property',
        'Listing-status check and flood zone',
        'Refreshed ahead of each sale date'
      ]
    },
    {
      id: 'rental',
      name: 'Rental & Hold Analysis',
      price: 'Ask',
      desc: 'The buy-and-hold case: cash flow, carry and exit, on your assumptions.',
      includes: [
        'Rent estimate and gross yield',
        'Taxes, insurance and carrying costs',
        'Financing scenarios including DSCR terms',
        'Hold-period return and refinance sensitivity'
      ]
    },
    {
      id: 'market',
      name: 'Custom Market Opportunity Report',
      price: 'Ask',
      desc: 'A scoped read on a market, ZIP code or property type you choose.',
      includes: [
        'Requested market, ZIP code or property type',
        'Recorded activity and pricing',
        'Opportunity and ownership signals where available',
        'Market-specific observations',
        'Defined scope before work begins'
      ]
    }
  ];

  var REPORTS_FOOTNOTE = 'Every report is scoped and priced before any work begins — tell us the property or market and you get a fixed quote and turnaround, no subscription required. Bulk and recurring analysis available.';

  var REPORT_DISCLAIMER =
    'Reports are provided for investment screening and informational purposes. ' +
    'Estimated values, comparable analyses and underwriting are not licensed real ' +
    'estate appraisals, title reports, inspections, legal opinions or guarantees of ' +
    'future performance. Users must independently verify all material information.';

  /* ---- Supported markets --------------------------------------------------
     Honest coverage tiers. Miami-Dade carries the deepest signal set (code
     cases, recorded liens, unsafe/expired permits, comps). The other live
     counties run on county tax-roll records + recorded sales; code/lien depth
     is still expanding — so they sit in "Live · expanding," not "Active."
     "Requested" = markets under public-data feasibility review, not a claim of
     demand. Edit these lists freely as coverage changes. ---------------------- */
  var MARKETS = {
    note: 'Public data differs by county. Each market is evaluated for record ' +
          'availability, reliability and update frequency before launch.',
    tiers: [
      {
        key: 'active',
        label: 'Active',
        blurb: 'Full signal set — code cases, recorded liens, unsafe/expired permits, comparable sales and underwriting.',
        markets: [
          { name: 'Miami-Dade County', page: 'off-market-deals-miami-dade.html',
            note: 'Deepest coverage. County-wide expansion rolling out.',
            cities: ['Kendall', 'Palmetto Bay', 'Pinecrest', 'South Miami', 'Homestead'] }
        ]
      },
      {
        key: 'expanding',
        label: 'Live · expanding coverage',
        blurb: 'Live now on county tax-roll records, recorded sales and owner mailing data, with ZIP-level sale bands. Code and lien depth is still being added county by county.',
        markets: [
          { name: 'Broward County', page: 'off-market-deals-broward.html',
            cities: ['Fort Lauderdale', 'Pompano Beach', 'Deerfield Beach', 'Coral Springs', 'Coconut Creek', 'Margate', 'Tamarac', 'Sunrise', 'Oakland Park', 'Lauderhill', 'Lauderdale Lakes', 'North Lauderdale', 'Wilton Manors', 'Lighthouse Point', 'Lauderdale By The Sea', 'Unincorporated Broward'] },
          { name: 'Lee County', page: 'off-market-deals-lee.html', note: 'Fort Myers metro',
            cities: ['Fort Myers', 'Cape Coral', 'Lehigh Acres', 'North Fort Myers', 'Bonita Springs', 'Estero', 'Fort Myers Beach', 'Sanibel', 'Alva', 'Bokeelia', 'Matlacha', 'Saint James City'] },
          { name: 'Collier County', page: 'off-market-deals-collier.html', note: 'Naples metro',
            cities: ['Naples', 'Golden Gate City', 'Marco Island', 'Immokalee', 'Everglades City', 'Goodland', 'Chokoloskee'] },
          { name: 'Polk County', page: 'off-market-deals-polk.html', note: 'Orlando–Tampa corridor',
            cities: ['Lakeland', 'Winter Haven', 'Davenport', 'Haines City', 'Auburndale', 'Lake Wales', 'Poinciana', 'Mulberry'] },
          { name: 'Lake County', page: 'off-market-deals-lake.html', note: 'Smallest market — Clermont area only',
            cities: ['Clermont'] }
        ]
      },
      {
        key: 'requested',
        label: 'Requested · under evaluation',
        blurb: 'On the evaluation list. We review public-data availability and update frequency before committing a launch date. Request yours to move it up the queue.',
        markets: [
          { name: 'Palm Beach County', cities: ['West Palm Beach', 'Boca Raton', 'Delray Beach', 'Lake Worth'] },
          { name: 'Hillsborough County', note: 'Tampa', cities: ['Tampa', 'Brandon', 'Plant City'] },
          { name: 'Orange County', note: 'Orlando', cities: ['Orlando', 'Apopka', 'Winter Garden'] }
        ]
      },
      {
        key: 'coming-soon',
        label: 'Coming soon',
        blurb: 'Launches are announced only after a market clears data review — nothing is scheduled today. Ask and we will tell you honestly where a market stands.',
        markets: []
      }
    ]
  };

  /* ---- Analytics event names ----------------------------------------------
     These are the named events the site fires. No analytics provider is wired
     in yet, so MACO.track() is a safe no-op that also pushes to window.dataLayer
     if you later add Google Tag Manager / GA. Nothing here sends data on its own. */
  var EVENTS = [
    'book_demo_click', 'demo_form_started', 'demo_form_submitted',
    'pricing_viewed', 'report_request_started', 'report_request_submitted',
    'login_click', 'sample_deal_click', 'market_request_submitted'
  ];

  function track(event, props) {
    try {
      if (window.dataLayer && typeof window.dataLayer.push === 'function') {
        window.dataLayer.push(Object.assign({ event: event }, props || {}));
      }
      // Uncomment for local debugging:
      // console.debug('[track]', event, props || {});
    } catch (e) { /* analytics must never break the page */ }
  }

  /* ---- Small DOM helpers --------------------------------------------------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function el(id) { return document.getElementById(id); }

  /* ---- Renderers ----------------------------------------------------------
     Build pricing / report / market markup from the config above so there is
     never a second copy of a price hard-coded in a page. */
  function renderPlans(containerId) {
    var box = el(containerId); if (!box) return;
    box.innerHTML = PLANS.map(function (p) {
      var badge = p.badge ? '<div class="plan__badge">' + esc(p.badge) + '</div>' : '';
      var feats = p.features.map(function (f) {
        return '<li>' + esc(f) + '</li>';
      }).join('');
      var notes = (p.notes || []).map(function (n) {
        return '<p class="plan__note">' + esc(n) + '</p>';
      }).join('');
      return '<article class="plan' + (p.featured ? ' plan--featured' : '') + '">' +
        badge +
        '<h3 class="plan__name">' + esc(p.name) + '</h3>' +
        '<div class="plan__price"><span class="plan__amount">' + esc(p.price) + '</span>' +
          '<span class="plan__cadence">' + esc(p.cadence) + '</span></div>' +
        '<p class="plan__desc">' + esc(p.desc) + '</p>' +
        '<ul class="plan__features">' + feats + '</ul>' +
        notes +
        (function () {
          var pay = STRIPE_LINKS[p.id];
          if (pay) {
            // Payment link configured. The TRIAL stays the primary button and checkout
            // is the secondary link — deliberately, for two reasons. Every page promises
            // "7-day free trial, no card", and a Subscribe-first card contradicts that.
            // And for a product with no reviews and no track record yet, asking for a
            // card before anyone has seen a lead board is the harder sell. Swap the two
            // once the trial-to-paid rate says people are converting anyway.
            return '<a class="da-btn ' + (p.featured ? 'da-btn--primary' : 'da-btn--dark') + ' plan__cta" ' +
              'href="' + esc(p.href) + '?plan=' + esc(p.id) + '" data-track="trial_click" ' +
              'data-plan="' + esc(p.id) + '">' + esc(p.cta) + ' <span aria-hidden="true">&rarr;</span></a>' +
              '<p class="plan__note" style="text-align:center;margin-top:8px">or ' +
              '<a href="' + esc(pay) + '" data-track="subscribe_click" data-plan="' + esc(p.id) + '" ' +
              'style="text-decoration:underline">subscribe now — ' + esc(p.price) + esc(p.cadence) + '</a></p>';
          }
          return '<a class="da-btn ' + (p.featured ? 'da-btn--primary' : 'da-btn--dark') + ' plan__cta" ' +
            'href="' + esc(p.href) + '?plan=' + esc(p.id) + '" data-track="book_demo_click" ' +
            'data-plan="' + esc(p.id) + '">' + esc(p.cta) + ' <span aria-hidden="true">&rarr;</span></a>';
        })() +
      '</article>';
    }).join('');
    track('pricing_viewed', { location: containerId });
  }

  // opts.showPrices=false renders the SAMPLE view (prices live only on pricing.html).
  function renderReports(containerId, opts) {
    var box = el(containerId); if (!box) return;
    var showPrices = !(opts && opts.showPrices === false);
    box.innerHTML = REPORTS.map(function (r) {
      var items = r.includes.map(function (i) {
        return '<li>' + esc(i) + '</li>';
      }).join('');
      return '<article class="report">' +
        '<div class="report__head">' +
          '<h3 class="report__name">' + esc(r.name) + '</h3>' +
          (showPrices ? '<div class="report__price">' + esc(r.price) + '</div>'
                      : '<div class="report__price" style="font-size:11px;letter-spacing:.1em">SAMPLE</div>') +
        '</div>' +
        '<p class="report__desc">' + esc(r.desc) + '</p>' +
        '<ul class="report__list">' + items + '</ul>' +
        '<a class="da-btn da-btn--outline report__cta" ' +
          'href="reports.html?report=' + encodeURIComponent(r.name) + '#request" ' +
          'data-report="' + esc(r.name) + '" data-track="report_request_started">' +
          'Request This Report</a>' +
      '</article>';
    }).join('');
  }

  // County landing pages — pills link through when a page exists.
  var MARKET_PAGES = {
    'Miami-Dade County': 'off-market-deals-miami-dade.html',
    'Broward County': 'off-market-deals-broward.html',
    'Lee County (Fort Myers)': 'off-market-deals-lee.html',
    'Collier County (Naples)': 'off-market-deals-collier.html',
    'Polk County': 'off-market-deals-polk.html',
    'Lake County': 'off-market-deals-lake.html'
  };
  function renderMarkets(containerId) {
    var box = el(containerId); if (!box) return;
    box.innerHTML = MARKETS.tiers.map(function (t) {
      var body = t.markets.length
        ? '<div class="market-umbrellas">' + t.markets.map(function (m) {
            var head = m.page
              ? '<a class="market-umb__name" href="' + m.page + '">' + esc(m.name) + ' <span aria-hidden="true">&rarr;</span></a>'
              : '<span class="market-umb__name">' + esc(m.name) + '</span>';
            var cities = (m.cities || []).length
              ? '<div class="market-umb__cities">' + m.cities.map(function (c) {
                  return '<span class="market-city">' + esc(c) + '</span>';
                }).join('') + '</div>'
              : '';
            return '<div class="market-umb">' +
              '<div class="market-umb__head">' + head +
                (m.note ? '<span class="market-umb__note">' + esc(m.note) + '</span>' : '') +
              '</div>' + cities +
            '</div>';
          }).join('') + '</div>'
        : '<p class="market-tier__empty">None scheduled yet.</p>';
      return '<div class="market-tier market-tier--' + esc(t.key) + '">' +
        '<div class="market-tier__head">' +
          '<span class="market-tier__label">' + esc(t.label) + '</span>' +
          '<span class="market-tier__count">' + t.markets.length + '</span>' +
        '</div>' +
        '<p class="market-tier__blurb">' + esc(t.blurb) + '</p>' +
        body +
      '</div>';
    }).join('');
  }

  /* ---- Wire click tracking + form confirmations --------------------------- */
  function wireTracking() {
    document.addEventListener('click', function (ev) {
      var t = ev.target;
      while (t && t !== document && !t.getAttribute) t = t.parentNode;
      var node = ev.target;
      while (node && node.getAttribute) {
        var name = node.getAttribute('data-track');
        if (name) { track(name, { text: (node.textContent || '').trim().slice(0, 60) }); break; }
        node = node.parentNode;
      }
    }, true);
  }

  // Prefill a report/plan choice into a form select when arriving via a card CTA.
  function prefillFromQuery() {
    try {
      var q = new URLSearchParams(location.search);
      var report = q.get('report');
      if (report) {
        var sel = document.querySelector('[name="report_type"]');
        if (sel) { for (var i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === report || sel.options[i].text === report) { sel.selectedIndex = i; break; }
        } }
      }
    } catch (e) {}
  }

  // Show the "message received" banner after a FormSubmit redirect (?sent=1).
  function showSentBanner(bannerId) {
    try {
      if (new URLSearchParams(location.search).get('sent') === '1') {
        var b = el(bannerId);
        if (b) { b.classList.add('show'); b.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      }
    } catch (e) {}
  }

  // ---- Reveal safety net -------------------------------------------------
  // Pages fade content in with .rv/.on driven by IntersectionObserver. If IO
  // never fires (rare: some background tabs, throttled renderers), content
  // would stay invisible. Shortly after load, if NOTHING has been revealed,
  // force-reveal everything. When IO works normally (the hero reveals first),
  // this does nothing and the scroll animation is preserved.
  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(function () {
        var rv = document.querySelectorAll('.rv');
        if (!rv.length) return;
        for (var i = 0; i < rv.length; i++) {
          if (rv[i].classList.contains('on')) return; // IO is working — leave it
        }
        for (var j = 0; j < rv.length; j++) rv[j].classList.add('on');
      }, 1200);
    });
  }

  return {
    contactEmail: CONTACT_EMAIL,
    formEndpoint: FORM_ENDPOINT,
    schedulingUrl: SCHEDULING_URL,
    stripeLinks: STRIPE_LINKS,
    foundingMemberLimit: FOUNDING_MEMBER_LIMIT,
    plans: PLANS,
    reports: REPORTS,
    reportsFootnote: REPORTS_FOOTNOTE,
    reportDisclaimer: REPORT_DISCLAIMER,
    markets: MARKETS,
    events: EVENTS,
    track: track,
    renderPlans: renderPlans,
    renderReports: renderReports,
    renderMarkets: renderMarkets,
    wireTracking: wireTracking,
    prefillFromQuery: prefillFromQuery,
    showSentBanner: showSentBanner
  };
})();
