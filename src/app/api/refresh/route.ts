import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { createClient } from '@/utils/supabase/server'

export const dynamic = 'force-dynamic'

export async function POST(req: Request) {
    try {
        // Get authenticated user and their org
        const supabase = createClient()
        const { data: { user }, error: authError } = await supabase.auth.getUser()

        if (authError || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email! },
            include: { organization: true }
        })

        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        const orgId = profile.organizationId

        // Create a FetchJob for tracking
        const job = await prisma.fetchJob.create({
            data: {
                organizationId: orgId,
                status: 'pending',
                processed: 0,
                total: 0,
            }
        })

        // Parse optional params from request body
        let days: number | undefined
        let competitorName: string | undefined
        try {
            const body = await req.json()
            days = body.days
            competitorName = body.competitorName
        } catch {
            // No body is fine
        }

        if (process.env.PYTHON_WORKER_URL) {
            // PRODUCTION: Call Railway Python Worker
            console.log(`Calling Python Worker at ${process.env.PYTHON_WORKER_URL}/refresh-news...`)
            const workerRes = await fetch(`${process.env.PYTHON_WORKER_URL}/refresh-news`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    orgId,
                    jobId: job.id,
                    days,
                    competitorName,
                }),
            })

            if (!workerRes.ok) {
                const errText = await workerRes.text()
                console.error(`Worker failed: ${workerRes.status} ${errText}`)
                await prisma.fetchJob.update({
                    where: { id: job.id },
                    data: { status: 'error', error: errText }
                })
                return NextResponse.json({ error: 'Worker failed', details: errText }, { status: 502 })
            }

            return NextResponse.json({ success: true, jobId: job.id, message: 'Refresh started in background' })
        } else {
            // DEVELOPMENT: Spawn local Python process
            const { spawn } = require('child_process')
            const path = require('path')
            const fs = require('fs')

            const scriptPath = path.join(process.cwd(), 'scripts', 'news_fetcher.py')
            const logPath = path.join(process.cwd(), 'public', 'refresh_log.txt')

            let pythonCmd = 'python3'
            const venvPython = path.join(process.cwd(), '.venv/bin/python')
            if (fs.existsSync(venvPython)) {
                pythonCmd = venvPython
            }

            const args = [scriptPath, '--org-id', orgId]
            if (days) args.push('--days', String(days))
            if (competitorName) args.push('--competitor', competitorName)
            args.push('--job-id', job.id)

            console.log(`Spawning: ${pythonCmd} ${args.join(' ')}`)

            const logFile = fs.openSync(logPath, 'w')
            const child = spawn(pythonCmd, args, {
                detached: true,
                stdio: ['ignore', logFile, logFile],
                cwd: process.cwd(),
                env: { ...process.env }
            })

            child.on('error', (err: Error) => {
                console.error('Failed to start subprocess:', err)
            })

            child.unref()

            return NextResponse.json({ success: true, jobId: job.id, message: 'Refresh started in background' })
        }
    } catch (error: any) {
        console.error(`Refresh error: ${error}`)
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}
