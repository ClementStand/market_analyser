'use client'

import { useState, useEffect, Suspense } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { Sparkles, Save, X, Plus, Loader2 } from 'lucide-react'
import { APP_CONFIG } from '@/lib/config'

const AVAILABLE_REGIONS = Object.keys(APP_CONFIG.regions)

export default function SettingsPage() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [autoDetecting, setAutoDetecting] = useState(false)
    const [saved, setSaved] = useState(false)

    // Org data
    const [competitors, setCompetitors] = useState<{ id: string; name: string }[]>([])
    const [vipCompetitors, setVipCompetitors] = useState<string[]>([])
    const [priorityRegions, setPriorityRegions] = useState<string[]>([])

    // For adding custom VIP name
    const [customVip, setCustomVip] = useState('')

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/settings')
            const data = await res.json()
            setCompetitors(data.competitors || [])
            setVipCompetitors(data.vipCompetitors || [])
            setPriorityRegions(data.priorityRegions || [])
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    const handleAutoDetect = async () => {
        setAutoDetecting(true)
        try {
            const res = await fetch('/api/settings/auto-detect', { method: 'POST' })
            const data = await res.json()
            if (data.vipCompetitors) setVipCompetitors(data.vipCompetitors)
            if (data.priorityRegions) setPriorityRegions(data.priorityRegions)
        } catch (e) {
            console.error(e)
        } finally {
            setAutoDetecting(false)
        }
    }

    const handleSave = async () => {
        setSaving(true)
        setSaved(false)
        try {
            await fetch('/api/settings', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vipCompetitors, priorityRegions }),
            })
            setSaved(true)
            setTimeout(() => setSaved(false), 2000)
        } catch (e) {
            console.error(e)
        } finally {
            setSaving(false)
        }
    }

    const toggleVip = (name: string) => {
        setVipCompetitors(prev =>
            prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
        )
    }

    const removeVip = (name: string) => {
        setVipCompetitors(prev => prev.filter(n => n !== name))
    }

    const addCustomVip = () => {
        const trimmed = customVip.trim()
        if (trimmed && !vipCompetitors.includes(trimmed)) {
            setVipCompetitors(prev => [...prev, trimmed])
            setCustomVip('')
        }
    }

    const toggleRegion = (region: string) => {
        setPriorityRegions(prev =>
            prev.includes(region) ? prev.filter(r => r !== region) : [...prev, region]
        )
    }

    return (
        <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
            <Suspense fallback={<div className="w-64 bg-slate-950 border-r border-slate-800 h-screen" />}>
                <Sidebar />
            </Suspense>

            <main className="flex-1 lg:ml-64 p-4 lg:p-12">
                <div className="max-w-3xl mx-auto">
                    <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-6">
                        <div>
                            <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
                            <p className="text-slate-400">Configure scoring boosts for VIP competitors and priority regions.</p>
                        </div>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-md flex items-center gap-2 transition-colors"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            {saved ? 'Saved!' : 'Save Changes'}
                        </button>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
                        </div>
                    ) : (
                        <div className="space-y-10">
                            {/* VIP Competitors Section */}
                            <section>
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-amber-500" />
                                            VIP Competitors
                                        </h2>
                                        <p className="text-sm text-slate-500 mt-1">
                                            VIP competitors get a +20 impact score boost on all their articles.
                                        </p>
                                    </div>
                                    <button
                                        onClick={handleAutoDetect}
                                        disabled={autoDetecting}
                                        className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-md flex items-center gap-2 transition-colors disabled:opacity-50"
                                    >
                                        {autoDetecting ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                                        )}
                                        Auto-detect
                                    </button>
                                </div>

                                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 space-y-4">
                                    {/* Select from existing competitors */}
                                    <div>
                                        <label className="block text-sm text-slate-400 mb-2">Select from your competitors</label>
                                        <div className="flex flex-wrap gap-2">
                                            {competitors.map(c => (
                                                <button
                                                    key={c.id}
                                                    onClick={() => toggleVip(c.name)}
                                                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                                                        vipCompetitors.includes(c.name)
                                                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                                            : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600 hover:text-slate-300'
                                                    }`}
                                                >
                                                    {c.name}
                                                </button>
                                            ))}
                                            {competitors.length === 0 && (
                                                <span className="text-sm text-slate-600">No competitors added yet.</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Current VIP list */}
                                    {vipCompetitors.length > 0 && (
                                        <div>
                                            <label className="block text-sm text-slate-400 mb-2">Current VIP list</label>
                                            <div className="flex flex-wrap gap-2">
                                                {vipCompetitors.map(name => (
                                                    <span
                                                        key={name}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                                    >
                                                        {name}
                                                        <button
                                                            onClick={() => removeVip(name)}
                                                            className="hover:text-red-400 transition-colors"
                                                        >
                                                            <X className="w-3.5 h-3.5" />
                                                        </button>
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Add custom */}
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={customVip}
                                            onChange={e => setCustomVip(e.target.value)}
                                            onKeyDown={e => e.key === 'Enter' && addCustomVip()}
                                            placeholder="Add a competitor name not in your list..."
                                            className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 placeholder:text-slate-600"
                                        />
                                        <button
                                            onClick={addCustomVip}
                                            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded text-sm flex items-center gap-1"
                                        >
                                            <Plus className="w-3.5 h-3.5" /> Add
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* Priority Regions Section */}
                            <section>
                                <div className="mb-4">
                                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-cyan-500" />
                                        Priority Regions
                                    </h2>
                                    <p className="text-sm text-slate-500 mt-1">
                                        Articles from priority regions get a +20 impact score boost.
                                    </p>
                                </div>

                                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
                                    <div className="flex flex-wrap gap-2">
                                        {AVAILABLE_REGIONS.map(region => (
                                            <button
                                                key={region}
                                                onClick={() => toggleRegion(region)}
                                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                    priorityRegions.includes(region)
                                                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                                                        : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600 hover:text-slate-300'
                                                }`}
                                            >
                                                {region}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* Info Card */}
                            <section className="bg-slate-900/30 border border-slate-800/50 rounded-xl p-5">
                                <h3 className="text-sm font-semibold text-slate-300 mb-2">How Impact Scoring Works</h3>
                                <div className="text-sm text-slate-500 space-y-1.5">
                                    <p>Each article starts with a base score (10-50) based on its significance.</p>
                                    <p>Then bonuses are added:</p>
                                    <ul className="list-disc list-inside ml-2 space-y-1">
                                        <li>M&A, acquisitions, major funding: <span className="text-amber-400">+40</span></li>
                                        <li>Major enterprise contracts: <span className="text-amber-400">+30</span></li>
                                        <li>VIP competitor articles: <span className="text-cyan-400">+20</span></li>
                                        <li>Priority region articles: <span className="text-cyan-400">+20</span></li>
                                    </ul>
                                    <p className="text-slate-600 mt-2">Scores are capped at 100.</p>
                                </div>
                            </section>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
