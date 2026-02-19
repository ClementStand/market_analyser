'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Loader2, Building2, Search, Check, Globe } from "lucide-react"
import { createClient } from '@/utils/supabase/client'

type Step = 'business' | 'competitors' | 'processing'

interface CompetitorRecommendation {
    name: string
    website: string
    reason: string
}

interface FetchJobStatus {
    status: string
    currentStep: string | null
    processed: number
    total: number
    error: string | null
}

export default function OnboardingPage() {
    const router = useRouter()
    const [step, setStep] = useState<Step>('business')
    const [loading, setLoading] = useState(false)

    // Business Info
    const [orgName, setOrgName] = useState('')
    const [website, setWebsite] = useState('')
    const [industry, setIndustry] = useState('')
    const [regions, setRegions] = useState<string[]>([])
    const [keywords, setKeywords] = useState('')

    // Competitors
    const [recommendations, setRecommendations] = useState<CompetitorRecommendation[]>([])
    const [selectedCompetitors, setSelectedCompetitors] = useState<CompetitorRecommendation[]>([])

    // Manual Entry
    const [manualName, setManualName] = useState('')
    const [manualWebsite, setManualWebsite] = useState('')

    // Processing status
    const [jobStatus, setJobStatus] = useState<FetchJobStatus | null>(null)
    const [jobId, setJobId] = useState<string | null>(null)
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

    const AVAILABLE_REGIONS = [
        "Global",
        "North America",
        "Europe",
        "MENA",
        "APAC",
        "South America"
    ]

    // Poll for job status when in processing step
    useEffect(() => {
        if (step !== 'processing' || !jobId) return

        const supabase = createClient()

        // Subscribe to Realtime changes on FetchJob
        const channel = supabase
            .channel(`fetch-job-${jobId}`)
            .on(
                'postgres_changes',
                {
                    event: 'UPDATE',
                    schema: 'public',
                    table: 'FetchJob',
                    filter: `id=eq.${jobId}`
                },
                (payload) => {
                    const newData = payload.new as any
                    setJobStatus({
                        status: newData.status,
                        currentStep: newData.currentStep,
                        processed: newData.processed,
                        total: newData.total,
                        error: newData.error,
                    })

                    if (newData.status === 'completed') {
                        setTimeout(() => {
                            router.push('/')
                            router.refresh()
                        }, 2000)
                    }
                }
            )
            .subscribe()

        // Also poll as fallback (in case Realtime isn't enabled on FetchJob table)
        const poll = async () => {
            try {
                const res = await fetch(`/api/fetch-status?jobId=${jobId}`)
                if (res.ok) {
                    const data = await res.json()
                    setJobStatus({
                        status: data.status,
                        currentStep: data.currentStep,
                        processed: data.processed,
                        total: data.total,
                        error: data.error,
                    })

                    if (data.status === 'completed') {
                        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                        setTimeout(() => {
                            router.push('/')
                            router.refresh()
                        }, 2000)
                    }
                    if (data.status === 'error') {
                        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                    }
                }
            } catch { /* ignore */ }
        }

        pollIntervalRef.current = setInterval(poll, 5000)
        poll() // Initial poll

        return () => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
            supabase.removeChannel(channel)
        }
    }, [step, jobId, router])

    const toggleRegion = (region: string) => {
        if (regions.includes(region)) {
            setRegions(prev => prev.filter(r => r !== region))
        } else {
            setRegions(prev => [...prev, region])
        }
    }

    const fetchRecommendations = async (isLoadMore = false) => {
        setLoading(true)
        try {
            const res = await fetch('/api/onboarding/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    website,
                    industry,
                    orgName,
                    regions,
                    keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
                    existingCompetitors: isLoadMore ? [...selectedCompetitors, ...recommendations] : []
                })
            })

            if (!res.ok) throw new Error('Failed to fetch recommendations')

            const data = await res.json()

            if (isLoadMore) {
                const newRecs = data.recommendations.filter((rec: any) =>
                    !recommendations.some(r => r.name === rec.name) &&
                    !selectedCompetitors.some(c => c.name === rec.name)
                )
                setRecommendations(prev => [...prev, ...newRecs])
            } else {
                setRecommendations(data.recommendations)
                setStep('competitors')
            }
        } catch (error) {
            console.error(error)
            if (!isLoadMore) {
                setRecommendations([
                    { name: "Competitor A", website: "https://example.com/a", reason: "Similar industry" },
                    { name: "Competitor B", website: "https://example.com/b", reason: "Key player" },
                    { name: "Competitor C", website: "https://example.com/c", reason: "Direct rival" },
                ])
                setStep('competitors')
            }
        } finally {
            setLoading(false)
        }
    }

    const handleBusinessSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        await fetchRecommendations(false)
    }

    const handleComplete = async () => {
        setLoading(true)
        setStep('processing')

        try {
            // 1. Create Organization & Initial Competitor Records
            const res = await fetch('/api/onboarding/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    orgName,
                    website,
                    industry,
                    regions,
                    keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
                    competitors: selectedCompetitors
                })
            })

            if (res.status === 401) {
                alert("Session expired. Please log in again.")
                router.push('/login')
                return
            }

            const data = await res.json()

            if (!res.ok) {
                throw new Error(data.error || 'Failed to complete onboarding')
            }

            // 2. Trigger Enrichment & Historical Scan
            const processRes = await fetch('/api/onboarding/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    orgId: data.orgId,
                })
            })

            if (processRes.ok) {
                const processData = await processRes.json()
                if (processData.jobId) {
                    setJobId(processData.jobId)
                }
            } else {
                // Process failed but org is created — redirect anyway
                console.error("Enrichment process failed, redirecting anyway")
                setTimeout(() => {
                    router.push('/')
                    router.refresh()
                }, 3000)
            }
        } catch (error: any) {
            console.error(error)
            alert(`Error: ${error.message}`)
            setStep('competitors')
        } finally {
            setLoading(false)
        }
    }

    const toggleCompetitor = (comp: CompetitorRecommendation) => {
        if (selectedCompetitors.find(c => c.name === comp.name)) {
            setSelectedCompetitors(prev => prev.filter(c => c.name !== comp.name))
        } else {
            if (selectedCompetitors.length >= 5) return
            setSelectedCompetitors(prev => [...prev, comp])
        }
    }

    const isValidUrl = (url: string) => {
        try {
            new URL(url)
            return url.includes('.')
        } catch {
            return false
        }
    }

    const addManualCompetitor = () => {
        if (!manualName || !manualWebsite) return

        if (!isValidUrl(manualWebsite) && !isValidUrl(`https://${manualWebsite}`)) {
            alert("Please enter a valid website URL (e.g. https://example.com)")
            return
        }

        let validUrl = manualWebsite
        if (!manualWebsite.startsWith('http')) {
            validUrl = `https://${manualWebsite}`
        }

        const newComp = { name: manualName, website: validUrl, reason: 'Manually added' }
        setRecommendations(prev => [newComp, ...prev])
        toggleCompetitor(newComp)
        setManualName('')
        setManualWebsite('')
    }

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-2xl">
                {/* Progress Steps */}
                <div className="flex justify-between mb-8 max-w-xs mx-auto">
                    <div className={`flex flex-col items-center gap-2 ${step === 'business' ? 'text-cyan-400' : 'text-slate-500'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${step === 'business' || step === 'competitors' || step === 'processing' ? 'border-cyan-400 bg-cyan-950 text-cyan-400' : 'border-slate-700'}`}>1</div>
                        <span className="text-xs font-medium">Business</span>
                    </div>
                    <div className={`h-0.5 flex-1 mx-4 my-4 bg-slate-800 ${(step === 'competitors' || step === 'processing') && 'bg-cyan-900'}`} />
                    <div className={`flex flex-col items-center gap-2 ${step === 'competitors' ? 'text-cyan-400' : 'text-slate-500'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${step === 'competitors' || step === 'processing' ? 'border-cyan-400 bg-cyan-950 text-cyan-400' : 'border-slate-700'}`}>2</div>
                        <span className="text-xs font-medium">Competitors</span>
                    </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">

                    {step === 'business' && (
                        <div className="animate-in fade-in slide-in-from-bottom-4">
                            <h1 className="text-2xl font-bold text-white mb-2 text-center">Tell us about your business</h1>
                            <p className="text-slate-400 text-center mb-8">We&apos;ll use this to find relevant competitors in your market.</p>

                            <form onSubmit={handleBusinessSubmit} className="space-y-6">
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2"><Building2 className="w-4 h-4" /> Company Name</Label>
                                    <input
                                        required
                                        value={orgName}
                                        onChange={e => setOrgName(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                                        placeholder="e.g. Acme Inc."
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2"><Globe className="w-4 h-4" /> Website URL</Label>
                                    <input
                                        type="url"
                                        required
                                        value={website}
                                        onChange={e => setWebsite(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                                        placeholder="https://acme.com"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2"><Search className="w-4 h-4" /> Industry / Core Focus</Label>
                                    <input
                                        required
                                        value={industry}
                                        onChange={e => setIndustry(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                                        placeholder="e.g. Fintech, E-commerce, SaaS..."
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2"><Globe className="w-4 h-4" /> Target Regions</Label>
                                    <div className="flex flex-wrap gap-2">
                                        {AVAILABLE_REGIONS.map(r => {
                                            const isSelected = regions.includes(r)
                                            return (
                                                <button
                                                    key={r}
                                                    type="button"
                                                    onClick={() => toggleRegion(r)}
                                                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${isSelected
                                                        ? 'bg-cyan-600 border-cyan-500 text-white'
                                                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'}`}
                                                >
                                                    {r}
                                                </button>
                                            )
                                        })}
                                    </div>
                                    {regions.length === 0 && <p className="text-xs text-amber-500">Please select at least one region.</p>}
                                </div>

                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2"><Search className="w-4 h-4" /> Focus Keywords (Optional)</Label>
                                    <input
                                        value={keywords}
                                        onChange={e => setKeywords(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                                        placeholder="e.g. payments, blockchain, mobile app (comma separated)"
                                    />
                                </div>

                                <Button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-500 h-12 text-lg" disabled={loading || regions.length === 0}>
                                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Next: Find Competitors"}
                                </Button>
                            </form>
                        </div>
                    )}

                    {step === 'competitors' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                            <h1 className="text-2xl font-bold text-white mb-2 text-center">Select your competitors</h1>
                            <p className="text-slate-400 text-center mb-6">Choose up to 5 recommended competitors to track.</p>

                            {/* Manual Entry */}
                            <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 mb-6">
                                <h3 className="text-sm font-medium text-slate-300 mb-3">Add a Competitor Manually</h3>
                                <div className="flex gap-2">
                                    <input
                                        placeholder="Name"
                                        className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white"
                                        value={manualName}
                                        onChange={e => setManualName(e.target.value)}
                                    />
                                    <input
                                        placeholder="Website"
                                        className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white"
                                        value={manualWebsite}
                                        onChange={e => setManualWebsite(e.target.value)}
                                    />
                                    <Button
                                        size="sm"
                                        disabled={!manualName || !manualWebsite || selectedCompetitors.length >= 5}
                                        onClick={addManualCompetitor}
                                        className="bg-cyan-600 hover:bg-cyan-500"
                                    >
                                        Add
                                    </Button>
                                </div>
                            </div>

                            <div className="space-y-3 mb-8 max-h-[400px] overflow-y-auto pr-2">
                                {recommendations.map((rec, i) => {
                                    const isSelected = selectedCompetitors.some(c => c.name === rec.name)
                                    return (
                                        <div
                                            key={i}
                                            onClick={() => toggleCompetitor(rec)}
                                            className={`p-4 rounded-lg border cursor-pointer transition-all ${isSelected ? 'bg-cyan-950/40 border-cyan-500/50' : 'bg-slate-950 border-slate-800 hover:border-slate-700'}`}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <h3 className={`font-semibold ${isSelected ? 'text-cyan-400' : 'text-slate-200'}`}>{rec.name}</h3>
                                                    <p className="text-xs text-slate-500 mt-1">{rec.website}</p>
                                                    <p className="text-sm text-slate-400 mt-2">{rec.reason}</p>
                                                </div>
                                                <div className={`w-6 h-6 rounded border flex items-center justify-center ${isSelected ? 'bg-cyan-600 border-cyan-600' : 'border-slate-600'}`}>
                                                    {isSelected && <Check className="w-4 h-4 text-white" />}
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                            <div className="text-center mb-6">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => fetchRecommendations(true)}
                                    disabled={loading}
                                    className="text-cyan-400 border-cyan-900 hover:bg-cyan-950"
                                >
                                    {loading ? <Loader2 className="w-3 h-3 animate-spin mr-2" /> : null}
                                    Load More AI Suggestions
                                </Button>
                            </div>

                            <div className="flex items-center justify-between border-t border-slate-800 pt-6">
                                <span className="text-sm text-slate-500">
                                    {selectedCompetitors.length} / 5 selected
                                </span>
                                <div className="flex gap-3">
                                    <Button variant="ghost" onClick={() => setStep('business')}>Back</Button>
                                    <Button
                                        onClick={handleComplete}
                                        className="bg-cyan-600 hover:bg-cyan-500 px-8"
                                        disabled={selectedCompetitors.length === 0 || loading}
                                    >
                                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Start Tracking"}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 'processing' && (
                        <div className="py-12 text-center animate-in fade-in zoom-in">
                            <Loader2 className="w-16 h-16 text-cyan-500 animate-spin mx-auto mb-6" />
                            <h2 className="text-2xl font-bold text-white mb-2">
                                {jobStatus?.status === 'completed' ? 'Analysis Complete!' : 'Analyzing Competitors...'}
                            </h2>

                            {jobStatus && jobStatus.status === 'running' && (
                                <div className="mt-4 space-y-3">
                                    {jobStatus.currentStep && (
                                        <p className="text-cyan-400 text-sm">
                                            Currently processing: {jobStatus.currentStep}
                                        </p>
                                    )}
                                    <div className="w-full max-w-xs mx-auto bg-slate-800 rounded-full h-2">
                                        <div
                                            className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                                            style={{ width: `${jobStatus.total > 0 ? (jobStatus.processed / jobStatus.total) * 100 : 0}%` }}
                                        />
                                    </div>
                                    <p className="text-slate-400 text-sm">
                                        {jobStatus.processed} / {jobStatus.total} competitors
                                    </p>
                                </div>
                            )}

                            {jobStatus?.status === 'completed' && (
                                <p className="text-green-400 mt-4">Redirecting to your dashboard...</p>
                            )}

                            {jobStatus?.status === 'error' && (
                                <div className="mt-4">
                                    <p className="text-red-400">Something went wrong: {jobStatus.error}</p>
                                    <Button
                                        onClick={() => { router.push('/'); router.refresh() }}
                                        className="mt-4 bg-cyan-600 hover:bg-cyan-500"
                                    >
                                        Go to Dashboard
                                    </Button>
                                </div>
                            )}

                            {!jobStatus && (
                                <div className="mt-4">
                                    <p className="text-slate-400">Fetching revenue, employee data, and scanning historical news (2025-Present).</p>
                                    <p className="text-xs text-slate-500 mt-4">This may take a few minutes.</p>
                                </div>
                            )}

                            {jobStatus?.status !== 'completed' && jobStatus?.status !== 'error' && (
                                <p className="text-xs text-slate-500 mt-4">
                                    You'll receive an email when the analysis is complete. Feel free to close this page.
                                </p>
                            )}
                        </div>
                    )}

                </div>
            </div>
        </div>
    )
}
