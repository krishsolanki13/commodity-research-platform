import { useMutation } from '@tanstack/react-query'
import { client } from '@/api/client'
import type { components } from '@/api/schema'

type ValidationLaunchRequest = components['schemas']['ValidationLaunchRequest']
// Launch returns ValidationStatusResponse (no ValidationLaunchResponse in schema)
type ValidationStatusResponse = components['schemas']['ValidationStatusResponse']

export function useValidationLaunch() {
  return useMutation({
    mutationFn: (request: ValidationLaunchRequest): Promise<ValidationStatusResponse> =>
      client.post('/api/validation/run', request),
  })
}
