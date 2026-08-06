import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type ValidationReportResponse = components['schemas']['ValidationReportResponse']

export function useValidationReport(id: string | null) {
  return useQuery({
    queryKey: qk.validation.report(id!),
    queryFn: (): Promise<ValidationReportResponse> =>
      client.get(`/api/validation/${id}/report`),
    enabled: !!id,
    staleTime: Infinity,
  })
}
