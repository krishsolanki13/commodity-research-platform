import { z } from 'zod'

export const portfolioUrlSchema = z.object({
  run_id: z.string().optional(),
})

export const portfolioUrlDefaults: z.infer<typeof portfolioUrlSchema> = {
  run_id: undefined,
}
