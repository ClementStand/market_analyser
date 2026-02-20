'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'

const SurveillanceBackground = () => {
    // 5 active intercept dots using the requested brand colors
    const dots = [
        { top: '35%', left: '25%', color: 'bg-cyan-500', delay: 0 },
        { top: '48%', left: '72%', color: 'bg-emerald-500', delay: 1.2 },
        { top: '65%', left: '42%', color: 'bg-red-500', delay: 0.5 },
        { top: '28%', left: '58%', color: 'bg-cyan-500', delay: 2.1 },
        { top: '75%', left: '78%', color: 'bg-emerald-500', delay: 1.8 },
    ];

    return (
        <div
            className="absolute inset-0 z-0 overflow-hidden pointer-events-none"
            style={{
                // Radial gradient mask fades to pure black (transparent) at the edges and bottom
                maskImage: 'radial-gradient(ellipse at center, black 0%, transparent 80%)',
                WebkitMaskImage: 'radial-gradient(ellipse at center, black 0%, transparent 80%)'
            }}
        >
            {/* Highly Stylized Geometric Map Grid (Curved network layers) */}
            <div className="absolute inset-0 opacity-30 flex items-center justify-center">
                <svg className="w-[150%] h-[150%] max-w-none opacity-50" viewBox="0 0 1000 600" fill="none" xmlns="http://www.w3.org/2000/svg">
                    {/* Lat/Lon mapping curves */}
                    <g stroke="currentColor" className="text-slate-400" strokeWidth="1" strokeDasharray="4 4">
                        {/* Horizontal curves */}
                        <path d="M-200,300 Q500,-100 1200,300" />
                        <path d="M-200,300 Q500,100 1200,300" />
                        <path d="M-200,300 Q500,300 1200,300" strokeDasharray="none" strokeWidth="1.5" opacity="0.6" />
                        <path d="M-200,300 Q500,500 1200,300" />
                        <path d="M-200,300 Q500,700 1200,300" />

                        {/* Vertical curves */}
                        <path d="M500,-100 Q100,300 500,700" />
                        <path d="M500,-100 Q300,300 500,700" />
                        <path d="M500,-100 Q500,300 500,700" strokeDasharray="none" strokeWidth="1.5" opacity="0.6" />
                        <path d="M500,-100 Q700,300 500,700" />
                        <path d="M500,-100 Q900,300 500,700" />
                    </g>
                    {/* Concentric radar overlay */}
                    <g stroke="currentColor" className="text-slate-500" strokeWidth="1" strokeDasharray="2 6" opacity="0.4">
                        <circle cx="500" cy="300" r="150" />
                        <circle cx="500" cy="300" r="300" />
                        <circle cx="500" cy="300" r="450" />
                    </g>
                </svg>
            </div>

            {/* Dotted Grid Overlay to give it that "map matrix" feel */}
            <div
                className="absolute inset-0 opacity-[0.10]"
                style={{
                    backgroundImage: 'radial-gradient(circle at center, white 1.5px, transparent 1.5px)',
                    backgroundSize: '20px 20px',
                }}
            />

            {/* Active Intercept Dots */}
            {dots.map((dot, i) => (
                <div key={i} className="absolute z-10" style={{ top: dot.top, left: dot.left }}>
                    <motion.div
                        className={`w-3 h-3 rounded-full ${dot.color}`}
                        animate={{
                            scale: [1, 2.5, 1],
                            opacity: [0.8, 0, 0.8],
                        }}
                        transition={{
                            duration: 3,
                            delay: dot.delay,
                            repeat: Infinity,
                            ease: "easeInOut"
                        }}
                    />
                    {/* Inner solid glowing core */}
                    <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full ${dot.color} shadow-[0_0_12px_currentColor]`} />
                </div>
            ))}
        </div>
    );
};

export default function Hero() {
    return (
        <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden bg-slate-950">
            {/* Layer 0: Global Surveillance Map Component */}
            <SurveillanceBackground />

            {/* Background glowing blobs layer (kept extremely faded so map is visible) */}
            <div className="absolute inset-0 pointer-events-none z-0 mix-blend-screen opacity-50">
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-blue-500/10 rounded-full blur-[120px]" />
                <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-emerald-500/10 rounded-full blur-[100px]" />
            </div>

            <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
                {/* Badge */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/20 bg-blue-900/20 backdrop-blur-md text-blue-300 text-xs font-medium mb-8 shadow-xl shadow-blue-500/5"
                >
                    <Sparkles className="w-3.5 h-3.5" />
                    AI-Powered Competitive Intelligence
                </motion.div>

                {/* Headline */}
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white tracking-tight leading-[1.1] drop-shadow-lg"
                >
                    Your Unfair Advantage.{' '}
                    <span className="bg-gradient-to-r from-blue-400 via-emerald-400 to-blue-400 bg-clip-text text-transparent">
                        Automated.
                    </span>
                </motion.h1>

                {/* Subheadline */}
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="mt-6 text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed drop-shadow-md"
                >
                    Scoper monitors your competitors 24/7 — tracking funding rounds, product launches,
                    leadership changes, and strategic moves — so you can act before they do.
                </motion.p>

                {/* CTAs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
                >
                    <Link
                        href="/signup"
                        className="group flex items-center gap-2 px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 relative overflow-hidden"
                    >
                        {/* Subtle interactive shine on button hover */}
                        <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent skew-x-12" />
                        <span className="relative z-10 flex items-center gap-2">
                            Start Scouting for Free
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </span>
                    </Link>
                </motion.div>
            </div>
        </section>
    )
}
