'use client'

import { motion } from 'framer-motion'
import { BrainCircuit, AlertTriangle, ArrowRight, X } from 'lucide-react'

// Common animation configurations
const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.4,
            delayChildren: 0.2
        }
    }
}

const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.6, ease: "easeOut" as const }
    }
}

const scaleVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
        opacity: 1,
        scale: 1,
        transition: { type: "spring" as const, stiffness: 100, damping: 20 }
    }
}

export default function SignalVsNoise() {
    return (
        <section className="py-24 px-4 sm:px-6 relative overflow-hidden bg-slate-950">
            {/* Background elements */}
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-slate-800 to-transparent" />

            <div className="max-w-6xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-100px' }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-16"
                >
                    <h2 className="text-4xl sm:text-5xl font-bold tracking-tighter text-white mb-6">
                        From Noise to <span className="text-emerald-400">Signal</span>
                    </h2>
                    <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                        Scoper's AI engine reads through thousands of chaotic press releases, ads, and filler text to extract exactly what matters to your business.
                    </p>
                </motion.div>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-50px' }}
                    className="flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-12"
                >
                    {/* Left Side: The Noise */}
                    <motion.div variants={itemVariants} className="w-full lg:w-2/5 max-w-md">
                        <div className="bg-slate-100 rounded-xl overflow-hidden border border-slate-300 shadow-2xl relative h-[450px] flex flex-col">
                            {/* Fake Browser Chrome */}
                            <div className="bg-slate-200 border-b border-slate-300 px-4 py-3 flex items-center gap-2">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-400" />
                                    <div className="w-3 h-3 rounded-full bg-amber-400" />
                                    <div className="w-3 h-3 rounded-full bg-green-400" />
                                </div>
                                <div className="mx-auto bg-white rounded-md w-1/2 h-5 shadow-sm" />
                            </div>

                            {/* Cluttered Article Content */}
                            <div className="p-6 flex-1 flex flex-col gap-4 relative overflow-hidden bg-white">
                                {/* Fake Ad Block */}
                                <div className="w-full h-24 bg-slate-200 rounded flex items-center justify-center border border-dashed border-slate-300">
                                    <span className="text-slate-400 text-xs font-medium uppercase tracking-widest">Advertisement</span>
                                </div>

                                <div className="h-6 w-3/4 bg-slate-800 rounded" />
                                <div className="flex flex-col gap-2">
                                    {[1, 2, 3, 4, 5, 6].map(i => (
                                        <div key={i} className={`h-2.5 bg-slate-200 rounded ${i % 2 === 0 ? 'w-full' : 'w-5/6'}`} />
                                    ))}
                                </div>
                                <div className="h-32 w-full bg-slate-100 rounded-lg mt-2" />

                                {/* Cookie Banner Overlay */}
                                <div className="absolute bottom-4 left-4 right-4 bg-slate-900 text-white p-4 rounded-lg shadow-2xl flex flex-col gap-3">
                                    <div className="flex justify-between items-start">
                                        <p className="text-xs font-semibold">We value your privacy</p>
                                        <X className="w-4 h-4 text-slate-400" />
                                    </div>
                                    <p className="text-[10px] text-slate-300">We and our partners use cookies to store and/or access info...</p>
                                    <div className="flex gap-2">
                                        <div className="flex-1 h-6 bg-slate-700 rounded" />
                                        <div className="flex-1 h-6 bg-blue-500 rounded" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Middle: The Engine */}
                    <motion.div variants={itemVariants} className="flex flex-col items-center justify-center py-8 lg:py-0 z-10">
                        <div className="relative group">
                            {/* Glowing connector line (Desktop) */}
                            <div className="hidden lg:block absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 w-64 h-0.5 bg-gradient-to-r from-transparent via-blue-500/50 to-transparent blur-sm" />
                            <div className="hidden lg:block absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 w-48 h-px bg-gradient-to-r from-transparent via-blue-400 to-transparent" />

                            <motion.div
                                className="relative bg-slate-900 border border-slate-700 p-4 rounded-full shadow-[0_0_30px_rgba(59,130,246,0.2)] flex items-center justify-center z-10"
                                animate={{
                                    boxShadow: ["0 0 20px rgba(59,130,246,0.2)", "0 0 40px rgba(59,130,246,0.4)", "0 0 20px rgba(59,130,246,0.2)"],
                                    borderColor: ["rgba(51,65,85,1)", "rgba(59,130,246,0.5)", "rgba(51,65,85,1)"]
                                }}
                                transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
                            >
                                <BrainCircuit className="w-8 h-8 text-blue-400" />
                            </motion.div>
                        </div>
                        <div className="mt-4 flex flex-col items-center gap-1">
                            <span className="text-xs font-mono font-medium text-blue-400 tracking-wider">CLAUDE AI</span>
                            <span className="text-[10px] text-slate-500 uppercase tracking-widest">Processing</span>
                        </div>
                        <ArrowRight className="w-5 h-5 text-slate-600 mt-2 lg:hidden animate-bounce" />
                    </motion.div>

                    {/* Right Side: The Signal */}
                    <motion.div variants={scaleVariants} className="w-full lg:w-2/5 max-w-md">
                        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl relative h-[450px] flex flex-col justify-center">

                            {/* Exact Scoper Intelligence Card Replica */}
                            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-5 shadow-lg group hover:border-slate-700 transition-colors relative overflow-hidden">
                                {/* Top Header Row */}
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                                            <span className="text-indigo-400 font-bold text-sm">C</span>
                                        </div>
                                        <span className="font-semibold text-slate-200 text-sm">Competitor X</span>
                                        <span className="text-slate-600 px-1">•</span>
                                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]">
                                            Partnership
                                        </span>
                                    </div>
                                    <span className="text-xs text-slate-500 font-mono">Today</span>
                                </div>

                                <h3 className="text-lg font-bold text-white mb-3">
                                    Strategic Partnership Announced with Global Lead
                                </h3>

                                <div className="space-y-2 mb-6">
                                    <div className="flex gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-slate-600 mt-1.5 shrink-0" />
                                        <p className="text-sm text-slate-300 leading-relaxed">
                                            Competitor X signed a multi-year partnership to completely integrate their new AI-driven analytics suite.
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-slate-600 mt-1.5 shrink-0" />
                                        <p className="text-sm text-slate-300 leading-relaxed">
                                            This directly positions them to heavily contest our market share in the enterprise segment next quarter.
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between pt-4 border-t border-slate-800/60">
                                    <div className="flex gap-2">
                                        <span className="px-2 py-1 rounded bg-slate-800 text-[10px] text-slate-400 font-medium">Enterprise Data</span>
                                        <span className="px-2 py-1 rounded bg-slate-800 text-[10px] text-slate-400 font-medium">Analytics</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/20">
                                        <AlertTriangle className="w-3 h-3 text-rose-500" />
                                        <span className="text-[10px] font-medium text-rose-500 uppercase tracking-wider">Threat Level: High</span>
                                    </div>
                                </div>
                            </div>

                            {/* Subtle underlying glow */}
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-emerald-500/5 blur-[100px] -z-10 rounded-full pointer-events-none" />
                        </div>
                    </motion.div>
                </motion.div>
            </div>
        </section>
    )
}
