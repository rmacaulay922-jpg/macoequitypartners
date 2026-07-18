# FDOR Data Harness Report

Run: 2026-07-17 21:43 ET through 2026-07-18 01:55 ET (~4.2 h wall clock, most of it waiting out server load-shedding; ~40 min of actual query time). Source: FDOR Florida Statewide Cadastral ArcGIS layer (services9.arcgis.com / Florida_Statewide_Cadastral, FeatureServer 0), assessment year 2025 roll.
All values are verbatim FDOR fields. Nothing interpolated; missing is missing.

## 1) fdor-mailing-miami.js — Miami-Dade owner mailing backfill

- Folio universe: 2397 (2,397 keys of `window.MIA_HS` in mia-homestead.js; the 2,397 folios found in portal.html pa_url links are the same set).
- **Mailing/owner record found for 2394/2397 folios.**
- 3 folios returned no FDOR row: 3040300080010, 3050050041210, 3050080100380
- Folio-to-PARCEL_ID mapping verified before the batch run: FDOR PARCEL_ID for Dade = the 13 folio digits with dashes stripped, no county prefix. 3 test folios returned exact PHY_ADDR1 matches (9201 SW 93 AVE / 10044 SW 131 TER / 7315 SW 140 CT); dashed and '23'-prefixed formats returned 0 rows.
- Note: FDOR OWN_NAME is capped at ~30 chars by the state roll, so long names arrive truncated. OWN_ZIPCD=0 rows (missing zip on the roll) have `zip` omitted rather than guessed.

### Spot checks (FDOR PHY_ADDR1 vs. portal property address)

| Folio | FDOR site addr | Portal site addr | FDOR mailing | Match |
|---|---|---|---|---|
| 03-4132-004-0040 | 7901 ERWIN RD | 7901 ERWIN RD | 7901  ERWIN RD, CORAL GABLES FL | yes |
| 30-4033-020-0300 | 9623 SW 79 TER | 9623 SW 79 TER | 6850 CARTEE RD, MIAMI FL | yes |
| 30-5005-018-0650 | 9211 SW 100 AVENUE RD | 9211 SW 100 AVENUE RD | 9211 SW 100 AVENUE RD, MIAMI FL | yes |
| 30-5018-014-0420 | 13532 SW 114 PL | 13532 SW 114 PL | 13532 SW 114 PL, MIAMI FL | yes |
| 30-5903-037-1330 | 14347 SW 101 LN | 14347 SW 101 LN | 14347 SW 101 LN, MIAMI FL | yes |

### Owner-name mismatches (portal vs. FDOR): 119

Rows are included in fdor-mailing-miami.js regardless (FDOR is the newer roll; the portal name may be stale, reformatted, or the parcel may have changed hands). Compared on word-token sets so 'JOHN SMITH' vs 'SMITH JOHN' is NOT flagged; listed below are folios where the token overlap is under 50%.

