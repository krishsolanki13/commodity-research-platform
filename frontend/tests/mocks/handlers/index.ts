import { assetHandlers } from './assets'
import { systemHandlers } from './system'
import { runHandlers } from './runs'
import { featureHandlers } from './features'
import { indicatorHandlers } from './indicators'
import { signalHandlers } from './signals'
import { backtestHandlers } from './backtests'
import { runsDetailHandlers } from './runs-detail'
import { compareHandlers } from './compare'
import { curveHandlers } from './curves'
import { portfolioHandlers } from './portfolio'

export const handlers = [
  ...assetHandlers,
  ...systemHandlers,
  ...runHandlers,
  ...featureHandlers,
  ...indicatorHandlers,
  ...signalHandlers,
  ...backtestHandlers,
  ...runsDetailHandlers,
  ...compareHandlers,
  ...curveHandlers,
  ...portfolioHandlers,
]
