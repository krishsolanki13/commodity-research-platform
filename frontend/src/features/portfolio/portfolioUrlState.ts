import { z } from 'zod'

export const portfolioUrlSchema = z.object({
  run_id: z.string().optional(),
  strategy: z.string().default('ema_crossover'),
  sizing_method: z
    .enum(['fixed_notional', 'volatility_scaled'])
    .default('fixed_notional'),
  initial_capital: z.coerce.number().default(1_000_000),
})

export const portfolioUrlDefaults: z.infer<typeof portfolioUrlSchema> = {
  run_id: undefined,
  strategy: 'ema_crossover',
  sizing_method: 'fixed_notional',
  initial_capital: 1_000_000,
}
