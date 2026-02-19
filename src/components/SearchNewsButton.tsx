'use client'

import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Search, Loader2, CheckCircle } from 'lucide-react'

export default function SearchNewsButton({ competitorName }: { competitorName: string }) {
    const [state, setState] = useState<'idle' | 'scanning' | 'done' | 'error'>('idle')
    const [step, setStep] = useState<string | null>(null)
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

                    if (data.currentStep) {
                        setStep(data.currentStep)
                    }

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
            <Button disabled className="bg-slate-800 text-slate-300 border border-slate-700 gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                {step ? `Scanning...` : 'Starting scan...'}
            </Button>
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
