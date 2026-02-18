import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { createClient } from '@/utils/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET(req: Request) {
    try {
        const supabase = createClient()
        const { data: { user }, error: authError } = await supabase.auth.getUser()

        if (authError || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email! },
        })

        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        // Get the latest FetchJob for this org
        const { searchParams } = new URL(req.url)
        const jobId = searchParams.get('jobId')

        let job
        if (jobId) {
            job = await prisma.fetchJob.findUnique({
                where: { id: jobId }
            })
        } else {
            job = await prisma.fetchJob.findFirst({
                where: { organizationId: profile.organizationId },
                orderBy: { createdAt: 'desc' }
            })
        }

        if (!job) {
            return NextResponse.json({ status: 'none' })
        }

        return NextResponse.json({
            id: job.id,
            status: job.status,
            currentStep: job.currentStep,
            processed: job.processed,
            total: job.total,
            error: job.error,
            createdAt: job.createdAt,
            updatedAt: job.updatedAt,
        })
    } catch (error: any) {
        console.error('Fetch status error:', error)
        return NextResponse.json({ error: error.message }, { status: 500 })
    }
}
