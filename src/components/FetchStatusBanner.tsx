'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export default function FetchStatusBanner() {
    const [status, setStatus] = useState<{
        status: string
        currentStep: string | null
        processed: number
        total: number
    } | null>(null)

    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch('/api/fetch-status')
                if (res.ok) {
                    const data = await res.json()
                    if (data.status === 'running' || data.status === 'pending') {
                        setStatus(data)
                    } else {
                        setStatus(null)
                    }
                }
            } catch { /* ignore */ }
        }

        poll()
        const interval = setInterval(poll, 5000)
        return () => clearInterval(interval)
    }, [])

    if (!status) return null

    return (
        <div className="mb-4 bg-cyan-950/50 border border-cyan-800/50 rounded-lg px-4 py-3 flex items-center gap-3">
            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin flex-shrink-0" />
            <div className="flex-1 min-w-0">
                <p className="text-sm text-cyan-300">
                    News is being fetched for your competitors...
                    {status.currentStep && (
                        <span className="text-cyan-400 ml-1">({status.currentStep})</span>
                    )}
                </p>
                {status.total > 0 && (
                    <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 bg-slate-800 rounded-full h-1.5 max-w-[200px]">
                            <div
                                className="bg-cyan-500 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${(status.processed / status.total) * 100}%` }}
                            />
                        </div>
                        <span className="text-xs text-slate-400">{status.processed}/{status.total}</span>
                    </div>
                )}
            </div>
        </div>
    )
}