| Folio | Portal owner | FDOR owner |
|---|---|---|
| 03-5105-007-0020 | WOLFY ESTATES LLC | RAFAEL VILLOLDO |
| 03-5105-010-0210 | BETTY HORWITZ TRS | LILIANE ECKSTEIN |
| 03-5106-006-0081 | ZERIOSHA ZAPATA | TIMOTHY Z MOSLEY |
| 03-5107-010-0070 | CARLOS G ALONSO LE | CARLOS G ALONSO &W MAGALY L |
| 03-5118-005-0330 | JENNIFER'S ESTATES LLC | CRISTOBAL MARIN &W VIVIAN |
| 03-5118-006-0120 | EMTIFFANY LLC | 1022 CASA DEL MAR LLC |
| 09-4025-015-0780 | NIKOLAI PUNTIKOV | KYLE XU |
| 09-4025-034-0050 | ENRIQUE NEUFELD TRS | ISMAEL DEMARCHENA |
| 09-4036-039-0390 | 5930 SW 80ST LLC | KELLY ZIDIK |
| 20-5002-009-0240 | CARLOS A VARA | LUIS A VELAZQUEZ &W MARITZA |
| 20-5010-005-0033 | DOMINIQUE MONDINI TRS | HELEN WILLIAMS LE |
| 20-5011-004-0570 | KAI LATIN LEAF LLC | ITALICA INC |
| 20-5011-020-0080 | YAAKOV MILBAUER TRS | YAAKOV MILBAUER &W BAT-SHEVA |
| 20-5011-028-0180 | DANIEL DIEGUEZ | 7125 LLC |
| 20-5012-000-0280 | DOUGLAS JORDAN | ALEC MACHIELS |
| 20-5013-028-0290 | THOMAS B NEWBERN TRS | GLHB HOUSING LLC |
| 20-5013-031-0080 | LEONEL OSWALDO ENRIQUEZ ENRIQUEZ | MICHAEL KRESS |
| 20-5014-000-0643 | PETER A RAHAGHI | DANIEL M WEINBACH &W RANDI |
| 20-5014-011-0630 | ATHANASIOS GAVATIDES TRS | PANAGIOTA GAVATIDES EST OF |
| 20-5014-016-0140 | MILAGROS A SANCHEZ | AGUSTIN FELIX BRUGUERA LE |
| 20-5014-023-0020 | DAMARIS SALCINES | SATINDER BAVEJA &W GURPREET |
| 20-5015-000-0790 | RAMIRO FINOL | MELANIE A CAMBRIDGE |
| 20-5015-006-1130 | OMAR MONTESINO JR | ALEJANDRO PEREDA |
| 20-5015-014-0770 | BYT INVESTMENT GROUP LLC | GREGORY ORTIZ |
| 20-5015-017-0160 | NATIONAL CASH DEALS LLC | LINDSEY E BROWN TRS |
| 30-4025-035-1100 | 5760 TOWNHOMES LLC | ENRIQUE NEUFELD TRS |
| 30-4030-075-0180 | BARBARA C BENITEZ | LLOYD B MUCCIO &W MARLEN |
| 30-4031-035-0620 | ROGER E LYTTLETON | MATTHEW HILL |
| 30-4033-003-0400 | NANCY ROQUE DE ESCOBAR LE | EVELIO ROQUE DE ESCOBAR &W NAN |
| 30-4033-034-0040 | JANICE C FREEMAN | WELLS FARGO BANK N A TRS |
| 30-4034-015-0030 | MARGARITA C SALAZAR TRS | OMAR M SALAZAR |
| 30-4035-003-0100 | SAI PROPERTY HOLDINGS INC | GB2 7635 LLLP |
| 30-4910-044-0190 | OCTAVIO RAMOS LE | MELBA BEQUER |
| 30-4910-076-0090 | MARIA MONROY | MANUEL ROJO EST OF |
| 30-4915-003-1100 | ERIC GARCIA LE | ERIC GARCIA &W MELISSA |
| 30-4922-028-0760 | ERIC MENDEZ LE | ERIC MENDEZ &W JESSICA L |
| 30-4924-001-1910 | CARLOS CRUZ | FRANCISCO AIXALA TRS |
| 30-4934-002-0370 | NATASHA ISABEL GARCIA | LEONARD L CLAVAN |
| 30-4934-003-0120 | ERNESTO EDUARDO GOMEZ | RAQUEL SWEENY LE |
| 30-4934-007-0150 | EVANGELINA M DE OCA GARCIA LE | SARA ALVAREZ |
| 30-4935-003-1440 | YOVANNA DEL C HERNANDEZ LE | VICTOR M FERNANDEZ LE |
| 30-4936-003-0580 | JOSE ANTONIO ARRIAGA TRS | JOSE A ARRIAGA &W MARIA A |
| 30-5003-000-0620 | IGNACIO SERRALTA TRS | IGNACIO SERRALTA &W VIVIAN |
| 30-5003-007-0150 | 7800 SW 95 ST LLC | LUIS CATA &W DINORAH HERNANDEZ |
| 30-5003-020-0140 | SERGIO TIERRABLANCA | ELLIOTT N ZACK &W GLORIA M |
| 30-5004-026-0120 | MONA LISA MCDONOUGH | CLAUDETTE MARTINO LE |
| 30-5006-000-0721 | ANA TERESA MARQUEZ TRS | B2R BUILDERS LLC |
| 30-5006-013-0570 | SERGIO FLORES | ENRIQUE A DIAZ |
| 30-5007-004-0130 | SUSANN MARIE TAYLOR | SHIRLEY M TAYLOR |
| 30-5007-016-0970 | CARLOS A LASTRA | ASHLEY MAGAGNA PYEATT |
| 30-5008-016-0230 | EDGAR RAMIREZ | CARLOS J MARTINEZ &W |
| 30-5009-004-0140 | WESTON EQUITY GROUP LLC | JON J ALEXIOU |
| 30-5009-005-0030 | SURY MARIE NIEVES TRS | JORGE ENRIQUE LEAL |
| 30-5009-015-0020 | 8820 PALMETTO LLC | E RODRIGUEZ-ORLANDO |
| 30-5010-012-0130 | MARCOS ALMEIDA DA MOTA | ARIC DANIEL GASPER TRS |
| 30-5016-003-0300 | SERGIO ENRIQUE GONZALEZ | ANDRES HERNANDEZ |
| 30-5016-013-0010 | JAMES R PERKINS TRS | JAMES R PERKINS JR &W BARBARA |
| 30-5016-030-0280 | OSCAR ALEJANDRO VARONA | ANGELA SCHULER |
| 30-5017-010-0670 | JOCELYN LOURDES GUILLEN | ALEJANDRO MANUEL GARCIA |
| 30-5017-016-0010 | WILFREDO MELENDEZ | JOSE M RODRIGUEZ &W RACHEL L |
| 30-5017-033-0080 | SUSY CALZADILLA | ERIC MATA |
| 30-5017-041-0050 | CSM 10000 LLC | CLIFFORD MARZOUKA |
| 30-5018-007-1040 | GRISSETE M MORENO | FELIPE J ALVAREZ |
| 30-5018-014-1610 | MARIBEL EBRA | RALPH J EBRA &W |
| 30-5018-014-2250 | JUAN MACLOVIO BARRIOS LE | MACLOVIO BARRIOS &W ELIDA |
| 30-5018-014-2980 | MICHAEL SAINT GEORGE JACKSON LE | MICHAEL S JACKSON &W PATRICIA |
| 30-5019-001-0290 | GREEN LEAVES CONSULTING LLC | ADRIENNE THOMPKINS |
| 30-5019-001-0970 | LIANA BORREGO CARMONA | RODILVER FERNANDEZ LEYVA |
| 30-5019-001-3760 | LUIS ARIAS | 14800 JACKSON ST LLC |
| 30-5019-001-4430 | GUSTAVO URBANO QUINTERO | LAZARO DIAZ LUIS |
| 30-5019-002-1310 | MVP DEVELOPERS GROUP LLC | THEODORE PENDER |
| 30-5019-002-1740 | ALEXANDRA MARIA ROJAS | W B H INVESTMENTS LLC |
| 30-5019-003-0150 | ANSIL PEGUES LE | ANSIL PEGUES &W KAREN |
| 30-5019-003-0700 | MVP DEVELOPERS GROUP LLC | RUBY JEAN SMITH LE |
| 30-5019-003-1110 | JACKIE JENSEN CARTER | RANDER CARTER JR |
| 30-5019-014-0080 | EDDY SANCHEZ TELLEZ | ALTHEA MCMILLAN |
| 30-5019-014-1010 | THOMAS BEVEL SIMMONS TRS | MARGARET C HART |
| 30-5020-005-0410 | MARION COX | TYREE JOHNSON |
| 30-5020-011-0270 | JOSE LUIS FLORES SALINAS | GRANDVIEW VENTURES LLC |
| 30-5020-019-0440 | BARBARA K MAYKOX | ROBERT J MAYCOX |
| 30-5020-021-1370 | RONALD M AHEARN LE | RONALD M AHEARN &W MARIA J |
| 30-5020-021-1780 | CARLOS REYNA | RADAMES RODRIGUEZ &W ROSE |
| 30-5021-018-0410 | MARIA E PEREZ | PEREZ FAMILY ACQUISITION FUND |
| 30-5021-025-0460 | TERESA DE JESUS GILBERT | DAVID A GILBERT EST OF |
| 30-5029-019-0150 | YUNIERKY MENDOZA RODRIGUEZ | JEFFREY W LEWIS |
| 30-5029-035-0050 | MANUEL O MENOYA | CIRO DE LA PAZ |
| 30-5029-039-0300 | OLIVIA NATHANIEL AND ASSOCIATES | ANDREW ELLISTON |
| 30-5030-003-0740 | MONICA M COTO | RAS ASSOCIATES CORP |
| 30-5030-011-0520 | BLUEHAVEN HOLDINGS FL LLC | SHIRLEY BROWN |
| 30-5031-002-1440 | SADAIMARY LLANES BRENA | L & L SERVICES GROUP INC |
| 30-5031-015-0180 | ADHD 11111 LLC | HERMAN W DORSETT TRS |
| 30-5031-026-0090 | JEREMAZINE KIRKLAND | VULCAN DYNAMIC REALTY FD LP |
| 30-5901-022-0040 | MIGUEL ANGEL RODRIGUEZ | DARIEN ARMANDO MARTINEZ |
| 30-5901-065-0230 | CARLOS LOPEZ | JOSE A AGUAYO |
| 30-5902-002-1180 | IVAN VILLALOBOS | CALUSA CLUB HOME LLC |
| 30-5903-036-0560 | LAZARO CEPERO TRS | LAZARO CEPERO &W MARTHA |
| 30-5904-002-0800 | LUZ ELENA JACOME | LUZ E JACOME ET ALS (BEN) |
| 30-5904-006-0680 | AURELIEN MERAY | ROBERT MORGAN |
| 30-5904-063-0730 | ROSENDO LLANO TRS | ROSENDO V LLANO &W VIRGINIE W |
| 30-5908-013-0160 | REINALDO RODRIGUEZ GUERRERO | CERBERUS SFR HOLDINGS L P |
| 30-5909-044-0050 | ROBERTO JOSE BLANDON JR | JOSE F VALECILLOS &W ROSA |
| 30-5909-044-0390 | TERENCE HONG TRS | TERENCE HONG &W LINDA WOOLFSON |
| 30-5920-003-0870 | SHEILA DE LA CONCEPCION ROVIRA | SHEILA D ROVIRA |
| 30-5920-004-0520 | DAYETSI D LOPEZ GARCIA | REN REALTY INVESTMENT LLC |
| 30-5921-001-2080 | TATYANA G FERREIRA DE OLIVEIRA | ANNETTA MCEACHERN |
| 30-5921-005-0880 | DIANA ROSA CORDOBA LE | DIANA R CORDOBA |
| 30-5921-009-0140 | IDANIA HERNANDEZ | PEDRO J VALDES &W ANGELA |
| 30-5923-017-0030 | YULIANA OSSA BARRAGAN | HAI XIN |
| 33-5021-011-0040 | MARIA A MARTINEZ TRS | VINCENT J WARGER &W JOAN Q TRS |
| 33-5022-005-0020 | JAIME ROJAS TRS | JAIME ROJAS &W MARIA |
| 33-5027-002-1680 | MARIA MIGDALIA FERNANDEZ TRS | MARIA MIGDALIA FERNNADEZ |
| 33-5027-038-0120 | MARK KACER | CHERYL M SHECHTER |
| 33-5032-007-0650 | FRANJO PROPERTIES LLC | OPTICAL CRIME PREVENTION INC |
| 33-5034-004-0090 | RYAN MACAULAY | THORARINN THORARINSSON |
| 33-5034-021-0240 | SAKIR N ALI JR | JOSEPH BARLOW |
| 36-6003-034-4720 | ABID DEFALCO | MARIA DEFALCO |
| 36-6004-010-0410 | S & L DEVELOPMENT HOLDINGS LLC | DONALD THOMPSON &W ELIZABETH A |
| 36-6005-007-1770 | FIDEL DIAZ LOPEZ | FELIX RAMOS |
| 36-6005-015-0040 | YARENIS PROENZA RODRIGUEZ | BELLA INVESTORS LLC |

