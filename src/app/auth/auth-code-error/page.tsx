'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function AuthCodeErrorPage() {
    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            <div className="w-full max-w-md bg-white rounded-xl p-8 shadow-2xl text-center">
                <div className="mb-6">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-red-600 text-2xl">!</span>
                    </div>
                    <h1 className="text-xl font-semibold text-slate-900 mb-2">Authentication Error</h1>
                    <p className="text-slate-500 text-sm">
                        The confirmation link is invalid or has expired. This can happen if:
                    </p>
                    <ul className="text-slate-500 text-sm mt-3 space-y-1 text-left list-disc list-inside">
                        <li>The link has already been used</li>
                        <li>The link has expired</li>
                        <li>The link was modified</li>
                    </ul>
                </div>
                <div className="space-y-3">
                    <Link href="/signup">
                        <Button className="w-full bg-cyan-600 hover:bg-cyan-500 text-white">
                            Try signing up again
                        </Button>
                    </Link>
                    <Link href="/login" className="block">
                        <Button variant="outline" className="w-full">
                            <ArrowLeft className="mr-2 h-4 w-4" />
                            Back to login
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    )
}
