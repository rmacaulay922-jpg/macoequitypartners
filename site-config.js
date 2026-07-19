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

  /* ---- Business basics ---------------------------------------------------- */
  var CONTACT_EMAIL  = 'rmac@macoequitypartners.com';
  // All forms email you through the site's existing FormSubmit inbox.
  var FORM_ENDPOINT  = 'https://formsubmit.co/' + CONTACT_EMAIL;

  // Paste a scheduling URL (Calendly / SavvyCal / Google Appt) to let visitors
  // book directly. Leave "" and the demo page uses the request form instead.
  var SCHEDULING_URL = '';

  // STRIPE PAYMENT LINKS — paste your three Payment Link URLs here and every plan
  // card's button becomes "Subscribe" pointing straight at checkout. Leave "" and
  // the buttons keep sending people to the free trial (current behavior).
  // Create them at dashboard.stripe.com → Payment Links (recurring monthly), and
  // turn on the customer portal so "cancel anytime" is self-serve.
  var STRIPE_LINKS = {
    'founding':      '',   // $50/mo
    'standard':      '',   // $75/mo
    'market-select': ''    // $85/mo
  };

  // Set to a number (e.g. 25) to advertise a founding-member cap. Leave null to
  // show NO count (never invent a live countdown — see brand rules).
  var FOUNDING_MEMBER_LIMIT = null;

  // Extra-market economics (Market Select plan).
  var ADD_MARKET_PRICE = '+$10/month each';
  var NEW_MARKET_SETUP = 'New-market activation may require a one-time $49 setup fee.';

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
      price: '$15',
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
      price: '$29',
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
      price: '$49',
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
      price: '$79',
      desc: 'Full underwriting, reviewed by a person for obvious data issues and risk.',
      includes: [
        'Full deal underwriting',
        'Review of assumptions and obvious data issues',
        'Key risk considerations',
        'Clear next-step checklist'
      ]
    },
    {
      id: 'market',
      name: 'Custom Market Opportunity Report',
      price: 'From $99',
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

  var REPORTS_FOOTNOTE = 'Bulk property analysis available by quote.';

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
        markets: ['Miami-Dade County']
      },
      {
        key: 'expanding',
        label: 'Live · expanding coverage',
        blurb: 'Live now on county tax-roll records and recorded sales. Code and lien depth is still being added county by county.',
        markets: [
          'Broward County',
          'Lee County (Fort Myers)',
          'Collier County (Naples)',
          'Polk County',
          'Lake County'
        ]
      },
      {
        key: 'requested',
        label: 'Requested · under evaluation',
        blurb: 'On the evaluation list. We review public-data availability and update frequency before committing a launch date. Request yours to move it up the queue.',
        markets: [
          'Palm Beach County',
          'Hillsborough County (Tampa)',
          'Orange County (Orlando)'
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
            // Payment link configured — the button goes straight to checkout; trial stays one click away.
            return '<a class="da-btn ' + (p.featured ? 'da-btn--primary' : 'da-btn--dark') + ' plan__cta" ' +
              'href="' + esc(pay) + '" data-track="subscribe_click" data-plan="' + esc(p.id) + '">' +
              'Subscribe — ' + esc(p.price) + esc(p.cadence) + ' <span aria-hidden="true">&rarr;</span></a>' +
              '<p class="plan__note" style="text-align:center;margin-top:8px">or <a href="trial.html?plan=' + esc(p.id) + '" style="text-decoration:underline">try free for 7 days first</a></p>';
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

  function renderMarkets(containerId) {
    var box = el(containerId); if (!box) return;
    box.innerHTML = MARKETS.tiers.map(function (t) {
      var pills = t.markets.length
        ? '<div class="market-tier__pills">' + t.markets.map(function (m) {
            return '<span class="market-pill market-pill--' + esc(t.key) + '">' + esc(m) + '</span>';
          }).join('') + '</div>'
        : '<p class="market-tier__empty">None scheduled yet.</p>';
      return '<div class="market-tier market-tier--' + esc(t.key) + '">' +
        '<div class="market-tier__head">' +
          '<span class="market-tier__label">' + esc(t.label) + '</span>' +
          '<span class="market-tier__count">' + t.markets.length + '</span>' +
        '</div>' +
        '<p class="market-tier__blurb">' + esc(t.blurb) + '</p>' +
        pills +
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
