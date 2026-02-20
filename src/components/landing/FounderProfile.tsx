'use client'

import { motion } from 'framer-motion'

export default function FounderProfile() {
    return (
        <section className="py-24 px-4 sm:px-6 bg-slate-950 relative overflow-hidden">
            {/* Background Atmosphere */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-blue-500/5 rounded-full blur-[100px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="max-w-4xl mx-auto relative"
            >
                {/* Glassmorphism Card */}
                <div className="relative bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-3xl p-8 sm:p-12 md:p-16 overflow-hidden">

                    {/* Top Glow Accent */}
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />

                    {/* Content */}
                    <div className="relative z-10 flex flex-col space-y-12">

                        {/* Header */}
                        <div className="text-center space-y-6">
                            <span className="text-blue-400 font-mono text-xs sm:text-sm tracking-[0.2em] uppercase font-medium">
                                The Origin Story
                            </span>
                            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight">
                                Built out of <br className="hidden sm:block" />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">
                                    personal frustration.
                                </span>
                            </h2>
                        </div>

                        {/* Letter Body */}
                        <div className="prose prose-lg prose-invert max-w-none text-slate-300 space-y-6 leading-relaxed">
                            <p>
                                Hi, I'm Clément.
                            </p>
                            <p>
                                Originally from Belgium, I spent 13 years in Dubai before moving to Spain, where I am currently a 21-year-old student bridging Business Administration and Artificial Intelligence at ESADE in Barcelona.
                            </p>
                            <p>
                                Scoper actually started because of my dad. He kept asking me to manually compile monthly competitor reports for his business. Sifting through endless PR fluff, funding announcements, and website changes was mind-numbing. I realized that if his business needed this level of intelligence to stay competitive, every startup needed it—but almost no one has the time to do it right.
                            </p>
                            <p>
                                I built Scoper to automate that entire manual grind. My goal is to give small and medium teams the exact same market intelligence capabilities as a Fortune 500 strategy department, without the busywork.
                            </p>
                        </div>

                        {/* Signature Block */}
                        <div className="pt-8 border-t border-slate-800/50 flex items-center gap-4">
                            <div className="h-10 w-1 bg-blue-500/50 rounded-full" />
                            <div>
                                <div className="text-white font-semibold text-lg tracking-tight">
                                    Clement Standaert
                                </div>
                                <div className="text-sm text-blue-400 font-medium">
                                    Founder
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </motion.div>
        </section>
    )
}