## 2) fdor-enrich.js — sqft / year-built / last-sale backfill

- Broward: **600/600** lead parcels returned FDOR data.
- Lee: **600/600** lead parcels returned FDOR data.
- Collier: **599/599** lead parcels returned FDOR data.
- Polk: **867/867** lead parcels returned FDOR data.
- Only keys with at least one real value are emitted; individual missing fields (e.g. no last sale) are omitted.

### Spot checks (FDOR site address vs. lead-file address)

| County | PID | FDOR addr/zip | Lead addr/zip | sqft | yb | last sale | Match |
|---|---|---|---|---|---|---|---|
| broward | 474135010010 | 7200 LOXAHATCHEE RD 33067 | 7200 Loxahatchee Rd 33067 | 2868 | 1950 | - | yes |
| lee | 01442404000000730 | 1273 SUNRISE DR 33917 | 1273 Sunrise Dr 33917 | 1932 | 1961 | - | yes |
| collier | 00066160007 | 3077 SR 29  N 34142 | 3077 Sr 29  N 34142 | 3677 | 1967 | - | yes |
| polk | 232703000000024090 | 2335 D R BRYANT RD 33809 | 2335 D R Bryant Rd 33809 | 2651 | 1979 | $100 (2024, q=11) | yes |
| polk | 262814533502000280 | 160 BROAD ST 33881 | 160 Broad St 33881 | 3013 | 2016 | - | yes |

