import { EmptyState } from '@/components/layout/EmptyState'

export default function DataManagerScreen() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold text-text-primary">Data Manager</h1>
      <EmptyState
        className="h-64 mt-8"
        title="Data ingestion management"
        body="Contract acquisition and pipeline controls coming soon."
      />
    </main>
  )
}
