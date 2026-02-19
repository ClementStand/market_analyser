'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, Tooltip } from 'recharts'
import { TrendingUp, Clock, Shield } from 'lucide-react'

const comparisonData = [
    { name: 'Manual Research', hours: 42, fill: '#f97316', label: '42 hours/week of analyst time' },
    { name: 'Basic Alerts', hours: 18, fill: '#eab308', label: '18 hours/week filtering noise' },
    { name: 'Scoper AI', hours: 2, fill: '#3B82F6', label: '2 hours/week reviewing insights' },
]

const stats = [
    {
        icon: TrendingUp,
        value: '3x',
        label: 'More likely to capture market share',
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/20',
    },
    {
        icon: Clock,
        value: '85%',
        label: 'Less time on manual research',
        color: 'text-blue-400',
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/20',
    },
    {
        icon: Shield,
        value: '24/7',
        label: 'Continuous monitoring coverage',
        color: 'text-violet-400',
        bg: 'bg-violet-500/10',
        border: 'border-violet-500/20',
    },
]

function CustomTooltip({ active, payload }: any) {
    if (!active || !payload?.length) return null
    const data = payload[0].payload
    return (
        <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
            <p className="text-white font-medium text-sm">{data.name}</p>
            <p className="text-slate-300 text-xs mt-1">{data.label}</p>
            <p className="text-lg font-bold mt-1" style={{ color: data.fill }}>
                {data.hours}h <span className="text-xs font-normal text-slate-400">/ week</span>
            </p>
        </div>
    )
}

export default function ProofSection() {
    const [activeIndex, setActiveIndex] = useState<number | null>(null)

    return (
        <section id="proof" className="py-24 px-6">
            <div className="max-w-6xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-100px' }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-16"
                >
                    <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                        The Intelligence Gap is Real
                    </h2>
                    <p className="mt-4 text-slate-400 max-w-xl mx-auto">
                        Companies utilizing continuous competitive intelligence are 3x more likely
                        to capture market share. Most teams still do it manually.
                    </p>
                </motion.div>

                <div className="grid lg:grid-cols-2 gap-8 items-center">
                    {/* Chart */}
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true, margin: '-100px' }}
                        transition={{ duration: 0.6 }}
                        className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-8"
                    >
                        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
                            Weekly Hours Spent on Competitive Research
                        </h3>
                        <p className="text-xs text-slate-500 mb-6">Hover over bars to see details</p>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart
                                data={comparisonData}
                                barCategoryGap="25%"
                                onMouseLeave={() => setActiveIndex(null)}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                <XAxis
                                    dataKey="name"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    axisLine={{ stroke: '#334155' }}
                                    tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    unit="h"
                                    domain={[0, 50]}
                                />
                                <Tooltip
                                    content={<CustomTooltip />}
                                    cursor={{ fill: 'rgba(255,255,255,0.03)', radius: 8 }}
                                />
                                <Bar
                                    dataKey="hours"
                                    radius={[8, 8, 0, 0]}
                                    onMouseEnter={(_, index) => setActiveIndex(index)}
                                    animationDuration={1200}
                                    animationBegin={200}
                                >
                                    {comparisonData.map((entry, index) => (
                                        <Cell
                                            key={index}
                                            fill={entry.fill}
                                            fillOpacity={activeIndex === null || activeIndex === index ? 1 : 0.3}
                                            style={{ transition: 'fill-opacity 200ms ease' }}
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </motion.div>

                    {/* Stats */}
                    <motion.div
                        initial={{ opacity: 0, x: 30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true, margin: '-100px' }}
                        transition={{ duration: 0.6, delay: 0.1 }}
                        className="space-y-5"
                    >
                        {stats.map((stat, i) => (
                            <motion.div
                                key={stat.label}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.4, delay: 0.2 + i * 0.1 }}
                                className={`flex items-center gap-5 p-5 rounded-xl border ${stat.border} ${stat.bg} backdrop-blur-sm hover:scale-[1.02] transition-transform duration-200`}
                            >
                                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${stat.bg}`}>
                                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                                </div>
                                <div>
                                    <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                                    <div className="text-sm text-slate-400">{stat.label}</div>
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>
                </div>
            </div>
        </section>
    )
}
