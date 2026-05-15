# Maco Equity Partners — Website

Source for [macoequitypartners.com](https://macoequitypartners.com).

## Structure

- `index.html` — Landing page
- `research.html` — Research & market reports index
- `blog.html` — Insights blog
- `styles.css` — Shared design system
- `Q1_2026_*.html` — Quarterly market reports
- `CNAME` — Custom domain for GitHub Pages

## Local preview

Open `index.html` directly in a browser, or serve the folder:

```bash
python -m http.server 8080
# then visit http://localhost:8080
```

## Deploy

Push to the `main` branch — GitHub Pages serves the site automatically via the `CNAME` file.
