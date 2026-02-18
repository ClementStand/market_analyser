import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'

export async function POST(req: Request) {
    try {
        const { competitorIds, orgId } = await req.json()

        if ((!competitorIds || competitorIds.length === 0) && !orgId) {
            return NextResponse.json({ error: 'Must provide competitorIds or orgId' }, { status: 400 })
        }

        if (process.env.PYTHON_WORKER_URL) {
            // PRODUCTION: Call Railway Python Worker
            console.log(`Calling Python Worker at ${process.env.PYTHON_WORKER_URL}...`)
            const workerRes = await fetch(`${process.env.PYTHON_WORKER_URL}/process-onboarding`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ competitorIds, orgId }),
            })

            if (!workerRes.ok) {
                const errText = await workerRes.text()
                console.error(`Worker failed: ${workerRes.status} ${errText}`)
                return NextResponse.json({ error: 'Worker failed', details: errText }, { status: 502 })
            }

            const workerData = await workerRes.json()
            return NextResponse.json(workerData)

        } else {
            // DEVELOPMENT: Spawn Local Process
            const scriptPath = path.join(process.cwd(), 'scripts', 'onboarding_agent.py')
            const args = [scriptPath]

            if (competitorIds && competitorIds.length > 0) {
                args.push('--competitor-ids', competitorIds.join(','))
            } else if (orgId) {
                args.push('--org-id', orgId)
            }

            let pythonCmd = 'python3'
            const venvPython = path.join(process.cwd(), '.venv/bin/python')
            if (fs.existsSync(venvPython)) {
                pythonCmd = venvPython
            }

            console.log(`Starting onboarding agent using ${pythonCmd}...`)

            // FIX: Explicitly tell TypeScript this Promise returns a NextResponse
            return new Promise<NextResponse>((resolve) => {
                const python = spawn(pythonCmd, args)

                let output = ''
                let error = ''

                python.stdout.on('data', (data) => {
                    const text = data.toString()
                    console.log(`[Onboarding Agent] ${text}`)
                    output += text
                })

                python.stderr.on('data', (data) => {
                    const text = data.toString()
                    console.error(`[Onboarding Agent Error] ${text}`)
                    error += text
                })

                python.on('close', (code) => {
                    if (code !== 0) {
                        console.error(`Onboarding agent exited with code ${code}`)
                        resolve(NextResponse.json({ error: 'Agent failed', details: error }, { status: 500 }))
                    } else {
                        console.log('Onboarding agent completed successfully')
                        resolve(NextResponse.json({ success: true, logs: output }))
                    }
                })
            })
        }

    } catch (error) {
        console.error('Onboarding Process API Error:', error)
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
    }
}