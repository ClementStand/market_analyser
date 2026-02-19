'use client'

import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Search, Loader2, CheckCircle } from 'lucide-react'

export default function SearchNewsButton({ competitorName }: { competitorName: string }) {
    const [state, setState] = useState<'idle' | 'scanning' | 'done' | 'error'>('idle')
    const [step, setStep] = useState<string | null>(null)
    const [processed, setProcessed] = useState(0)
    const [total, setTotal] = useState(0)
    const intervalRef = useRef<NodeJS.Timeout | null>(null)
    const router = useRouter()

    const cleanup = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
        }
    }, [])

    const handleSearch = async () => {
        setState('scanning')
        setStep(null)
        setProcessed(0)
        setTotal(0)

        try {
            const res = await fetch('/api/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ competitorName, days: 14 }),
            })

            if (!res.ok) {
                setState('error')
                return
            }

            const { jobId } = await res.json()
            if (!jobId) {
                setState('error')
                return
            }

            // Poll for completion
            intervalRef.current = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/api/fetch-status?jobId=${jobId}`)
                    if (!statusRes.ok) return
                    const data = await statusRes.json()

                    if (data.currentStep) setStep(data.currentStep)
                    if (data.processed != null) setProcessed(data.processed)
                    if (data.total != null) setTotal(data.total)

                    if (data.status === 'completed') {
                        cleanup()
                        setState('done')
                        router.refresh()
                        setTimeout(() => setState('idle'), 3000)
                    } else if (data.status === 'error') {
                        cleanup()
                        setState('error')
                        setTimeout(() => setState('idle'), 5000)
                    }
                } catch { /* ignore polling errors */ }
            }, 4000)
        } catch {
            setState('error')
            setTimeout(() => setState('idle'), 5000)
        }
    }

    if (state === 'scanning') {
        return (
            <div className="flex items-center gap-3 bg-slate-800 text-slate-300 border border-slate-700 rounded-md px-4 py-2">
                <Loader2 className="h-4 w-4 animate-spin text-cyan-400 shrink-0" />
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm">{step ? `Scanning: ${step}` : 'Starting scan...'}</span>
                    {total > 0 && (
                        <div className="flex items-center gap-2">
                            <div className="bg-slate-900 rounded-full h-1.5 w-24">
                                <div
                                    className="bg-cyan-500 h-1.5 rounded-full transition-all duration-500"
                                    style={{ width: `${(processed / total) * 100}%` }}
                                />
                            </div>
                            <span className="text-xs text-slate-400">{processed}/{total}</span>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    if (state === 'done') {
        return (
            <Button disabled className="bg-green-900/50 text-green-300 border border-green-800 gap-2">
                <CheckCircle className="h-4 w-4" />
                Scan complete
            </Button>
        )
    }

    if (state === 'error') {
        return (
            <Button disabled className="bg-red-900/50 text-red-300 border border-red-800 gap-2">
                Scan failed
            </Button>
        )
    }

    return (
        <Button
            onClick={handleSearch}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 gap-2 shadow-lg shadow-black/20"
        >
            <Search className="h-4 w-4 text-cyan-400" />
            Search News (2 weeks)
        </Button>
    )
}
