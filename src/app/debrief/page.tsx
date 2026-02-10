'use client'
import { useState, useEffect, Suspense } from 'react'
import { format, subDays } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { Sidebar } from '@/components/Sidebar'

export default function WeeklyDebrief() {
    const [debrief, setDebrief] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [itemCount, setItemCount] = useState<number | null>(null)

    // Range Options
    const [rangeType] = useState<'7d'>('7d')

    // Calculate dates based on range type
    const getDates = () => {
        const end = new Date()
        const start = subDays(end, 7)
        return { start, end }
    }

    // Fetch Count
    const checkCount = async () => {
        const { start, end } = getDates()

        const payload: any = { mode: 'count' }
        if (start) {
            payload.startDate = start.toISOString()
            payload.endDate = end.toISOString()
        }

        try {
            const res = await fetch('/api/debrief', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            const data = await res.json()
            setItemCount(data.count)
        } catch (e) {
            console.error(e)
        }
    }

    useEffect(() => {
        checkCount()
    }, [rangeType])

    const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(null)

    // Load from LocalStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem('abuzz_weekly_debrief')
        if (saved) {
            try {
                const parsed = JSON.parse(saved)
                setDebrief(parsed.content)
                setLastGeneratedAt(parsed.generatedAt)
            } catch (e) {
                console.error("Failed to parse saved debrief", e)
            }
        }
    }, [])

    const generateDebrief = async () => {
        setLoading(true)
        setDebrief(null)
        const { start, end } = getDates()

        const payload: any = { mode: 'generate' }
        if (start) {
            payload.startDate = start.toISOString()
            payload.endDate = end.toISOString()
        }

        try {
            const res = await fetch('/api/debrief', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            const data = await res.json()
            setDebrief(data.response || data.debrief)

            // Save to LocalStorage
            const now = new Date().toISOString()
            setLastGeneratedAt(now)
            localStorage.setItem('abuzz_weekly_debrief', JSON.stringify({
                content: data.response || data.debrief,
                generatedAt: now
            }))

        } catch (error) {
            console.error('Failed to generate debrief:', error)
            setDebrief('Error generating debrief. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // Handle printing
    const handlePrint = () => {
        window.print()
    }

    const { start, end } = getDates()

    return (
        <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
            <div className="print:hidden">
                <Suspense fallback={<div className="w-64 bg-slate-950 border-r border-slate-800 h-screen" />}>
                    <Sidebar />
                </Suspense>
            </div>

            <main className="flex-1 ml-64 p-12 print:ml-0 print:p-0">
                <div className="max-w-4xl mx-auto">
                    {/* Header */}
                    <div className="flex items-end justify-between mb-12 border-b border-slate-800 pb-6 print:border-b-2 print:border-black">
                        <div>
                            <h1 className="text-3xl font-bold text-white mb-2 print:text-black">Weekly Intelligence Debrief</h1>
                            <div className="flex items-center gap-4 text-slate-400 print:text-slate-600">
                                {/* Range Selector Removed - Weekly Only */}
                                <span className="print:block">
                                    {`${format(start!, 'MMM d')} - ${format(end, 'MMM d, yyyy')}`}
                                </span>

                                {/* Item Count Badge */}
                                {itemCount !== null && (
                                    <span className={`text-xs px-2 py-1 rounded-full border ${itemCount > 0 ? 'bg-cyan-950/30 text-cyan-400 border-cyan-900/50' : 'bg-red-950/30 text-red-400 border-red-900/50'}`}>
                                        {itemCount} signals found
                                    </span>
                                )}

                                {/* Last Generated Timestamp */}
                                {lastGeneratedAt && (
                                    <span className="text-xs text-slate-500 border-l border-slate-800 pl-4 ml-2">
                                        Generated: {format(new Date(lastGeneratedAt), 'MMM d, h:mm a')}
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="flex gap-3 print:hidden">
                            <button
                                onClick={handlePrint}
                                disabled={!debrief}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Print / Save PDF
                            </button>
                            <button
                                onClick={generateDebrief}
                                disabled={loading || itemCount === 0}
                                className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-md transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-900/20"
                            >
                                {loading ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <span>✨</span> Generate Report
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Loading State */}
                    {loading && (
                        <div className="py-20 text-center animate-pulse">
                            <div className="w-16 h-16 bg-slate-800 rounded-full mx-auto mb-6 flex items-center justify-center">
                                <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
                            </div>
                            <h2 className="text-xl font-medium text-slate-300">Analyzing Market Intelligence...</h2>
                            <p className="text-slate-500 mt-2">Processing {itemCount} news items for strategic insights.</p>
                        </div>
                    )}

                    {/* Report Content */}
                    {debrief && (
                        <div className="prose prose-invert prose-slate max-w-none print:prose-black">
                            <style jsx global>{`
                .prose h2 { color: #22d3ee; margin-top: 2em; border-bottom: 1px solid #1e293b; padding-bottom: 0.5em; }
                .prose h3 { color: #cbd5e1; margin-top: 1.5em; }
                .prose strong { color: #fff; }
                .print\\:prose-black h2 { color: #000; border-bottom-color: #ddd; }
                .print\\:prose-black strong { color: #000; }
              `}</style>
                            <ReactMarkdown>{debrief}</ReactMarkdown>
                        </div>
                    )}

                    {/* Empty State */}
                    {!debrief && !loading && (
                        <div className="py-20 text-center border-2 border-dashed border-slate-800 rounded-xl bg-slate-900/50">
                            <p className="text-slate-500">
                                {itemCount === 0
                                    ? "No new intelligence found in this period."
                                    : "Ready to generate. Click 'Generate Report' to analyze " + itemCount + " items."}
                            </p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
