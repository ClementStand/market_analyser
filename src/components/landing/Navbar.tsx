'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'

const navLinks = [
    { label: 'Features', href: '#features' },
    { label: 'Proof', href: '#proof' },
    { label: 'About', href: '#about' },
]

export default function Navbar() {
    const [mobileOpen, setMobileOpen] = useState(false)

    return (
        <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl"
        >
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2.5">
                    <Image src="/scoper_logo.png" alt="Scoper" width={44} height={44} className="drop-shadow-[0_0_10px_rgba(6,182,212,0.3)]" />
                    <span className="text-lg font-semibold text-white tracking-tight">Scoper</span>
                </Link>

                {/* Desktop Links */}
                <div className="hidden md:flex items-center gap-8">
                    {navLinks.map((link) => (
                        <a
                            key={link.label}
                            href={link.href}
                            className="text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            {link.label}
                        </a>
                    ))}
                </div>

                {/* Desktop CTAs */}
                <div className="hidden md:flex items-center gap-3">
                    <Link
                        href="/login"
                        className="text-sm text-slate-300 hover:text-white transition-colors px-4 py-2"
                    >
                        Log In
                    </Link>
                    <Link
                        href="/signup"
                        className="text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg transition-colors"
                    >
                        Sign Up
                    </Link>
                </div>

                {/* Mobile toggle */}
                <button
                    onClick={() => setMobileOpen(!mobileOpen)}
                    className="md:hidden text-slate-400 hover:text-white"
                >
                    {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </div>

            {/* Mobile Menu */}
            {mobileOpen && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="md:hidden border-t border-white/5 bg-slate-950/95 backdrop-blur-xl px-6 py-4 space-y-3"
                >
                    {navLinks.map((link) => (
                        <a
                            key={link.label}
                            href={link.href}
                            onClick={() => setMobileOpen(false)}
                            className="block text-sm text-slate-400 hover:text-white py-2"
                        >
                            {link.label}
                        </a>
                    ))}
                    <div className="pt-3 border-t border-white/5 flex flex-col gap-2">
                        <Link href="/login" className="text-sm text-slate-300 hover:text-white py-2">
                            Log In
                        </Link>
                        <Link
                            href="/signup"
                            className="text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg text-center transition-colors"
                        >
                            Sign Up
                        </Link>
                    </div>
                </motion.div>
            )}
        </motion.nav>
    )
}
