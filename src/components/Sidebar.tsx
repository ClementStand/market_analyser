'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Checkbox } from "@/components/ui/checkbox"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { RefreshButton } from "@/components/ui/RefreshButton"
import { CompetitorLogo } from "@/components/ui/CompetitorLogo"
import { Loader2, LayoutDashboard, FileText, Settings, Menu, X, LogOut, User, Users } from "lucide-react"
import { createClient } from '@/utils/supabase/client'
import { matchesRegion, APP_CONFIG } from "@/lib/config"

interface SidebarProps {
    orgName?: string
}

export function Sidebar({ orgName }: SidebarProps) {
    const router = useRouter()
    const searchParams = useSearchParams()

    // Mobile menu state
    const [mobileOpen, setMobileOpen] = useState(false)

    // State
    const [competitors, setCompetitors] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    // Filters - Initialize from correct URL params
    const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(searchParams.get('competitorId'))
    const [minThreat, setMinThreat] = useState([parseInt(searchParams.get('minThreat') || '1')])
    const [unreadOnly, setUnreadOnly] = useState(searchParams.get('unread') === 'true')
    const [starredOnly, setStarredOnly] = useState(searchParams.get('starred') === 'true')
    const [selectedRegion, setSelectedRegion] = useState<string | null>(searchParams.get('region'))

    // Derived regions list
    const regions = Array.from(new Set(competitors.map(c => c.region).filter(Boolean))).sort()

    // Sync state with URL params
    useEffect(() => {
        // Only update state if it differs from URL to avoid loop
        const currentCompetitorId = searchParams.get('competitorId')
        if (currentCompetitorId !== selectedCompetitor) setSelectedCompetitor(currentCompetitorId)

        const currentThreat = parseInt(searchParams.get('minThreat') || '1')
        if (currentThreat !== minThreat[0]) setMinThreat([currentThreat])

        const currentRegion = searchParams.get('region')
        if (currentRegion !== selectedRegion) setSelectedRegion(currentRegion)

        const currentUnread = searchParams.get('unread') === 'true'
        if (currentUnread !== unreadOnly) setUnreadOnly(currentUnread)

        const currentStarred = searchParams.get('starred') === 'true'
        if (currentStarred !== starredOnly) setStarredOnly(currentStarred)

    }, [searchParams])

    useEffect(() => {
        const fetchCompetitors = async () => {
            try {
                const res = await fetch('/api/competitors')
                const data = await res.json()
                setCompetitors(data)
            } catch (e) {
                console.error(e)
            } finally {
                setLoading(false)
            }
        }
        fetchCompetitors()
    }, [])

    const applyFilters = () => {
        const params = new URLSearchParams(searchParams.toString())

        if (selectedCompetitor) params.set('competitorId', selectedCompetitor)
        else params.delete('competitorId')

        if (selectedRegion) params.set('region', selectedRegion)
        else params.delete('region')

        /* if (minThreat[0] > 1) params.set('minThreat', minThreat[0].toString())
        else params.delete('minThreat') */

        if (unreadOnly) params.set('unread', 'true')
        else params.delete('unread')

        if (starredOnly) params.set('starred', 'true')
        else params.delete('starred')

        // Only push if params changed
        if (params.toString() !== searchParams.toString()) {
            router.push(`/?${params.toString()}`)
        }
    }

    // Auto-apply on toggle changes
    useEffect(() => {
        // Debounce or just check logic?
        // We need to avoid triggering this immediately after the URL sync
        // But since we have the check inside applyFilters, it should be safe
        applyFilters()
    }, [selectedCompetitor, selectedRegion, minThreat, unreadOnly, starredOnly])

    // User profile
    const [userEmail, setUserEmail] = useState<string | null>(null)

    useEffect(() => {
        const fetchUser = async () => {
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()
            setUserEmail(user?.email ?? null)
        }
        fetchUser()
    }, [])

    const handleLogout = async () => {
        const supabase = createClient()
        await supabase.auth.signOut()
        router.push('/')
        router.refresh()
    }

    // Local search state
    const [searchTerm, setSearchTerm] = useState('')

    // Filtered competitors
    const filteredCompetitors = competitors.filter(c => {
        const matchSearch = c.name.toLowerCase().includes(searchTerm.toLowerCase())

        let regionMatch = true
        if (selectedRegion) {
            regionMatch = matchesRegion(c.region || '', selectedRegion)
        }

        return matchSearch && regionMatch
    })

    return (
        <>
            {/* Mobile hamburger button */}
            <button
                onClick={() => setMobileOpen(!mobileOpen)}
                className="lg:hidden fixed top-4 left-4 z-[60] p-2 bg-slate-900 border border-slate-700 rounded-md text-slate-300 hover:text-white"
            >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Overlay for mobile */}
            {mobileOpen && (
                <div
                    className="lg:hidden fixed inset-0 bg-black/60 z-40"
                    onClick={() => setMobileOpen(false)}
                />
            )}

            <div className={`w-64 bg-slate-950/80 backdrop-blur-xl border-r border-slate-800 h-screen p-4 flex flex-col fixed left-0 top-0 overflow-y-auto z-50 transition-transform duration-300 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>

                <div className="mb-8 px-2 pt-2">
                    <h1 className="font-bold text-xl tracking-tight text-white">
                        {orgName || process.env.NEXT_PUBLIC_APP_NAME || 'Market Analyser'}
                    </h1>
                </div>

                <div className="space-y-6 flex-1">
                    {/* Toggles */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="unread" className="text-sm font-medium text-slate-300">Unread Only</Label>
                            <Switch id="unread" checked={unreadOnly} onCheckedChange={setUnreadOnly} className="data-[state=checked]:bg-cyan-500" />
                        </div>
                        <div className="flex items-center justify-between">
                            <Label htmlFor="starred" className="text-sm font-medium text-slate-300">Starred Only</Label>
                            <Switch id="starred" checked={starredOnly} onCheckedChange={setStarredOnly} className="data-[state=checked]:bg-cyan-500" />
                        </div>
                    </div>

                    {/* Region Filter (Cleaned) */}
                    <div className="space-y-2">
                        <Label className="text-slate-300">Region</Label>
                        <select
                            className="w-full bg-slate-900 border border-slate-800 text-slate-200 text-sm rounded-md px-3 py-2 focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                            value={selectedRegion || ''}
                            onChange={(e) => setSelectedRegion(e.target.value || null)}
                        >
                            <option value="">All Regions</option>
                            {Object.keys(APP_CONFIG.regions).map(r => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </div>

                    {/* Competitors List */}
                    <div className="space-y-3">
                        <Link href="/" className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-cyan-400 hover:bg-slate-900/50 rounded-lg transition-colors group">
                            <LayoutDashboard className="w-4 h-4 text-slate-500 group-hover:text-cyan-400" />
                            Dashboard
                        </Link>
                        <Link href="/debrief" className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-cyan-400 hover:bg-slate-900/50 rounded-lg transition-colors group">
                            <FileText className="w-4 h-4 text-slate-500 group-hover:text-cyan-400" />
                            Weekly Debrief
                        </Link>
                        <Link href="/competitors" className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-cyan-400 hover:bg-slate-900/50 rounded-lg transition-colors group">
                            <Users className="w-4 h-4 text-slate-500 group-hover:text-cyan-400" />
                            Manage Competitors
                        </Link>
                        <Link href="/settings" className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-cyan-400 hover:bg-slate-900/50 rounded-lg transition-colors group">
                            <Settings className="w-4 h-4 text-slate-500 group-hover:text-cyan-400" />
                            Settings
                        </Link>
                        {/* Search Input */}
                        <input
                            type="text"
                            placeholder="Filter competitors..."
                            className="w-full text-sm px-3 py-2 rounded-md bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500 placeholder:text-slate-600"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />

                        <div className="space-y-1">
                            <button
                                onClick={() => setSelectedCompetitor(null)}
                                className={`w-full text-left px-2 py-1.5 rounded-md text-sm transition-all duration-200 ${!selectedCompetitor ? 'bg-cyan-950/30 text-cyan-400 font-medium border border-cyan-900/50' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}`}
                            >
                                All Competitors
                            </button>
                            {loading ? (
                                <Loader2 className="h-4 w-4 animate-spin mx-auto text-slate-600 mt-4" />
                            ) : (
                                filteredCompetitors.map(comp => {
                                    return (
                                        <button
                                            key={comp.id}
                                            onClick={() => setSelectedCompetitor(comp.id === selectedCompetitor ? null : comp.id)}
                                            className={`w-full text-left px-2 py-2 rounded-md text-sm flex items-center justify-between group transition-all duration-200 ${selectedCompetitor === comp.id ? 'bg-cyan-950/30 text-cyan-400 font-medium border border-cyan-900/50' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}`}
                                        >
                                            <div className="flex items-center gap-2 overflow-hidden flex-1">
                                                <CompetitorLogo
                                                    name={comp.name}
                                                    website={comp.website}
                                                    className="w-5 h-5 rounded-full flex-shrink-0 text-[10px] bg-slate-900 border-slate-800"
                                                />
                                                <Link
                                                    href={`/competitor/${comp.id}`}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="truncate hover:underline hover:text-cyan-400 transition-colors"
                                                    title="View Dossier"
                                                >
                                                    {comp.name}
                                                </Link>
                                            </div>
                                            <span className={`text-xs px-1.5 py-0.5 rounded-full ${selectedCompetitor === comp.id ? 'bg-cyan-900/50 text-cyan-300' : 'bg-slate-900 text-slate-600 group-hover:bg-slate-800 group-hover:text-slate-400'}`}>
                                                {comp.newsCount}
                                            </span>
                                        </button>
                                    )
                                })
                            )}
                        </div>
                    </div>
                </div>

                <div className="mt-auto pt-4 border-t border-slate-800 space-y-3">
                    {userEmail && (
                        <div className="flex items-center justify-between px-2 py-2 rounded-lg">
                            <div className="flex items-center gap-2 overflow-hidden">
                                <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-900 flex items-center justify-center flex-shrink-0">
                                    <User className="w-3.5 h-3.5 text-cyan-400" />
                                </div>
                                <span className="text-xs text-slate-400 truncate" title={userEmail}>
                                    {userEmail}
                                </span>
                            </div>
                            <button
                                onClick={handleLogout}
                                title="Sign out"
                                className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-950/30 rounded-md transition-colors flex-shrink-0"
                            >
                                <LogOut className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    )}
                    <RefreshButton />
                </div>
            </div>
        </>
    )
}