## 3) zip-value-bands.js — qualified-sale $/sf bands

- Zips covered: 97 (property zips from broward/lee/collier/polk lead files, plus Clermont 34711/34714/34715 for Lake — lake-leads.js has no property zips; 34711 and 34715 are corroborated by owner mailing addresses inside lake-leads.js, 34714 is the third Clermont-area zip and was queried on that basis).
- Lee lead file contains one junk zip value '0' — excluded.
- **92 zips published; 5 skipped as too thin (n<8 after filters/trim).**
- Sale filter: DOR_UC 001, QUAL_CD1 in ('01','02'), SALE_YR1>=2024, sale > $50k, living area > 500 sf. Raw sales pulled and statistics computed locally (server-side statistics queries 400 on this host); $/sf outside $60-$1,200 dropped, then top/bottom 5% trimmed; median/p25/p75 on the trimmed set.
- Collection method (matters for coverage): per-zip filtered scans and ids-only queries were load-shedded by the host all evening (transient 400s / 504s regardless of pagination). What the host tolerates is scans whose cost is bounded by an OBJECTID range. County parcels sit in contiguous OBJECTID blocks (verified by sampling OBJECTIDs of known lead parcels; blocks run alphabetically by county). Each county block was swept in adaptive 5k-100k-OID ranges with the sale filter plus a PHY_ZIPCD IN (county zips) clause, and rows were bucketed per zip locally. Segments swept: 100k-500k + 1.9M-2.45M (Collier), 500k-1.9M (Broward), 3.7M-4.4M (Lake), 4.15M-4.75M (Lee), 8.4M-9.2M (Polk); 30,721 sale rows collected in 24 minutes once the sweep design landed.
- Coverage caveat (honest disclosure): the sweep envelopes were padded far beyond every sampled parcel OBJECTID, but FDOR occasionally re-appends updated parcels OUTSIDE their county's block (one Collier lead parcel sits at OBJECTID 214k vs the 2.0-2.27M block — that stray region was swept too). Any similar strays outside all swept segments would be missed; with per-zip n in the hundreds, a handful of missing rows cannot materially move a median. Bands are honest medians of what the state roll serves, not appraisals.

