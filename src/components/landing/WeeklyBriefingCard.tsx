'use client'

import { motion } from 'framer-motion'

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
}

export default function WeeklyBriefingCard() {
    return (
        <motion.div
            variants={itemVariants}
            className="group relative flex flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/50 backdrop-blur-sm hover:bg-slate-900/80 transition-colors duration-300 md:col-span-2"
        >
            {/* Visual Area */}
            <div className="relative h-48 sm:h-64 w-full overflow-hidden border-b border-slate-800/50 bg-slate-900/20 group-hover:bg-slate-900/40 transition-colors flex items-end justify-center px-4 md:px-10">

                {/* Email UI Mockup */}
                <motion.div
                    initial={{ y: 15, scale: 1 }}
                    whileHover={{ y: -5, scale: 1.02 }}
                    transition={{ type: "spring" as const, stiffness: 300, damping: 20 }}
                    className="w-full max-w-md bg-slate-900 border border-slate-700/50 rounded-t-xl shadow-2xl overflow-hidden flex flex-col relative z-10 h-[85%] sm:h-[90%]"
                >
                    {/* Mac window dots and Header */}
                    <div className="bg-slate-800/50 px-4 py-2.5 flex items-center gap-3 border-b border-slate-700/50">
                        <div className="flex gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-full bg-slate-600 group-hover:bg-red-400 transition-colors duration-300" />
                            <div className="w-2.5 h-2.5 rounded-full bg-slate-600 group-hover:bg-amber-400 transition-colors duration-300 delay-75" />
                            <div className="w-2.5 h-2.5 rounded-full bg-slate-600 group-hover:bg-emerald-400 transition-colors duration-300 delay-150" />
                        </div>
                        <div className="flex-1 text-center">
                            <span className="text-[10px] text-slate-400 font-medium tracking-wider">Inbox</span>
                        </div>
                    </div>

                    {/* Email Meta */}
                    <div className="px-5 py-3 border-b border-slate-800/50 bg-slate-900">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-xs text-slate-300"><span className="text-slate-500">From:</span> Scoper AI &lt;intel@scoper.es&gt;</span>
                            <span className="text-xs text-slate-500">Mon 8:00 AM</span>
                        </div>
                        <h4 className="text-sm font-semibold text-white">Your Weekly Intel: 3 Critical Updates</h4>
                    </div>

                    {/* Email Body */}
                    <div className="px-5 py-4 space-y-5 bg-slate-900 flex-1">

                        {/* Item 1 */}
                        <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-[0_0_8px_rgba(168,85,247,0.15)]">
                                    M&A
                                </span>
                                <span className="text-xs font-semibold text-slate-200">MazeMap acquires Thing Technologies</span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-relaxed max-w-[90%]">
                                MazeMap has absorbed a key competitor to solidify market share in the DACH region enterprise wayfinding sector.
                            </p>
                        </div>

                        {/* Item 2 */}
                        <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.15)]">
                                    New Contract
                                </span>
                                <span className="text-xs font-semibold text-slate-200">IndoorAtlas expands in MEA</span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-relaxed max-w-[90%]">
                                Signed a massive multi-year rollout for 5 major airports in the Middle East, challenging our upcoming expansion.
                            </p>
                        </div>

                    </div>
                </motion.div>

                {/* Subtle underlying glow */}
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3/4 h-3/4 bg-blue-500/10 blur-[60px] z-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
            </div>

            {/* Text Content */}
            <div className="p-6 flex flex-col justify-end flex-1">
                <h3 className="text-lg font-semibold text-slate-100 mb-2 group-hover:text-white transition-colors">
                    Weekly Executive Briefing
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed max-w-sm">
                    Get the signal without the noise. Every Monday, Scoper drops the 3 most critical market shifts directly into your inbox.
                </p>
            </div>
        </motion.div>
    );
}
