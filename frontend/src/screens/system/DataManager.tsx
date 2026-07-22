import { EmptyState } from '@/components/layout/EmptyState'

export default function DataManagerScreen() {
  return (
    <main className="p-6">
      <h1 className="font-ui text-xl text-text-emphasis">Data Manager</h1>
      <EmptyState
        className="mt-8 h-64"
        title="Data ingestion management"
        body="Contract acquisition and pipeline controls coming soon."
      />
    </main>
  )
}