### Skipped zips

| Zip | County | Raw sales | In $60-1200 band | After trim | Reason |
|---|---|---|---|---|---|
| 33845 | polk | 6 | 6 | 6 | only 6 usable qualified sales (<8) - too thin to publish |
| 34138 | collier | 0 | 0 | 0 | only 0 usable qualified sales (<8) - too thin to publish |
| 34139 | collier | 7 | 7 | 7 | only 7 usable qualified sales (<8) - too thin to publish |
| 34140 | collier | 3 | 3 | 3 | only 3 usable qualified sales (<8) - too thin to publish |
| 34141 | collier | 0 | 0 | 0 | only 0 usable qualified sales (<8) - too thin to publish |

### Spot checks (published bands + sample sale addresses from the same query)

| Zip | County | med $/sf | p25 | p75 | n | Sample sale addresses |
|---|---|---|---|---|---|---|
| 33060 | broward | $308 | $271 | $409 | 443 | 2341 NE 1 AVE, 2221 NE 2 AVE |
| 33321 | broward | $261 | $240 | $289 | 559 | 9111 NW 83 ST, 9701 NW 83 ST |
| 33853 | polk | $132 | $115 | $150 | 197 | 268 LAKE SUZANNE DR, 340 LAKE SUZANNE DR |
| 33916 | lee | $144 | $125 | $164 | 140 | 3825 SCHOOLHOUSE RD E, 4291 AVIAN AVE |
| 34104 | collier | $288 | $258 | $322 | 211 | 91 GLEN EAGLE CIR, 7948 LEICESTER DR |

