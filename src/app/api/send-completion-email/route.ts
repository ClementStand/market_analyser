import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { createClient } from '@/utils/supabase/server'
import { sendAnalysisCompleteEmail } from '@/lib/email'

export async function POST(request: Request) {
    try {
        const supabase = createClient()
        const { data: { user } } = await supabase.auth.getUser()

        if (!user?.email) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const { jobId } = await request.json()
        if (!jobId) {
            return NextResponse.json({ error: 'jobId required' }, { status: 400 })
        }

        // Get user's org
        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email },
            include: { organization: true }
        })

        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        // Verify job belongs to user's org and is completed
        const job = await prisma.fetchJob.findUnique({ where: { id: jobId } })
        if (!job || job.organizationId !== profile.organizationId) {
            return NextResponse.json({ error: 'Job not found' }, { status: 404 })
        }
        if (job.status !== 'completed') {
            return NextResponse.json({ error: 'Job not completed yet' }, { status: 400 })
        }
        if (job.emailSent) {
            return NextResponse.json({ message: 'Email already sent' })
        }

        // Send email
        const origin = request.headers.get('origin') || 'https://market-analyser-dtcf.vercel.app'
        await sendAnalysisCompleteEmail(user.email, profile.organization.name, origin)

        // Mark as sent
        await prisma.fetchJob.update({
            where: { id: jobId },
            data: { emailSent: true }
        })

        return NextResponse.json({ message: 'Email sent' })
    } catch (error) {
        console.error('Send completion email error:', error)
        return NextResponse.json({ error: 'Failed to send email' }, { status: 500 })
    }
}
