'use client'

import Link from 'next/link'
import Image from 'next/image'
import { ArrowRight } from 'lucide-react'

const footerLinks = {
    Product: [
        { label: 'Features', href: '#features' },
        { label: 'Pricing', href: '#proof' },
        { label: 'Demo', href: '#proof' },
    ],
    Company: [
        { label: 'About', href: '#about' },
        { label: 'Blog', href: '#' },
        { label: 'Contact', href: '#' },
    ],
    Legal: [
        { label: 'Privacy Policy', href: '#' },
        { label: 'Terms of Service', href: '#' },
    ],
}

export default function Footer() {
    return (
        <footer className="border-t border-slate-800 bg-slate-950">
            {/* Final CTA */}
            <div className="max-w-4xl mx-auto text-center py-20 px-6">
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                    Ready to outsmart your competition?
                </h2>
                <p className="mt-3 text-slate-400">
                    Join founders and strategy teams using Scoper to make faster, smarter decisions.
                </p>
                <Link
                    href="/signup"
                    className="group inline-flex items-center gap-2 mt-8 px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-blue-500/20"
                >
                    Get Started for Free
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
            </div>

            {/* Links grid */}
            <div className="max-w-6xl mx-auto px-6 pb-12">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                    {/* Brand */}
                    <div>
                        <div className="flex items-center gap-2 mb-4">
                            <Image src="/scoper_logo.png" alt="Scoper" width={28} height={28} className="rounded-md bg-white p-0.5" />
                            <span className="text-sm font-semibold text-white">Scoper</span>
                        </div>
                        <p className="text-xs text-slate-500 leading-relaxed">
                            AI-powered competitive intelligence for modern teams.
                        </p>
                    </div>

                    {Object.entries(footerLinks).map(([category, links]) => (
                        <div key={category}>
                            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                                {category}
                            </h4>
                            <ul className="space-y-2">
                                {links.map((link) => (
                                    <li key={link.label}>
                                        <a
                                            href={link.href}
                                            className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
                                        >
                                            {link.label}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                {/* Bottom bar */}
                <div className="mt-12 pt-6 border-t border-slate-800/50 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <p className="text-xs text-slate-600">
                        &copy; {new Date().getFullYear()} Scoper. All rights reserved.
                    </p>
                    <div className="flex items-center gap-5">
                        <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="text-slate-600 hover:text-slate-400 transition-colors">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                        </a>
                        <a href="https://twitter.com" target="_blank" rel="noreferrer" className="text-slate-600 hover:text-slate-400 transition-colors">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    )
}
