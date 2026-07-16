import { useMemo } from 'react'
import { z } from 'zod'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/tabs'
import { useUrlState } from '@/lib/useUrlState'
import { cn } from '@/lib/cn'

interface TabDef {
  value: string
  label: string
  content: React.ReactNode
}

interface TabsUrlSyncProps {
  tabs: TabDef[]
  defaultTab?: string
  urlParam?: string
  className?: string
}

export function TabsUrlSync({ tabs, defaultTab, urlParam = 'tab', className }: TabsUrlSyncProps) {
  const schema = useMemo(() => z.object({ [urlParam]: z.string().optional() }), [urlParam])

  const firstTabValue = tabs[0]?.value
  const defaults = useMemo(
    () => ({ [urlParam]: defaultTab ?? firstTabValue ?? '' }),
    [urlParam, defaultTab, firstTabValue]
  )

  const [state, setState] = useUrlState(schema, defaults)

  const rawParam = (state as Record<string, string | undefined>)[urlParam]
  const activeTab =
    rawParam !== undefined && tabs.some((t) => t.value === rawParam)
      ? rawParam
      : (defaultTab ?? tabs[0]?.value ?? '')

  function handleTabChange(value: string) {
    // useUrlState already applies { replace: true } on every update
    setState({ [urlParam]: value })
  }

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange} className={cn('w-full', className)}>
      <TabsList>
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value}>
          {tab.content}
        </TabsContent>
      ))}
    </Tabs>
  )
}
