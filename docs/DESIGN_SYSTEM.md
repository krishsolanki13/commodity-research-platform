# Design System

## 2. Color Semantics

### 2.2 Regime Colors

Regime color semantics (confirmed F9, implemented F9–FEP):

- **CONTANGO** → `text-warn` (amber, `--warn-500`) — roll cost to longs
- **BACKWARDATION** → `text-gain` (green, `--gain-500`) — roll yield to longs
- **FLAT** → `text-text-secondary` (gray, `--gray-500`)

Note: Earlier documentation referenced `tone.regime()` → loss/red for contango. This was never implemented. Amber/warn is the confirmed platform standard, aligned with FuturesCurve markArea fills (F17-hotfix HF-7) and RegimeBreakdownChart (FEP Inc4).
