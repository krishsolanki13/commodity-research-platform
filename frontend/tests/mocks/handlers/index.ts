import { assetHandlers } from './assets'
import { systemHandlers } from './system'
import { runHandlers } from './runs'
import { featureHandlers } from './features'
import { indicatorHandlers } from './indicators'
import { signalHandlers } from './signals'

export const handlers = [
  ...assetHandlers,
  ...systemHandlers,
  ...runHandlers,
  ...featureHandlers,
  ...indicatorHandlers,
  ...signalHandlers,
]
