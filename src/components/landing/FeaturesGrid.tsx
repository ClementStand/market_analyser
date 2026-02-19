'use client'

import { motion } from 'framer-motion'
import { Brain, Zap, Globe, Shield, Sparkles, Search, Activity } from 'lucide-react'
import { useEffect, useState } from 'react'

const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1,
            delayChildren: 0.2
        }
    },
}

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
}

// -- Visual Components for Bento Cards --

const DiscoveryVisual = () => {
    return (
        <div className="flex flex-col w-full h-full justify-center items-center p-6 relative overflow-hidden">
            {/* Search Interface */}
            <motion.div
                initial={{ width: "60%" }}
                whileHover={{ width: "70%" }}
                className="w-full max-w-sm bg-slate-800/50 border border-slate-700 rounded-lg p-3 flex items-center gap-3 shadow-lg backdrop-blur-sm z-10"
            >
                <Search className="w-4 h-4 text-blue-400" />
                <div className="h-2 w-24 bg-slate-700 rounded animate-pulse" />
            </motion.div>

            {/* Floating results (absolute) */}
            <motion.div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-8 w-64 space-y-2 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
            >
                {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-3 p-2 rounded bg-slate-800/80 border border-slate-700/50 backdrop-blur-md translate-x-4 group-hover:translate-x-0 transition-transform duration-500" style={{ transitionDelay: `${i * 100}ms` }}>
                        <div className="w-6 h-6 rounded-full bg-slate-700" />
                        <div className="h-2 w-20 bg-slate-600 rounded" />
                    </div>
                ))}
            </motion.div>

            {/* Background Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />
        </div>
    )
}

const CategorizationVisual = () => {
    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-6 relative">
            {/* Mock Article */}
            <div className="w-full bg-slate-900/50 border border-slate-800 rounded-lg p-4 space-y-3 relative overflow-hidden group-hover:border-slate-700 transition-colors">
                <div className="h-2 w-3/4 bg-slate-700 rounded" />
                <div className="h-2 w-1/2 bg-slate-800 rounded" />

                {/* Categorization Pills */}
                <div className="flex gap-2 pt-2">
                    <motion.span
                        whileHover={{ scale: 1.05 }}
                        className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20"
                    >
                        Leadership Change
                    </motion.span>
                    <motion.span
                        whileHover={{ scale: 1.05 }}
                        className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                    >
                        Merger
                    </motion.span>
                </div>
            </div>
        </div>
    )
}

const MonitoringVisual = () => {
    return (
        <div className="w-full h-full flex items-center justify-center relative p-6">
            <div className="relative w-32 h-32 flex items-center justify-center">
                {/* Outer Ring */}
                <div className="absolute inset-0 border-2 border-dashed border-slate-800 rounded-full animate-[spin_10s_linear_infinite]" />

                {/* Pulse Ring */}
                <div className="absolute inset-2 border border-emerald-500/20 rounded-full" />

                {/* Active Indicator */}
                <div className="flex flex-col items-center gap-2">
                    <div className="relative">
                        <div className="w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.4)]" />
                        <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-75" />
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400">SYSTEM ACTIVE</span>
                </div>
            </div>
        </div>
    )
}

const DebriefVisual = () => {
    const [typedText, setTypedText] = useState('')
    const fullText = "## Weekly Summary\n- Competitor X launched AI tool\n- CEO resigned on Tuesday..."

    useEffect(() => {
        let i = 0
        const interval = setInterval(() => {
            setTypedText(fullText.slice(0, i))
            i++
            if (i > fullText.length) i = 0
        }, 50)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="w-full h-full bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-400 relative overflow-hidden group-hover:border-slate-700 transition-colors">
            <div className="absolute top-2 right-2">
                <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
            </div>
            <div className="whitespace-pre-wrap">{typedText}</div>
            <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-slate-950 to-transparent" />
        </div>
    )
}


// -- Main Card Component --

function BentoCard({
    title,
    description,
    className = "",
    children,
    colSpan = 1
}: {
    title: string
    description: string
    className?: string
    children?: React.ReactNode
    colSpan?: 1 | 2 | 3
}) {
    return (
        <motion.div
            variants={itemVariants}
            className={`group relative flex flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/50 backdrop-blur-sm hover:bg-slate-900/80 transition-colors duration-300 ${colSpan === 2 ? 'md:col-span-2' : colSpan === 3 ? 'md:col-span-3' : 'md:col-span-1'
                } ${className}`}
        >
            {/* Visual Area */}
            <div className="relative h-48 sm:h-64 w-full overflow-hidden border-b border-slate-800/50 bg-slate-900/20 group-hover:bg-slate-900/40 transition-colors">
                {children}
            </div>

            {/* Text Content */}
            <div className="p-6 flex flex-col justify-end flex-1">
                <h3 className="text-lg font-semibold text-slate-100 mb-2 group-hover:text-white transition-colors">
                    {title}
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">
                    {description}
                </p>
            </div>
        </motion.div>
    )
}


// -- Main Grid --

export default function FeaturesGrid() {
    return (
        <section id="features" className="py-24 px-4 sm:px-6">
            <div className="max-w-6xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-100px' }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-16"
                >
                    <h2 className="text-center text-4xl sm:text-5xl font-bold tracking-tighter text-white mb-6">
                        Intelligence, Automated.
                    </h2>
                    <p className="text-xl text-center text-slate-400 max-w-2xl mx-auto">
                        We built the intelligence layer for your business so you can focus on strategy, not searching.
                    </p>
                </motion.div>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-50px' }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6"
                >
                    {/* 1. Large: AI Discovery */}
                    <BentoCard
                        title="AI-Powered Discovery"
                        description="Tell Scoper about your business, and it automatically identifies hidden competitors and market entrants you'd miss manually."
                        colSpan={2}
                    >
                        <DiscoveryVisual />
                    </BentoCard>

                    {/* 2. Small: Monitoring */}
                    <BentoCard
                        title="24/7 Monitoring"
                        description="Continuous background scanning of funding rounds, product launches, and strategic shifts."
                        colSpan={1}
                    >
                        <MonitoringVisual />
                    </BentoCard>

                    {/* 3. Small: Categorization (New!) */}
                    <BentoCard
                        title="Smart News Categorization"
                        description="AI automatically tags news into categories like Mergers, Leadership Changes, and Product Launches to cut through the noise."
                        colSpan={1}
                    >
                        <CategorizationVisual />
                    </BentoCard>

                    {/* 4. Large: Automated Debriefs */}
                    <BentoCard
                        title="Automated Debriefs"
                        description="Executive-grade summaries generated by Claude AI. Get the signal without the noise, delivered directly to your inbox or dashboard."
                        colSpan={2}
                    >
                        <div className="w-full h-full p-6 flex items-center justify-center bg-slate-900/30">
                            <DebriefVisual />
                        </div>
                    </BentoCard>

                </motion.div>
            </div>
        </section>
    )
}
