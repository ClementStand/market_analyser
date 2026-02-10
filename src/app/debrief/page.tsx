'use client'
import { useState, useEffect, Suspense } from 'react'
import { format, subDays } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { Sidebar } from '@/components/Sidebar'

export default function WeeklyDebrief() {
    const [debrief, setDebrief] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [itemCount, setItemCount] = useState<number | null>(null)
    const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(null)
    const [periodStart, setPeriodStart] = useState<Date | null>(null)
    const [periodEnd, setPeriodEnd] = useState<Date | null>(null)

    // Fetch latest debrief from DB + count
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch count and latest debrief in parallel
                const [countRes, debriefRes] = await Promise.all([
                    fetch('/api/debrief', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            mode: 'count',
                            startDate: subDays(new Date(), 7).toISOString(),
                            endDate: new Date().toISOString(),
                        })
                    }),
                    fetch('/api/debrief', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: 'latest' })
                    })
                ])

                const countData = await countRes.json()
                setItemCount(countData.count)

                const debriefData = await debriefRes.json()
                if (debriefData.response) {
                    setDebrief(debriefData.response)
                    setLastGeneratedAt(debriefData.generatedAt)
                    setPeriodStart(new Date(debriefData.periodStart))
                    setPeriodEnd(new Date(debriefData.periodEnd))
                }
            } catch (e) {
                console.error('Failed to load debrief:', e)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    const handlePrint = () => {
        window.print()
    }

    const displayStart = periodStart || subDays(new Date(), 7)
    const displayEnd = periodEnd || new Date()

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
                                <span className="print:block">
                                    {`${format(displayStart, 'MMM d')} - ${format(displayEnd, 'MMM d, yyyy')}`}
                                </span>

                                {itemCount !== null && (
                                    <span className={`text-xs px-2 py-1 rounded-full border ${itemCount > 0 ? 'bg-cyan-950/30 text-cyan-400 border-cyan-900/50' : 'bg-red-950/30 text-red-400 border-red-900/50'}`}>
                                        {itemCount} signals found
                                    </span>
                                )}

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
                        </div>
                    </div>

                    {/* Loading State */}
                    {loading && (
                        <div className="py-20 text-center animate-pulse">
                            <div className="w-16 h-16 bg-slate-800 rounded-full mx-auto mb-6 flex items-center justify-center">
                                <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
                            </div>
                            <h2 className="text-xl font-medium text-slate-300">Loading Debrief...</h2>
                        </div>
                    )}

                    {/* Report Content */}
                    {debrief && !loading && (
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
                                No debrief generated yet. Run the generator script locally:
                            </p>
                            <code className="block mt-4 text-cyan-400 text-sm bg-slate-900 px-4 py-2 rounded-lg inline-block">
                                ./.venv/bin/python scripts/debrief_generator.py
                            </code>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
