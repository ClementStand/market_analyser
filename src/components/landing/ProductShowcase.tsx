'use client'

import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'
import Image from 'next/image'

export const ProductShowcase = () => {
    const containerRef = useRef<HTMLDivElement>(null)
    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ['start end', 'end start']
    })

    const rotateX = useTransform(scrollYProgress, [0, 1], [15, 0])
    const opacity = useTransform(scrollYProgress, [0, 0.5], [0, 1])
    const translateY = useTransform(scrollYProgress, [0, 0.5], [100, 0])

    return (
        <div ref={containerRef} className="py-20 sm:py-24 pb-12 sm:pb-24">
            <div className="container mx-auto px-4 max-w-7xl">
                <div className="flex justify-center flex-col items-center">
                    <h2 className="text-center text-4xl sm:text-5xl font-bold tracking-tighter mb-4">
                        Intuitive Interface
                    </h2>
                    <p className="text-xl text-center text-white/70 mb-8 max-w-xl mx-auto">
                        Powerful insights delivered through a clean, modern dashboard designed for strategic decision making.
                    </p>

                    <motion.div
                        style={{
                            opacity: opacity,
                            rotateX: rotateX,
                            transformPerspective: "800px",
                            y: translateY
                        }}
                        className="relative w-full max-w-5xl mx-auto group"
                    >
                        {/* Glow Effect */}
                        <div className="absolute inset-0 bg-gradient-to-tr from-blue-600 to-purple-600 rounded-xl blur-3xl opacity-20 group-hover:opacity-40 transition-opacity duration-700 -z-10 transform scale-105" />

                        {/* Browser Frame */}
                        <div className="relative rounded-xl border border-white/10 bg-[#121212]/80 backdrop-blur-sm shadow-2xl overflow-hidden ring-1 ring-white/10">
                            {/* Browser Header (Traffic Lights) */}
                            <div className="relative h-10 border-b border-white/5 bg-[#1A1A1A]/90 flex items-center px-4 w-full">
                                <div className="flex space-x-2 z-10">
                                    <div className="h-3 w-3 rounded-full bg-[#FF5F57] shadow-inner" /> {/* Red */}
                                    <div className="h-3 w-3 rounded-full bg-[#FEBC2E] shadow-inner" /> {/* Yellow */}
                                    <div className="h-3 w-3 rounded-full bg-[#28C840] shadow-inner" /> {/* Green */}
                                </div>

                                {/* Fake URL Bar - Absolutely Centered */}
                                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                    <div className="w-full max-w-md mx-4 h-6 bg-black/40 rounded-md border border-white/5 flex items-center justify-center pointer-events-auto">
                                        <div className="flex items-center space-x-2 text-[10px] text-white/30 font-medium">
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-2.5 h-2.5">
                                                <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                                            </svg>
                                            <span>app.scoper.ai/dashboard</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Screenshot Content */}
                            <div className="relative aspect-video w-full bg-[#0A0A0A]">
                                <Image
                                    src="/app_preview2.png"
                                    alt="Analytics Dashboard Preview"
                                    fill
                                    className="object-contain"
                                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 90vw, 1200px"
                                    priority
                                />

                                {/* Subtle Overlay Gradient (fades bottom of image for blending if needed, optional) */}
                                <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#121212] to-transparent opacity-20" />
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
    )
}
