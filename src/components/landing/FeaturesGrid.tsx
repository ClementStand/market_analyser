'use client'

import { motion } from 'framer-motion'
import { Brain, Activity, FileText, Shield, Globe, Zap } from 'lucide-react'

const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
}

function FeatureCard({
    icon: Icon,
    title,
    description,
    iconColor,
    iconBg,
    glowBorder,
    className = '',
}: {
    icon: React.ElementType
    title: string
    description: string
    iconColor: string
    iconBg: string
    glowBorder: string
    className?: string
}) {
    return (
        <motion.div
            variants={itemVariants}
            className={`group relative p-7 rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm transition-all duration-300 hover:shadow-2xl hover:shadow-black/20 ${glowBorder} ${className}`}
        >
            {/* Subtle gradient on hover */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

            <div className={`relative w-11 h-11 rounded-xl flex items-center justify-center ${iconBg} mb-5`}>
                <Icon className={`w-5 h-5 ${iconColor}`} />
            </div>
            <h3 className="relative text-lg font-semibold text-white mb-2">{title}</h3>
            <p className="relative text-sm text-slate-400 leading-relaxed">{description}</p>
        </motion.div>
    )
}

export default function FeaturesGrid() {
    return (
        <section id="features" className="py-24 px-6">
            <div className="max-w-5xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-100px' }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-16"
                >
                    <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                        Everything You Need to Stay Ahead
                    </h2>
                    <p className="mt-4 text-slate-400 max-w-xl mx-auto">
                        From discovery to daily monitoring, Scoper automates the entire competitive intelligence lifecycle.
                    </p>
                </motion.div>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-50px' }}
                    className="grid grid-cols-1 md:grid-cols-2 gap-4"
                >
                    {/* Row 1: Hero feature (full width) */}
                    <FeatureCard
                        icon={Brain}
                        title="AI-Powered Discovery"
                        description="Tell Scoper about your business, and it instantly identifies your real competitors — not just the obvious ones. Our AI surfaces hidden threats, emerging players, and adjacent market entrants you'd never find manually."
                        iconColor="text-blue-400"
                        iconBg="bg-blue-500/10"
                        glowBorder="hover:border-blue-500/30"
                        className="md:col-span-2"
                    />

                    {/* Row 2: Two equal cards */}
                    <FeatureCard
                        icon={Activity}
                        title="24/7 Monitoring"
                        description="Background workers continuously scan funding rounds, product launches, leadership changes, and strategic shifts — across every competitor, every day."
                        iconColor="text-violet-400"
                        iconBg="bg-violet-500/10"
                        glowBorder="hover:border-violet-500/30"
                    />
                    <FeatureCard
                        icon={FileText}
                        title="Automated Debriefs"
                        description="Executive-grade intelligence summaries without the noise. Every article is analyzed by Claude AI, scored for relevance, and categorized by impact level."
                        iconColor="text-emerald-400"
                        iconBg="bg-emerald-500/10"
                        glowBorder="hover:border-emerald-500/30"
                    />

                    {/* Row 3: Two equal cards */}
                    <FeatureCard
                        icon={Shield}
                        title="Threat Detection"
                        description="Real-time threat scoring alerts you when competitors make high-impact moves that could affect your market position. Never be caught off guard again."
                        iconColor="text-amber-400"
                        iconBg="bg-amber-500/10"
                        glowBorder="hover:border-amber-500/30"
                    />
                    <FeatureCard
                        icon={Globe}
                        title="Multi-Region Coverage"
                        description="Global intelligence across MENA, Europe, APAC, and the Americas. Native-language search surfaces news that English-only tools miss entirely."
                        iconColor="text-cyan-400"
                        iconBg="bg-cyan-500/10"
                        glowBorder="hover:border-cyan-500/30"
                    />

                    {/* Row 4: Bottom feature (full width) */}
                    <FeatureCard
                        icon={Zap}
                        title="One-Click Intelligence Refresh"
                        description="Need the latest intel on a specific competitor? Hit the search button on any competitor profile and Scoper runs a deep 2-week scan in minutes — not hours."
                        iconColor="text-rose-400"
                        iconBg="bg-rose-500/10"
                        glowBorder="hover:border-rose-500/30"
                        className="md:col-span-2"
                    />
                </motion.div>
            </div>
        </section>
    )
}
