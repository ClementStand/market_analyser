'use client'

import { motion } from 'framer-motion'
import { Activity } from 'lucide-react'

const INTERCEPTS = [
    {
        id: 1,
        time: '2 minutes ago',
        competitor: 'MazeMap',
        snippet: 'MazeMap announces a strategic partnership with Planon, positioning them to strengthen enterprise offerings in the hybrid workplace market.'
    },
    {
        id: 2,
        time: '18 days ago',
        competitor: 'MazeMap',
        snippet: 'MazeMap acquires Thing Technologies to strengthen its position as a global leader in wayfinding and space intelligence.'
    },
    {
        id: 3,
        time: '3 weeks ago',
        competitor: 'IndoorAtlas',
        snippet: 'IndoorAtlas partners with ExpoFP to create interactive floor plans with accurate indoor positioning capabilities.'
    },
    {
        id: 4,
        time: '1 month ago',
        competitor: 'Mappedin',
        snippet: 'Mappedin launches new AI-powered mapping tools to accelerate digital wayfinding deployments for large venues.'
    }
];

// Duplicate for seamless infinite vertical scroll
const SCROLL_ITEMS = [...INTERCEPTS, ...INTERCEPTS];

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
}

export default function LiveInterceptsCard() {
    return (
        <motion.div
            variants={itemVariants}
            className="group relative flex flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/50 backdrop-blur-sm hover:bg-slate-900/80 transition-colors duration-300 md:col-span-1 h-[22rem]"
        >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-slate-800/50 bg-slate-900/40 z-10 shrink-0">
                <div className="flex items-center gap-3">
                    <Activity className="w-5 h-5 text-slate-400" />
                    <h3 className="text-lg font-semibold text-slate-100">Live Intercepts</h3>
                </div>
                <div className="relative flex items-center justify-center w-2 h-2">
                    <div className="absolute w-2 h-2 bg-red-500 rounded-full" />
                    <div className="absolute w-2 h-2 bg-red-500 rounded-full animate-ping opacity-75" />
                </div>
            </div>

            {/* Scrolling Content Feed */}
            <div
                className="relative flex-1 overflow-hidden px-6 py-2"
                style={{
                    maskImage: 'linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)',
                    WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)'
                }}
            >
                <motion.div
                    animate={{ y: ["0%", "-50%"] }}
                    transition={{
                        repeat: Infinity,
                        ease: "linear",
                        duration: 20, // Slow vertical scroll
                    }}
                    className="flex flex-col gap-6 pt-4"
                >
                    {SCROLL_ITEMS.map((item, idx) => (
                        <div key={`${item.id}-${idx}`} className="flex flex-col gap-1.5 border-l-2 border-slate-800 pl-4 py-1 hover:border-slate-600 transition-colors">
                            <div className="flex items-center gap-2">
                                <span className="text-[11px] font-mono font-medium text-cyan-400">{item.time}</span>
                                <span className="text-sm font-bold text-white">{item.competitor}</span>
                            </div>
                            <p className="text-[13px] text-slate-400 line-clamp-2 leading-relaxed">
                                {item.snippet}
                            </p>
                        </div>
                    ))}
                </motion.div>
            </div>

        </motion.div>
    );
}
