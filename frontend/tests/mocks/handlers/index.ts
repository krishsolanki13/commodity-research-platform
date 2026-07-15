import { assetHandlers } from './assets'
import { systemHandlers } from './system'
import { runHandlers } from './runs'
import { featureHandlers } from './features'

export const handlers = [
  ...assetHandlers,
  ...systemHandlers,
  ...runHandlers,
  ...featureHandlers,
]
