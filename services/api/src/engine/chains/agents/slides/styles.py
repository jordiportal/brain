"""CSS styles para las presentaciones."""

SLIDES_CSS = """
<style>
.slide {
  padding: 32px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  min-height: 400px;
}
.slide h1 {
  font-size: 2.2rem;
  margin-bottom: 16px;
  color: #e94560;
}
.slide h2 {
  font-size: 1.6rem;
  margin-bottom: 12px;
  color: #0f3460;
  background: linear-gradient(90deg, #e94560, #f39c12);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.slide p {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 12px;
}
.slide ul, .slide ol {
  margin-left: 24px;
  margin-bottom: 16px;
}
.slide li {
  margin-bottom: 8px;
  line-height: 1.5;
}
.badge {
  display: inline-block;
  padding: 4px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 20px;
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
  margin-bottom: 12px;
}
.highlight {
  color: #f39c12;
  font-weight: 600;
}
.stats {
  display: flex;
  gap: 32px;
  margin: 24px 0;
}
.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #e94560;
}
.stat-label {
  font-size: 0.9rem;
  color: #888;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}
.card {
  background: rgba(255,255,255,0.05);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
}
.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #e94560;
}
.card-desc {
  font-size: 0.95rem;
  color: #ccc;
}
.quote {
  border-left: 4px solid #e94560;
  padding-left: 20px;
  font-style: italic;
  margin: 20px 0;
  color: #ddd;
}
.code {
  background: rgba(0,0,0,0.3);
  padding: 16px;
  border-radius: 8px;
  font-family: monospace;
  overflow-x: auto;
}
</style>
"""
