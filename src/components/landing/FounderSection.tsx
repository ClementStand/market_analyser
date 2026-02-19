'use client'

import { motion } from 'framer-motion'
import { User } from 'lucide-react'

export default function FounderSection() {
    return (
        <section id="about" className="py-24 px-6">
            <div className="max-w-3xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-100px' }}
                    transition={{ duration: 0.6 }}
                    className="relative p-8 sm:p-10 rounded-2xl border border-slate-800 bg-slate-900/30 backdrop-blur-sm"
                >
                    {/* Subtle glow */}
                    <div className="absolute -top-20 -right-20 w-40 h-40 bg-blue-500/5 rounded-full blur-[80px] pointer-events-none" />

                    <div className="flex flex-col sm:flex-row items-start gap-6">
                        {/* Avatar */}
                        <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 border border-slate-700 flex items-center justify-center shrink-0">
                            <User className="w-7 h-7 text-blue-400" />
                        </div>

                        <div>
                            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                                Built by
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-4">
                                Cl&eacute;ment Standaert
                            </h3>
                            <p className="text-slate-400 leading-relaxed">
                                As a 21-year-old student bridging Business Administration and Artificial Intelligence,
                                I built Scoper because I saw how much time startups waste on manual market research
                                instead of actual execution. Scoper gives small teams the intelligence capabilities
                                of a Fortune 500 strategy department.
                            </p>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    )
}
