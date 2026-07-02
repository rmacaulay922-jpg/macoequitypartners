// Collier County (Naples) motivated-seller leads — POPULATED BY scrape_fl_county.py (config:
// collier). Same lead schema as Polk (window.POLK_LEADS) + parcel-centroid lat/lng for the
// crime-band overlay. Empty until the scrape runs. NOTE: Naples is a luxury/coastal market —
// thin flip inventory; expect a smaller, higher-value lead set than the other counties.
window.COLLIER_LEADS=[];
window.COLLIER_META={county:'Collier',count:0,snapshot:'',markets:[]};