## Run notes

- Final harness process (the one that completed all remaining work via the OID-range sweep) ran 24.0 minutes end to end; total wall clock across the session was ~4.2 hours.
- Throttle events (each followed by a full 8.5-minute cooldown before resuming): 14. Where: miami batch 10 (21:48:55); miami batch 17 (22:02:15); miami batch 18 (22:19:15); zip 33060 (23:15:22); zip 33060 (23:32:39); zip 33060 page @oid>1088931 (23:54:36); zip 33060 ids (00:06:30); zip 33060 ids (00:18:01); zip 33062 ids (00:28:50); zip 33060 ids (00:39:21); zip 33060 cursor @oid>1078234 (00:53:47); zip 33060 cursor @oid>1078234 (01:03:13); zip 33060 cursor @oid>1078234 (01:12:39); zip 33060 cursor @oid>1078234 (01:23:58)
- Host behavior encountered, for the next run: (1) 90-ID `PARCEL_ID IN` GET URLs bounce with an XHTML 404 page — use POST; (2) under load the host progressively slows then 504s heavy queries — 45-ID IN-batches stayed reliable when 90-ID batches started failing; (3) from ~23:00 to ~01:30 the host load-shedded every full-table scan (ids-only, statistics, unbounded filtered pages) with empty-message 400s while still serving indexed lookups and OID-range-bounded scans — the bounded-sweep design in section 3 is the workaround, and it also avoids the hidden full-table 'prove the last page is empty' scan that stalls per-zip cursor paging.
- Pacing: 3-5s sleeps between queries early, widened to 6.5-9.5s after the first 504; resultOffset never used (host rejects it); OBJECTID-cursor ordering used where paging was needed. All partial progress saved to disk after every batch; the run survived 8 process restarts with no data loss.
- Deliverable outputs are additive join files; portal.html and the *-leads.js files were not modified.

