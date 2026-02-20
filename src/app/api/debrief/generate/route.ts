import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'
import { prisma } from '@/lib/prisma'
import { spawn } from 'child_process'
import path from 'path'

export const maxDuration = 300 // Set max duration heavily for python script (Vercel max for Hobby is 10s though, Pro is 300s)

export async function POST(request: Request) {
    try {
        const supabase = createClient()
        const { data: { user } } = await supabase.auth.getUser()

        if (!user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email! }
        })

        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        const orgId = profile.organizationId

        // Call python script
        const scriptPath = path.join(process.cwd(), 'scripts', 'debrief_generator.py')

        // Spawn Python process in the background. On Vercel, this is extremely risky,
        // but since we are generating it this way, we'll wait for it.
        return new Promise<NextResponse>((resolve) => {
            // Using python3, might need to rely on the vercel environment or standard python
            const pythonProcess = spawn('python3', [scriptPath, '--org-id', orgId])

            let output = ''
            let errorOutput = ''

            pythonProcess.stdout.on('data', (data) => {
                output += data.toString()
            })

            pythonProcess.stderr.on('data', (data) => {
                errorOutput += data.toString()
            })

            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    console.error('Debrief Generator Error:', errorOutput)
                    resolve(NextResponse.json({ error: 'Failed to generate debrief', details: errorOutput }, { status: 500 }))
                    return
                }

                resolve(NextResponse.json({ success: true, message: 'Debrief generated successfully' }))
            })

            // To prevent hanging indefinitely
            setTimeout(() => {
                pythonProcess.kill()
                resolve(NextResponse.json({ error: 'Generation timed out' }, { status: 504 }))
            }, 55000) // NextJS edge limit or Vercel Hobby limits
        })

    } catch (error: any) {
        console.error('Debrief API error:', error)
        return NextResponse.json(
            { error: 'Internal server error', details: error.message },
            { status: 500 }
        )
    }
}
